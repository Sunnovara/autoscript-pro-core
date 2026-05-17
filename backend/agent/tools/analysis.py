import re
import logging
from pydantic import BaseModel
from langchain.tools import Tool, StructuredTool

from backend.services.file_builder import create_terraform_tfvars_with_updates, create_readme

logger = logging.getLogger(__name__)


class _EmptyInput(BaseModel):
    """No input required"""
    pass


def make_describe_tool(agent) -> StructuredTool:
    """Factory for the describe_existing_code StructuredTool"""

    def describe_existing_code() -> str:
        codebase = agent.existing_code if agent.existing_code else agent.generated_files
        if not codebase:
            return "There is no Terraform code available to describe."

        analysis = "**Code Analysis Report**\n\n"
        for filename, content in codebase.items():
            analysis += f"**{filename}:**\n"

            resources = [
                f"{m.group(1)} ({m.group(2)})"
                for line in content.split('\n')
                if line.strip().startswith('resource "')
                for m in [re.search(r'resource "([^"]+)" "([^"]+)"', line)]
                if m
            ]
            if resources:
                analysis += f"  Resources: {', '.join(resources)}\n"

            variables = [
                m.group(1)
                for line in content.split('\n')
                if line.strip().startswith('variable "')
                for m in [re.search(r'variable "([^"]+)"', line)]
                if m
            ]
            if variables:
                analysis += f"  Variables: {', '.join(variables)}\n"

            outputs = [
                m.group(1)
                for line in content.split('\n')
                if line.strip().startswith('output "')
                for m in [re.search(r'output "([^"]+)"', line)]
                if m
            ]
            if outputs:
                analysis += f"  Outputs: {', '.join(outputs)}\n"

            analysis += "\n"

        total_resources = sum(len(re.findall(r'resource "', c)) for c in codebase.values())
        analysis += (
            f"**Summary:** {len(codebase)} files, {total_resources} resources total\n"
            f"**Provider:** {agent.selected_cloud_provider.upper()}\n\n"
            "Next steps: modify the code, push to GitHub, or run terraform plan."
        )
        return analysis

    return StructuredTool.from_function(
        name="describe_existing_code",
        func=describe_existing_code,
        description="Describe and analyse the existing Terraform code that is currently loaded.",
        args_schema=_EmptyInput,
    )


def make_load_code_tool(agent) -> Tool:
    """Factory for the load_existing_code Tool"""

    def load_existing_code(code_files) -> str:
        try:
            if not code_files:
                return "Error: No code files provided."

            agent.existing_code = code_files

            detected_provider = "unknown"
            for content in code_files.values():
                if 'provider "aws"' in content or 'aws_' in content:
                    detected_provider = "aws"
                    break
                elif 'provider "azurerm"' in content or 'azurerm_' in content:
                    detected_provider = "azure"
                    break

            if detected_provider != "unknown":
                agent.selected_cloud_provider = detected_provider

            file_list = ', '.join(code_files.keys())
            result = (
                f"Code Loaded Successfully!\n"
                f"Files loaded: {len(code_files)}\n"
                f"Files: {file_list}\n"
            )
            if detected_provider != "unknown":
                result += f"Detected provider: {detected_provider.upper()}\n"
            result += "\nYou can now: describe the code, modify it, or push to GitHub."
            return result

        except Exception as e:
            logger.error(f"Loading existing code failed: {e}")
            return f"Error loading code: {str(e)}"

    return Tool(
        name="load_existing_code",
        func=load_existing_code,
        description="Load existing Terraform code files for analysis and modification. Input: dict of filename->content.",
    )


def make_load_attachments_tool(agent) -> Tool:
    """Factory for the load_attachments Tool"""

    def load_attachments(attachments) -> str:
        try:
            if not attachments:
                return "Error: No attachments provided."
            agent.attachments = attachments
            return (
                f"Attachments Loaded!\n"
                f"Files: {', '.join(attachments.keys())}\n"
                "These files are available for reference when generating infrastructure."
            )
        except Exception as e:
            logger.error(f"Loading attachments failed: {e}")
            return f"Error loading attachments: {str(e)}"

    return Tool(
        name="load_attachments",
        func=load_attachments,
        description="Load attachments (images, PDFs, etc.) for reference. Input: dict of filename->binary_data.",
    )


