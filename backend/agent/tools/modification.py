import re
import json
import logging
from langchain.tools import Tool

from backend.services.code_validator import format_terraform_code, validate_file_consistency, auto_fix_consistency_issues
from backend.services.file_builder import (
    create_readme,
    extract_value_updates_from_request,
    create_terraform_tfvars_with_updates,
)

logger = logging.getLogger(__name__)


def make_modify_tool(agent) -> Tool:
    """Factory returning the modify_terraform_code LangChain Tool"""

    def modify_terraform_code(modification_request: str) -> str:
        """Modify existing Terraform code based on a natural-language description of the change"""
        try:
            if not agent.generated_files:
                return "Error: No code to modify. Generate code first."

            logger.info(f"Modifying Terraform code: {modification_request}")

            current_code = "\n\n".join(
                f"# {fname}\n{code}" for fname, code in agent.generated_files.items()
            )

            current_resources = agent._extract_resource_types_from_code(current_code)
            docs_text = agent._get_documentation_for_resources(current_resources)

            provider = getattr(agent, 'selected_cloud_provider', 'aws')
            has_modules = any('modules/' in f for f in agent.generated_files)
            system_prompt = _build_modification_prompt(provider, docs_text, current_code, modification_request, has_modules)

            response = agent.llm.invoke(system_prompt)
            content = _strip_json_fences(response.content.strip())
            logger.info(f"LLM response (first 500 chars): {content[:500]}")
            modified_files = json.loads(content)
            logger.info(f"Parsed {len(modified_files)} files from LLM response")

            # Preserve any core files the LLM omitted
            for core_file in ['main.tf', 'variables.tf', 'outputs.tf', 'provider.tf']:
                if core_file not in modified_files and core_file in agent.generated_files:
                    modified_files[core_file] = agent.generated_files[core_file]

            for filename, code in list(modified_files.items()):
                if filename.endswith('.tf'):
                    code = code.replace('\\n', '\n').replace('\\t', '\t')
                    modified_files[filename] = format_terraform_code(code)

            # Extract any explicit value changes from the request
            value_updates = extract_value_updates_from_request(modification_request, modified_files)

            # Fallback extraction for bucket names / regions / environments
            if not value_updates:
                aws_res = re.findall(r'aws-[\w-]+', modification_request)
                if aws_res:
                    value_updates["bucket_name"] = f'"{aws_res[-1]}"'
                regions = re.findall(r'us-[\w-]+|eu-[\w-]+|ap-[\w-]+', modification_request)
                if regions:
                    value_updates["region"] = f'"{regions[-1]}"'
                envs = re.findall(r'\b(dev|test|staging|prod|production)\b', modification_request.lower())
                if envs:
                    value_updates["environment"] = f'"{envs[-1]}"'

            modified_files["terraform.tfvars"] = create_terraform_tfvars_with_updates(
                modified_files, value_updates, agent.generated_files
            )

            issues = validate_file_consistency(modified_files)
            if issues:
                logger.warning(f"Consistency issues: {issues}")
                modified_files = auto_fix_consistency_issues(modified_files, issues)

            modified_files["README.md"] = create_readme(modification_request, "us-east-1", modified_files, provider)

            agent.generated_files = modified_files
            return (
                f"Successfully modified Terraform code. Updated {len(modified_files)} files.\n"
                "All files updated consistently."
            )

        except Exception as e:
            logger.error(f"Code modification failed: {e}")
            if "json" in str(e).lower():
                return f"Error: AI response was not valid JSON. Try rephrasing your request. ({str(e)})"
            return f"Error modifying code: {str(e)}. Please try rephrasing your modification request."

    return Tool(
        name="modify_terraform_code",
        func=modify_terraform_code,
        description="Modify existing Terraform code. Input: description of the change. Example: 'Add encryption to the S3 bucket'",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_json_fences(content: str) -> str:
    if content.startswith('```json'):
        return content.split('```json')[1].split('```')[0].strip()
    if content.startswith('```'):
        return content.split('```')[1].split('```')[0].strip()
    return content


def _build_modification_prompt(
    provider: str,
    docs_text: str,
    current_code: str,
    modification_request: str,
    has_modules: bool,
) -> str:
    provider_name = "AzureRM" if provider == "azure" else "AWS"
    provider_docs = (
        "https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs"
        if provider == "azure"
        else "https://registry.terraform.io/providers/hashicorp/aws/latest/docs"
    )
    provider_version = "~> 3.0" if provider == "azure" else "~> 5.0"
    resource_prefix = "azurerm_" if provider == "azure" else "aws_"

    modular_note = ""
    if has_modules:
        modular_note = """
CRITICAL: The current code has a MODULAR STRUCTURE.
- PRESERVE the modular structure when making modifications.
- Update the appropriate module files when modifying resources.
"""

    return f"""
You are an expert Terraform code modifier using the official {provider_name} Provider.

CRITICAL REQUIREMENTS:
1. Use ONLY official {provider_name} Provider syntax from {provider_docs}
2. Maintain compatibility with provider version {provider_version}
3. CURRENT PROVIDER: {provider.upper()} — use {resource_prefix} prefix for all resources
4. NEVER reference the other cloud provider

{modular_note}

OFFICIAL {provider_name.upper()} DOCUMENTATION:
{docs_text}

CURRENT CODE:
{current_code}

MODIFICATION REQUEST: {modification_request}

INSTRUCTIONS:
- NEVER ask for clarification — ALWAYS make the change directly
- Update ALL relevant files consistently (main.tf, variables.tf, outputs.tf, modules/)
- If you change a resource name, update every reference across all files
- ALWAYS return complete code for ALL files
- Do NOT include terraform.tfvars or README.md — they are regenerated automatically

Respond with VALID JSON:
{{
  "main.tf": "...",
  "variables.tf": "...",
  "outputs.tf": "...",
  "provider.tf": "..."
}}
"""
