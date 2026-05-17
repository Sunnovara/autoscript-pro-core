import time
import logging
import requests
from langchain.tools import Tool, StructuredTool

from backend.services.github_api import (
    parse_github_credentials,
    save_credentials,
    test_github_auth,
    create_initial_commit,
    push_files_to_existing_repo,
)
from backend.services.github_workflows import create_github_workflows
from backend.services.plan_parser import extract_plan_from_artifact, extract_plan_summary

logger = logging.getLogger(__name__)


def make_push_tool(agent) -> Tool:
    """Factory for the push_to_github Tool"""

    def push_to_github(input_str: str) -> str:
        if not agent.generated_files:
            return "No files to push. Generate Terraform code first."

        if not input_str or "|" not in input_str:
            file_list = "\n".join(f"• {f}" for f in agent.generated_files)
            return (
                "GitHub Repository Setup Required\n\n"
                "Provide: https://github.com/username/repo | ghp_token\n\n"
                f"Files ready to push:\n{file_list}"
            )

        parts = input_str.split("|")
        if len(parts) != 2:
            return "Invalid format. Expected: repo_url|token"

        repo_url, github_token = parts[0].strip(), parts[1].strip()

        if not repo_url.startswith("http"):
            return "Invalid URL — must start with https://"
        if not github_token:
            return "Missing GitHub token"

        try:
            owner, repo, api_base, _ = parse_github_credentials(repo_url, github_token)
        except ValueError as e:
            return f"Error: {str(e)}"

        # Store credentials on agent
        agent.github_token = github_token
        agent.github_repo_url = repo_url
        agent.api_base = api_base
        save_credentials({
            'github_token': github_token,
            'github_repo_url': repo_url,
            'github_domain': 'github.com' if 'github.com' in repo_url else None,
            'api_base': api_base,
        })

        auth_ok, headers = test_github_auth(api_base, github_token)
        if not auth_ok:
            return (
                "GitHub Authentication Failed.\n"
                "Check token validity and permissions (needs 'repo' + 'workflow' scopes).\n"
                "Regenerate at https://github.com/settings/tokens"
            )

        repo_resp = requests.get(f"{api_base}/repos/{owner}/{repo}", headers=headers)
        if repo_resp.status_code != 200:
            return f"Cannot access repository {owner}/{repo}: {repo_resp.text}"

        default_branch = repo_resp.json().get('default_branch', 'main')

        workflows = create_github_workflows(agent.selected_cloud_provider)
        all_files = {**agent.generated_files, **workflows}

        contents_resp = requests.get(f"{api_base}/repos/{owner}/{repo}/contents", headers=headers)
        is_empty = contents_resp.status_code == 404

        if is_empty:
            return create_initial_commit(owner, repo, headers, all_files, default_branch, api_base)
        return push_files_to_existing_repo(owner, repo, headers, all_files, default_branch, api_base)

    return Tool(
        name="push_to_github",
        func=push_to_github,
        description=(
            "Push generated Terraform code and GitHub workflows to a repository. "
            "Input format: 'repo_url|github_token'. "
            "Example: 'https://github.com/user/repo|ghp_token123'"
        ),
    )


def make_plan_tool(agent) -> Tool:
    """Factory for the trigger_terraform_plan Tool"""

    def trigger_terraform_plan(input_str: str = "") -> str:
        if isinstance(input_str, dict):
            input_str = ""

        if input_str and "|" in input_str:
            parts = input_str.split("|")
            try:
                owner, repo, api_base, _ = parse_github_credentials(parts[0].strip(), parts[1].strip())
                agent.github_token = parts[1].strip()
                agent.github_repo_url = parts[0].strip()
                agent.api_base = api_base
            except ValueError as e:
                return f"Error: {str(e)}"
        elif not agent.github_token or not agent.github_repo_url:
            return "Error: GitHub credentials not set. Push code first."
        else:
            try:
                owner, repo, api_base, _ = parse_github_credentials(agent.github_repo_url, agent.github_token)
            except ValueError as e:
                return f"Error: {str(e)}"

        headers = {"Authorization": f"token {agent.github_token}", "Accept": "application/vnd.github.v3+json"}
        api_url = f"{api_base}/repos/{owner}/{repo}/actions/workflows/terraform-plan.yml/dispatches"

        response = requests.post(api_url, headers=headers, json={"ref": "main"})
        if response.status_code == 204:
            time.sleep(3)
            try:
                plan_output = _get_plan_output(agent, owner, repo, api_base, headers)
                if plan_output and "No plan output available" not in plan_output:
                    agent.terraform_plan_output = plan_output
                    return f"Terraform Plan workflow triggered for {owner}/{repo}.\n\nPlan Output:\n\n{plan_output}"
            except Exception as e:
                logger.warning(f"Could not auto-retrieve plan output: {e}")
            return (
                f"Terraform Plan workflow triggered for {owner}/{repo}.\n"
                "Workflow is running (1–2 minutes). Ask me to 'get terraform plan output' to see results."
            )
        return f"Failed to trigger workflow: {response.text}"

    return Tool(
        name="trigger_terraform_plan",
        func=trigger_terraform_plan,
        description="Trigger Terraform plan workflow on GitHub. Input: 'repo_url|token' or empty if credentials are stored.",
    )


