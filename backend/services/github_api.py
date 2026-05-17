import os
import json
import base64
import logging
import tempfile
import requests
from typing import Tuple, Dict, Optional

logger = logging.getLogger(__name__)

GITHUB_ENTERPRISE_DOMAIN = os.getenv("GITHUB_ENTERPRISE_DOMAIN")


# ---------------------------------------------------------------------------
# Credential helpers
# ---------------------------------------------------------------------------

def parse_github_credentials(repo_url: str, github_token: str) -> Tuple[str, str, str, dict]:
    """
    Parse a GitHub repo URL and token.
    Returns (owner, repo, api_base, auth_headers).
    Supports github.com and GITHUB_ENTERPRISE_DOMAIN.
    """
    if "github.com/" in repo_url:
        api_base = "https://api.github.com"
        url_parts = repo_url.split("github.com/")[1].split("/")
    elif GITHUB_ENTERPRISE_DOMAIN and f"{GITHUB_ENTERPRISE_DOMAIN}/" in repo_url:
        api_base = f"https://{GITHUB_ENTERPRISE_DOMAIN}/api/v3"
        url_parts = repo_url.split(f"{GITHUB_ENTERPRISE_DOMAIN}/")[1].split("/")
    else:
        raise ValueError(
            "Unsupported GitHub URL format. Use github.com or set GITHUB_ENTERPRISE_DOMAIN."
        )

    owner = url_parts[0]
    repo = url_parts[1].replace(".git", "")

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    return owner, repo, api_base, headers


def save_credentials(credentials: dict) -> None:
    """Persist GitHub credentials to a temp file for session continuity"""
    try:
        creds_file = os.path.join(tempfile.gettempdir(), 'terraform_agent_creds.json')
        with open(creds_file, 'w') as f:
            json.dump(credentials, f)
        logger.info(f"Credentials saved to {creds_file}")
    except Exception as e:
        logger.warning(f"Failed to save credentials: {e}")


def restore_credentials() -> Optional[dict]:
    """Load previously saved GitHub credentials from temp file"""
    try:
        creds_file = os.path.join(tempfile.gettempdir(), 'terraform_agent_creds.json')
        if os.path.exists(creds_file):
            with open(creds_file, 'r') as f:
                credentials = json.load(f)
            if credentials.get('github_token') and credentials.get('github_repo_url'):
                logger.info(f"Credentials restored from {creds_file}")
                return credentials
        logger.info("No saved credentials found")
        return None
    except Exception as e:
        logger.warning(f"Failed to restore credentials: {e}")
        return None


# ---------------------------------------------------------------------------
# Push helpers
# ---------------------------------------------------------------------------

def test_github_auth(api_base: str, github_token: str) -> Tuple[bool, dict]:
    """
    Test GitHub token validity.
    Returns (success, headers_to_use).
    Tries Bearer first, falls back to token format.
    """
    headers_bearer = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    response = requests.get(f"{api_base}/user", headers=headers_bearer)
    if response.status_code == 200:
        return True, headers_bearer

    headers_token = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    response = requests.get(f"{api_base}/user", headers=headers_token)
    if response.status_code == 200:
        return True, headers_token

    return False, {}


def create_initial_commit(
    owner: str,
    repo: str,
    headers: dict,
    all_files: Dict[str, str],
    branch: str,
    api_base: str,
) -> str:
    """
    Populate an empty GitHub repository by creating files one by one via the Contents API.
    README.md is created first to initialise the default branch.
    """
    try:
        logger.info(f"Creating initial commit for {owner}/{repo} with {len(all_files)} files")

        success_files = []
        failed_files = []

        readme_content = all_files.get("README.md") or _default_readme(repo, all_files)

        readme_url = f"{api_base}/repos/{owner}/{repo}/contents/README.md"
        readme_resp = requests.put(
            readme_url,
            headers=headers,
            json={
                "message": "Initial commit: Add README",
                "content": base64.b64encode(readme_content.encode()).decode(),
                "branch": branch,
            },
        )
        if readme_resp.status_code == 201:
            success_files.append("README.md")
        else:
            return f"Failed to initialize repository: {readme_resp.text}"

        for filename, content in all_files.items():
            if filename.lower() == 'readme.md':
                continue
            try:
                file_url = f"{api_base}/repos/{owner}/{repo}/contents/{filename}"
                resp = requests.put(
                    file_url,
                    headers=headers,
                    json={
                        "message": f"Add {filename} via Terraform AI Agent",
                        "content": base64.b64encode(content.encode()).decode(),
                        "branch": branch,
                    },
                )
                if resp.status_code == 201:
                    success_files.append(filename)
                else:
                    failed_files.append(f"{filename}: {resp.text}")
            except Exception as e:
                failed_files.append(f"{filename}: {str(e)}")

        if failed_files:
            return (
                f"Partial success — {len(success_files)} files created, "
                f"{len(failed_files)} failed:\n"
                + "\n".join(f"  - {e}" for e in failed_files)
            )
        return (
            f"All {len(success_files)} files successfully pushed to {owner}/{repo}.\n"
            f"Next: configure repository secrets and run the Terraform Plan workflow."
        )

    except Exception as e:
        logger.error(f"Exception in create_initial_commit: {e}")
        return f"Error creating initial commit: {str(e)}"


def push_files_to_existing_repo(
    owner: str,
    repo: str,
    headers: dict,
    all_files: Dict[str, str],
    default_branch: str,
    api_base: str,
) -> str:
    """Update or create files one by one in a non-empty repository"""
    success_files = []
    failed_files = []

    for filename, content in all_files.items():
        try:
            api_url = f"{api_base}/repos/{owner}/{repo}/contents/{filename}"
            existing = requests.get(api_url, headers=headers)

            data = {
                "message": f"Add/Update {filename} via Terraform Agent",
                "content": base64.b64encode(content.encode()).decode(),
                "branch": default_branch,
            }
            if existing.status_code == 200:
                data["sha"] = existing.json()["sha"]

            resp = requests.put(api_url, headers=headers, json=data)
            if resp.status_code in (200, 201):
                success_files.append(filename)
            else:
                failed_files.append(f"{filename}: {resp.text}")
        except Exception as e:
            failed_files.append(f"{filename}: {str(e)}")

    if success_files and not failed_files:
        return (
            f"Successfully pushed {len(success_files)} files to {owner}/{repo}.\n"
            "Next: run terraform plan to preview the infrastructure."
        )
    elif success_files:
        return (
            f"Pushed {len(success_files)} files. "
            f"{len(failed_files)} failed:\n"
            + "\n".join(f"  - {e}" for e in failed_files)
        )
    return f"Failed to push files: {failed_files}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _default_readme(repo: str, all_files: Dict[str, str]) -> str:
    file_list = "\n".join(f"- `{f}`" for f in all_files if f.lower() != "readme.md")
    return f"""# {repo}

Terraform infrastructure code generated by AutoScript-Pro AI Agent.

## Files

{file_list}

## Usage

1. Configure cloud provider credentials
2. Run `terraform init`
3. Run `terraform plan` to review changes
4. Run `terraform apply` to deploy infrastructure

Generated by AutoScript-Pro Terraform AI Agent
"""
