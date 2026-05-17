import json
import logging
from langchain.tools import Tool

from backend.services.code_validator import format_terraform_code, validate_terraform_code
from backend.services.file_builder import (
    create_terraform_tfvars,
    create_readme,
    create_terraform_gitignore,
)

logger = logging.getLogger(__name__)


def make_generate_tool(agent) -> Tool:
    """
    Factory that returns the generate_terraform_code LangChain Tool.
    The inner function closes over `agent` to read/write agent state.
    """

    def generate_terraform_code(input_str: str) -> str:
        """Generate Terraform code from a natural-language description"""
        try:
            parts = input_str.split("|")
            user_request = parts[0].strip()
            default_region = "us-east-1" if agent.selected_cloud_provider == "aws" else "East US"
            region = parts[1].strip() if len(parts) > 1 else default_region

            real_time_docs = agent._get_resource_documentation(user_request)
            provider = agent.selected_cloud_provider

            if provider not in ("aws", "azure"):
                return f"Error: Unsupported provider '{provider}'. Select 'aws' or 'azure' first."

            modular_keywords = ['modular', 'module', 'modules', 'modular structure', 'separate modules']
            is_modular = any(kw in user_request.lower() for kw in modular_keywords)

            system_prompt = _build_generation_prompt(provider, is_modular, region, real_time_docs, user_request)

            response = agent.llm.invoke(system_prompt)
            content = _strip_json_fences(response.content.strip())
            generated_files = json.loads(content)

            for filename, code in list(generated_files.items()):
                if filename.endswith('.tf'):
                    code = code.replace('\\n', '\n').replace('\\t', '\t')
                    generated_files[filename] = format_terraform_code(code)

            validation = validate_terraform_code(generated_files)
            if validation['has_errors']:
                logger.warning(f"Generated code has validation issues: {validation['errors']}")

            generated_files["terraform.tfvars"] = create_terraform_tfvars(generated_files)
            generated_files["README.md"] = create_readme(user_request, region, generated_files, provider)
            generated_files[".gitignore"] = create_terraform_gitignore()

            agent.generated_files = generated_files
            file_list = ', '.join(generated_files.keys())
            return f"Successfully generated Terraform code with {len(generated_files)} files: {file_list}"

        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            return f"Error generating code: {str(e)}"

    return Tool(
        name="generate_terraform_code",
        func=generate_terraform_code,
        description=(
            f"Generate Terraform code for {agent.selected_cloud_provider.upper()} infrastructure. "
            "Input format: 'description|region' or just 'description'. "
            "Example: 'Create S3 bucket with versioning|us-east-1'"
        ),
    )


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _strip_json_fences(content: str) -> str:
    if content.startswith('```json'):
        return content.split('```json')[1].split('```')[0].strip()
    if content.startswith('```'):
        return content.split('```')[1].split('```')[0].strip()
    return content


def _build_generation_prompt(provider: str, is_modular: bool, region: str, real_time_docs: str, user_request: str) -> str:
    if provider == "aws":
        return _aws_prompt(is_modular, region, real_time_docs, user_request)
    return _azure_prompt(is_modular, region, user_request)


def _aws_prompt(is_modular: bool, region: str, real_time_docs: str, user_request: str) -> str:
    if is_modular:
        return f"""
You are an expert Terraform code generator for AWS infrastructure using MODULAR STRUCTURE with the official HashiCorp AWS Provider.

CRITICAL REQUIREMENTS:
1. Use ONLY official Terraform AWS Provider syntax from https://registry.terraform.io/providers/hashicorp/aws/latest/docs
2. Create SEPARATE MODULE DIRECTORIES for each logical component
3. Use AWS provider version (~> 5.0)
4. Target AWS region: {region}
5. NEVER reference Azure resources

OFFICIAL TERRAFORM AWS PROVIDER DOCUMENTATION:
{real_time_docs}

USER REQUEST: {user_request}

Create root files (main.tf, variables.tf, outputs.tf, provider.tf, terraform.tfvars) plus
modules/[component_name]/main.tf, variables.tf, outputs.tf for each module.

Provider.tf must use:
terraform {{
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
  }}
}}
provider "aws" {{
  region = var.aws_region
}}

Respond with VALID JSON containing filenames as keys and Terraform code as values.
"""
    return f"""
You are an expert Terraform code generator for AWS infrastructure using the official HashiCorp AWS Provider.

CRITICAL REQUIREMENTS:
1. Use ONLY official Terraform AWS Provider syntax
2. Use AWS provider version (~> 5.0)
3. Include ALL required arguments for each resource
4. Target AWS region: {region}
5. NEVER reference Azure resources
6. ONLY create resources explicitly mentioned in the user request

OFFICIAL TERRAFORM AWS PROVIDER DOCUMENTATION:
{real_time_docs}

USER REQUEST: {user_request}

Provider.tf must use:
terraform {{
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
  }}
}}
provider "aws" {{
  region = var.aws_region
}}

For S3 buckets use separate resources for versioning and encryption configuration.

Validation checklist:
- All resources have required arguments
- All variables used in main.tf are declared in variables.tf
- No syntax errors or unmatched braces

Respond with VALID JSON. Always include: main.tf, variables.tf, outputs.tf, provider.tf
"""


def _azure_prompt(is_modular: bool, region: str, user_request: str) -> str:
    if is_modular:
        return f"""
You are an expert Terraform code generator for Azure infrastructure using MODULAR STRUCTURE with the official AzureRM Provider.

CRITICAL REQUIREMENTS:
1. Use AzureRM provider version (~> 3.0) — NEVER version 5.0
2. Create SEPARATE MODULE DIRECTORIES for each component mentioned in the request
3. Target Azure region: {region}
4. NEVER reference AWS resources
5. ONLY create modules for resources explicitly mentioned

USER REQUEST: {user_request}

Create root files plus modules/[component]/main.tf, variables.tf, outputs.tf for each requested component.

Provider.tf must use:
terraform {{
  required_providers {{
    azurerm = {{
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }}
  }}
}}
provider "azurerm" {{
  features {{}}
}}

Respond with VALID JSON containing filenames as keys and Terraform code as values.
"""
    return f"""
You are an expert Terraform code generator for Azure infrastructure using the official AzureRM Provider.

CRITICAL REQUIREMENTS:
1. Use AzureRM provider version (~> 3.0) — NEVER version 5.0
2. Use azurerm_ prefix for ALL resources
3. Target Azure region: {region}
4. NEVER reference AWS resources
5. ONLY create resources explicitly mentioned in the user request

USER REQUEST: {user_request}

Provider.tf must use:
terraform {{
  required_providers {{
    azurerm = {{
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }}
  }}
}}
provider "azurerm" {{
  features {{}}
}}

Respond with VALID JSON. Always include: main.tf, variables.tf, outputs.tf, provider.tf
"""