def make_plan_output_tool(agent) -> StructuredTool:
    """Factory for the get_terraform_plan_output StructuredTool"""

    def get_terraform_plan_output(input_str: str = "") -> str:
        if not agent.github_token or not agent.github_repo_url:
            return "Error: GitHub credentials not set"

        try:
            owner, repo, api_base, _ = parse_github_credentials(agent.github_repo_url, agent.github_token)
        except ValueError as e:
            return f"Error: {str(e)}"

        headers = {"Authorization": f"token {agent.github_token}", "Accept": "application/vnd.github.v3+json"}

        runs_url = f"{api_base}/repos/{owner}/{repo}/actions/workflows/terraform-plan.yml/runs"
        runs_resp = requests.get(runs_url, headers=headers)
        if runs_resp.status_code != 200:
            return f"Failed to get workflow runs: {runs_resp.text}"

        runs = runs_resp.json().get("workflow_runs", [])
        if not runs:
            return "No terraform plan runs found"

        latest_run = next((r for r in runs if r.get("conclusion") == "success"), None)
        if not latest_run:
            return f"No successful runs found. Latest status: {runs[0].get('conclusion', 'unknown')}"

        artifacts_resp = requests.get(
            f"{api_base}/repos/{owner}/{repo}/actions/runs/{latest_run['id']}/artifacts", headers=headers
        )
        if artifacts_resp.status_code != 200:
            return f"Failed to get artifacts: {artifacts_resp.text}"

        artifacts = artifacts_resp.json().get("artifacts", [])
        plan_artifact = next(
            (a for a in artifacts if "terraform-plan-output" in a.get("name", "").lower()), None
        )
        if not plan_artifact:
            return f"Plan output artifact not found. Available: {[a.get('name') for a in artifacts]}"

        download_resp = requests.get(plan_artifact["archive_download_url"], headers=headers)
        if download_resp.status_code != 200:
            return f"Failed to download artifact: {download_resp.text}"

        plan_output = extract_plan_from_artifact(download_resp.content)
        if plan_output and len(plan_output.strip()) > 50:
            agent.terraform_plan_output = plan_output
            agent.generated_files["plan-output"] = plan_output
            summary = extract_plan_summary(plan_output)
            return (
                f"## Terraform Plan Output\n\n{summary}\n\n"
                "Complete plan is in the 'plan-output' tab.\n"
                "Next: Review the plan and run 'terraform apply' if everything looks correct."
            )
        return "Plan output not found in artifact. Check GitHub Actions for details."

    return StructuredTool.from_function(
        name="get_terraform_plan_output",
        func=lambda input_str="": get_terraform_plan_output(input_str),
        description="Get output from the latest Terraform plan workflow run. No input required.",
    )


def make_apply_tool(agent) -> StructuredTool:
    """Factory for the trigger_terraform_apply StructuredTool"""

    def trigger_terraform_apply(input_str: str = "") -> str:
        if isinstance(input_str, dict):
            input_str = ""
        if not agent.github_token or not agent.github_repo_url:
            return "Error: GitHub credentials not set. Push code first."

        try:
            owner, repo, api_base, _ = parse_github_credentials(agent.github_repo_url, agent.github_token)
        except ValueError as e:
            return f"Error: {str(e)}"

        headers = {"Authorization": f"token {agent.github_token}", "Accept": "application/vnd.github.v3+json"}
        response = requests.post(
            f"{api_base}/repos/{owner}/{repo}/actions/workflows/terraform-apply.yml/dispatches",
            headers=headers,
            json={"ref": "main"},
        )
        if response.status_code == 204:
            provider_name = "Azure" if agent.selected_cloud_provider == "azure" else "AWS"
            return (
                f"Terraform Apply workflow triggered.\n"
                f"This will deploy real {provider_name} infrastructure and may incur costs.\n"
                "Monitor progress in the GitHub Actions tab."
            )
        return f"Failed to trigger apply workflow: {response.text}"

    return StructuredTool.from_function(
        name="trigger_terraform_apply",
        func=lambda input_str="": trigger_terraform_apply(input_str),
        description="Trigger Terraform apply workflow to deploy infrastructure. No input required.",
    )