def make_change_bucket_tool(agent) -> Tool:
    """Factory for the change_bucket_name Tool"""

    def change_bucket_name(bucket_name: str) -> str:
        try:
            bucket_name = bucket_name.strip()
            if not agent.generated_files:
                return "Error: No code to modify. Generate code first."

            modified_files = agent.generated_files.copy()

            main_tf = modified_files.get('main.tf', '')
            main_tf = re.sub(
                r'(resource\s+"aws_s3_bucket"\s+"[^"]+"\s+\{\s+)bucket\s+=\s+[^\n]+',
                r'\1bucket = var.bucket_name',
                main_tf,
            )
            modified_files['main.tf'] = main_tf

            variables_tf = modified_files.get('variables.tf', '')
            if 'variable "bucket_name"' in variables_tf:
                variables_tf = re.sub(
                    r'(variable\s+"bucket_name"[^}]*default\s+=\s+")[^"]+(")',
                    f'\\g<1>{bucket_name}\\g<2>',
                    variables_tf,
                )
            else:
                variables_tf += (
                    f'\nvariable "bucket_name" {{\n'
                    f'  description = "Name of the S3 bucket"\n'
                    f'  type        = string\n'
                    f'  default     = "{bucket_name}"\n'
                    f'}}\n'
                )
            modified_files['variables.tf'] = variables_tf

            modified_files["terraform.tfvars"] = create_terraform_tfvars_with_updates(
                modified_files, {"bucket_name": f'"{bucket_name}"'}, agent.generated_files
            )
            modified_files["README.md"] = create_readme(
                f"Create S3 bucket named {bucket_name}", "us-east-1", modified_files,
                agent.selected_cloud_provider
            )

            agent.generated_files = modified_files
            return (
                f"Successfully changed S3 bucket name to '{bucket_name}'. "
                f"Updated {len(modified_files)} files."
            )

        except Exception as e:
            logger.error(f"Bucket name change failed: {e}")
            return f"Error changing bucket name: {str(e)}"

    return Tool(
        name="change_bucket_name",
        func=change_bucket_name,
        description="Change the S3 bucket name directly. Input: new bucket name. Example: 'aws-my-new-bucket'",
    )


def make_save_locally_tool(agent) -> Tool:
    """Factory for the save_files_locally Tool"""

    def save_files_locally(input_str: str = "") -> str:
        import os
        output_dir = "generated_terraform"
        try:
            os.makedirs(output_dir, exist_ok=True)
            saved = []
            for filename, content in agent.generated_files.items():
                file_path = os.path.join(output_dir, filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                saved.append(filename)
            return f"Saved {len(saved)} files to '{output_dir}': {', '.join(saved)}"
        except Exception as e:
            logger.error(f"Error saving files: {e}")
            return f"Error saving files: {str(e)}"

    return Tool(
        name="save_files_locally",
        func=save_files_locally,
        description="Save generated Terraform files to the local generated_terraform/ directory. No input required.",
    )


def make_retry_push_tool(agent) -> Tool:
    """Factory for the retry_github_push Tool"""

    def retry_github_push(input_str: str = "") -> str:
        if not agent.github_token or not agent.github_repo_url:
            return "No stored GitHub credentials. Provide repository URL and token first."
        if not agent.generated_files:
            return "No files to push. Generate Terraform code first."

        from backend.agent.tools.github_tools import make_push_tool
        push_tool = make_push_tool(agent)
        return push_tool.func(f"{agent.github_repo_url}|{agent.github_token}")

    return Tool(
        name="retry_github_push",
        func=retry_github_push,
        description="Retry GitHub push using previously stored credentials. No input required.",
    )
