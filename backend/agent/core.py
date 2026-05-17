import os
import re
import logging
from typing import Dict, List, Optional, Set

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from backend.services.aws_docs import AWSProviderDocsFetcher
from backend.services.github_api import restore_credentials, save_credentials
from backend.agent.tools.generation import make_generate_tool
from backend.agent.tools.modification import make_modify_tool
from backend.agent.tools.github_tools import (
    make_push_tool,
    make_plan_tool,
    make_plan_output_tool,
    make_apply_tool,
    make_state_tool,
    make_destroy_tool,
)
from backend.agent.tools.analysis import (
    make_describe_tool,
    make_load_code_tool,
    make_load_attachments_tool,
    make_change_bucket_tool,
    make_save_locally_tool,
    make_retry_push_tool,
)

logger = logging.getLogger(__name__)


class TerraformAIAgent:
    """
    Orchestrator for the Terraform AI Agent.

    State is kept on this object; all tool logic lives in backend/agent/tools/
    and backend/services/.
    """

    def __init__(self):
        import httpx
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self.llm = None
        try:
            http_client = httpx.Client(verify=False, timeout=30.0)
            self.llm = ChatOpenAI(
                model=os.environ.get("OPENAI_MODEL", "gpt-4.1"),
                api_key=os.environ.get("OPENAI_API_KEY"),
                temperature=0.1,
                max_tokens=4000,
                timeout=30,
                max_retries=2,
                http_client=http_client,
            )
        except Exception:
            logger.warning(
                "OpenAI LLM could not be initialised at startup. "
                "The app will still run, but AI features will fail until an API key is set."
            )

        # ── Agent state ──────────────────────────────────────────────────
        self.generated_files: Dict[str, str] = {}
        self.existing_code: Dict[str, str] = {}
        self.attachments: Dict[str, bytes] = {}
        self.github_token: Optional[str] = None
        self.github_repo_url: Optional[str] = None
        self.github_domain: Optional[str] = None
        self.api_base: Optional[str] = None
        self.terraform_plan_output: Optional[str] = None
        self.selected_cloud_provider: str = "aws"
        self.service_principal_auth: bool = True

        logger.info(f"TerraformAIAgent initialised — ID: {id(self)}")

        self._restore_credentials()

        self.docs_fetcher = AWSProviderDocsFetcher()
        self.tools = self._create_tools()
        self.agent_executor = self._create_agent()

    # ── Credential persistence ────────────────────────────────────────────

    def _save_credentials(self) -> None:
        save_credentials({
            'github_token': self.github_token,
            'github_repo_url': self.github_repo_url,
            'github_domain': self.github_domain,
            'api_base': self.api_base,
        })

    def _restore_credentials(self) -> None:
        creds = restore_credentials()
        if creds:
            self.github_token = creds.get('github_token')
            self.github_repo_url = creds.get('github_repo_url')
            self.github_domain = creds.get('github_domain')
            self.api_base = creds.get('api_base')

    # ── Documentation helpers (used by tool closures) ──────────────────────

    def _get_resource_documentation(self, user_request: str) -> str:
        resource_mappings = {
            's3': ['aws_s3_bucket', 'aws_s3_bucket_versioning', 'aws_s3_bucket_server_side_encryption_configuration'],
            'bucket': ['aws_s3_bucket', 'aws_s3_bucket_versioning', 'aws_s3_bucket_server_side_encryption_configuration'],
            'ec2': ['aws_instance', 'aws_security_group', 'aws_key_pair'],
            'instance': ['aws_instance', 'aws_security_group', 'aws_key_pair'],
            'vpc': ['aws_vpc', 'aws_subnet', 'aws_internet_gateway', 'aws_route_table'],
            'rds': ['aws_db_instance', 'aws_db_subnet_group', 'aws_db_parameter_group'],
            'database': ['aws_db_instance', 'aws_db_subnet_group', 'aws_db_parameter_group'],
            'lambda': ['aws_lambda_function', 'aws_iam_role', 'aws_iam_role_policy_attachment'],
            'alb': ['aws_lb', 'aws_lb_target_group', 'aws_lb_listener'],
            'cloudfront': ['aws_cloudfront_distribution', 'aws_cloudfront_origin_access_control'],
            'api': ['aws_api_gateway_rest_api', 'aws_api_gateway_resource', 'aws_api_gateway_method'],
            'iam': ['aws_iam_role', 'aws_iam_policy', 'aws_iam_role_policy_attachment'],
        }

        relevant_resources: Set[str] = set()
        lower = user_request.lower()
        for keyword, resources in resource_mappings.items():
            if keyword in lower:
                relevant_resources.update(resources)

        if not relevant_resources:
            relevant_resources = {'aws_instance', 'aws_s3_bucket', 'aws_vpc'}

        docs_text = ""
        for resource_type in list(relevant_resources)[:5]:
            docs = self.docs_fetcher.fetch_resource_docs(resource_type)
            if docs:
                docs_text += f"\n=== {resource_type.upper()} DOCUMENTATION ===\n"
                docs_text += f"URL: {docs['url']}\n"
                if docs['required_args']:
                    docs_text += f"REQUIRED ARGUMENTS: {', '.join(docs['required_args'])}\n"
                if docs['optional_args']:
                    docs_text += f"OPTIONAL ARGUMENTS: {', '.join(docs['optional_args'][:10])}\n"
                if docs['example']:
                    docs_text += f"EXAMPLE:\n{docs['example']}\n"
                docs_text += "\n"

        return docs_text or "No specific documentation found."

    def _extract_resource_types_from_code(self, code: str) -> Set[str]:
        resource_types: Set[str] = set()
        for line in code.split('\n'):
            if line.strip().startswith('resource '):
                parts = line.strip().split('"')
                if len(parts) >= 2 and parts[1].startswith('aws_'):
                    resource_types.add(parts[1])
        return resource_types

    def _get_documentation_for_resources(self, resource_types: Set[str]) -> str:
        docs_text = ""
        for resource_type in list(resource_types)[:5]:
            docs = self.docs_fetcher.fetch_resource_docs(resource_type)
            if docs:
                docs_text += f"\n=== {resource_type.upper()} DOCUMENTATION ===\n"
                if docs['required_args']:
                    docs_text += f"REQUIRED: {', '.join(docs['required_args'])}\n"
                if docs['optional_args']:
                    docs_text += f"OPTIONAL: {', '.join(docs['optional_args'][:10])}\n"
                if docs['example']:
                    docs_text += f"EXAMPLE:\n{docs['example']}\n"
        return docs_text or "No documentation found."

    # ── Cloud provider selection ──────────────────────────────────────────

    def select_cloud_provider(self, provider: str) -> str:
        provider = provider.lower().strip()
        if provider in ('aws', 'amazon'):
            self.selected_cloud_provider = "aws"
            return (
                "AWS Selected! You can now generate AWS infrastructure.\n"
                "Try: 'Generate S3 bucket with versioning' or 'Create EC2 instance with security group'"
            )
        elif provider in ('azure', 'microsoft'):
            self.selected_cloud_provider = "azure"
            return (
                "Azure Selected! You can now generate Azure infrastructure.\n"
                "Try: 'Generate storage account' or 'Create virtual machine with network'"
            )
        return f"Unknown provider '{provider}'. Please select 'aws' or 'azure'."

    # ── Tool registration ─────────────────────────────────────────────────

    def _create_tools(self):
        from langchain.tools import Tool
        return [
            Tool(
                name="select_cloud_provider",
                func=self.select_cloud_provider,
                description="Select cloud provider for infrastructure generation. Input: 'aws' or 'azure'.",
            ),
            make_generate_tool(self),
            make_modify_tool(self),
            make_push_tool(self),
            make_plan_tool(self),
            make_plan_output_tool(self),
            make_apply_tool(self),
            make_state_tool(self),
            make_destroy_tool(self),
            make_save_locally_tool(self),
            make_change_bucket_tool(self),
            make_load_code_tool(self),
            make_load_attachments_tool(self),
            make_describe_tool(self),
            make_retry_push_tool(self),
        ]

    # ── Agent executor ────────────────────────────────────────────────────

    def _create_agent(self) -> Optional[AgentExecutor]:
        if self.llm is None:
            logger.warning("Skipping agent creation — LLM is not initialised (no API key).")
            return None

        provider = getattr(self, "selected_cloud_provider", "aws")
        provider_context = (
            "AWS (~> 5.0) using official Terraform AWS provider documentation"
            if provider == "aws"
            else "Azure (~> 3.0) using official Terraform AzureRM provider documentation"
        )

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                f"""You are AutoScript-Pro, a Terraform AI Agent.

GENERAL RULES:
- Use ONLY official Terraform provider documentation from registry.terraform.io
- NEVER output raw Terraform code directly — ALWAYS use tools
- The selected provider is FIXED: {provider.upper()}
- Provider constraint: {provider_context}

GITHUB RULES:
- NEVER push code unless the user explicitly provides a GitHub URL and PAT

TOOL USAGE:
- Infrastructure creation → generate_terraform_code
- Any change or update → modify_terraform_code
- Push to GitHub → push_to_github
- Terraform plan → trigger_terraform_plan
- Get plan output → get_terraform_plan_output
- Terraform apply → trigger_terraform_apply

WORKFLOW:
1. Generate or modify code using tools
2. Push to GitHub ONLY after explicit user instruction
3. Run terraform plan before apply

Be concise, accurate, and deterministic.
""",
            ),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])

        agent = create_openai_tools_agent(llm=self.llm, tools=self.tools, prompt=prompt)
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=20,
        )

    # ── Public interface ──────────────────────────────────────────────────

    def run(self, user_input: str) -> str:
        if self.agent_executor is None:
            return "Error: AI features are unavailable — OPENAI_API_KEY is not set."
        try:
            result = self.agent_executor.invoke({"input": user_input})
            return result.get("output", "No response generated")
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            return f"Error: {str(e)}"