def make_state_tool(agent) -> StructuredTool:
    """Factory for the get_terraform_state StructuredTool"""

    def get_terraform_state(input_str: str = "") -> str:
        if not agent.github_token or not agent.github_repo_url:
            return "Error: GitHub credentials not set. Push code first."

        try:
            owner, repo, api_base, _ = parse_github_credentials(agent.github_repo_url, agent.github_token)
        except ValueError as e:
            return f"Error: {str(e)}"

        import base64, json as _json

        headers = {"Authorization": f"token {agent.github_token}", "Accept": "application/vnd.github.v3+json"}
        resp = requests.get(f"{api_base}/repos/{owner}/{repo}/contents/terraform.tfstate", headers=headers)

        if resp.status_code == 200:
            state_content = base64.b64decode(resp.json()['content']).decode('utf-8')
            agent.generated_files["terraform.tfstate"] = state_content
            try:
                state_data = _json.loads(state_content)
                resources = state_data.get('resources', [])
                resource_types: dict = {}
                for r in resources:
                    rt = r.get('type', 'unknown')
                    resource_types[rt] = resource_types.get(rt, 0) + 1
                summary = f"## Terraform State Summary\n\n**Total Resources:** {len(resources)}\n\n"
                if resource_types:
                    summary += "**Resource Types:**\n"
                    for rt, count in resource_types.items():
                        summary += f"- {rt}: {count}\n"
                return summary
            except Exception:
                return "State file retrieved. See the 'terraform.tfstate' tab."

        elif resp.status_code == 404:
            return "No state file found. No infrastructure has been deployed yet."
        return f"Error retrieving state file: {resp.text}"

    return StructuredTool.from_function(
        name="get_terraform_state",
        func=lambda input_str="": get_terraform_state(input_str),
        description="Get current Terraform state file from the repository. No input required.",
    )


def make_destroy_tool(agent) -> StructuredTool:
    """Factory for the trigger_terraform_destroy StructuredTool"""

    def trigger_terraform_destroy(input_str: str = "") -> str:
        if isinstance(input_str, dict):
            input_str = ""
        if not agent.github_token or not agent.github_repo_url:
            return "Error: GitHub credentials not set. Push code first."

        try:
            owner, repo, api_base, _ = parse_github_credentials(agent.github_repo_url, agent.github_token)
        except ValueError as e:
            return f"Error: {str(e)}"

        headers = {"Authorization": f"token {agent.github_token}", "Accept": "application/vnd.github.v3+json"}
        full_repo_name = f"{owner}/{repo}"

        state_resp = requests.get(
            f"{api_base}/repos/{owner}/{repo}/contents/terraform.tfstate", headers=headers
        )
        if state_resp.status_code == 404:
            return f"No terraform.tfstate found in {full_repo_name}. Nothing to destroy."

        response = requests.post(
            f"{api_base}/repos/{owner}/{repo}/actions/workflows/terraform-destroy.yml/dispatches",
            headers=headers,
            json={
                "ref": "main",
                "inputs": {"confirm_destroy": "DESTROY", "repository_name": full_repo_name},
            },
        )
        if response.status_code == 204:
            provider_name = "Azure" if agent.selected_cloud_provider == "azure" else "AWS"
            return (
                f"Terraform Destroy workflow triggered for {full_repo_name}.\n"
                f"WARNING: This will permanently destroy all {provider_name} resources in this repository's state.\n"
                "Multiple safety checks are active. Monitor progress in GitHub Actions."
            )
        return f"Failed to trigger destroy workflow: {response.text}"

    return StructuredTool.from_function(
        name="trigger_terraform_destroy",
        func=lambda input_str="": trigger_terraform_destroy(input_str),
        description="Trigger Terraform destroy workflow. Only destroys resources in THIS repository's state. No input required.",
    )


# ---------------------------------------------------------------------------
# Internal plan output helper
# ---------------------------------------------------------------------------

def _get_plan_output(agent, owner: str, repo: str, api_base: str, headers: dict) -> str:
    runs_resp = requests.get(
        f"{api_base}/repos/{owner}/{repo}/actions/workflows/terraform-plan.yml/runs",
        headers=headers,
        params={"per_page": 1},
    )
    if runs_resp.status_code != 200:
        return "No plan output available"

    runs = runs_resp.json().get("workflow_runs", [])
    if not runs or runs[0]["status"] != "completed" or runs[0]["conclusion"] != "success":
        return "No plan output available"

    run_id = runs[0]["id"]
    artifacts_resp = requests.get(
        f"{api_base}/repos/{owner}/{repo}/actions/runs/{run_id}/artifacts", headers=headers
    )
    if artifacts_resp.status_code != 200:
        return "No plan output available"

    artifacts = artifacts_resp.json().get("artifacts", [])
    plan_artifact = next((a for a in artifacts if a["name"] == "terraform-plan-output"), None)
    if not plan_artifact:
        return "No plan output available"

    dl_resp = requests.get(plan_artifact["archive_download_url"], headers=headers)
    if dl_resp.status_code != 200:
        return "No plan output available"

    return extract_plan_from_artifact(dl_resp.content)
