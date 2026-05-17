import re
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def format_terraform_code(code: str) -> str:
    """Basic Terraform code formatting — fixes indentation"""
    if not code or not code.strip():
        return code

    lines = code.split('\n')
    formatted_lines = []
    indent_level = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            formatted_lines.append('')
            continue

        if stripped == '}':
            indent_level = max(0, indent_level - 1)

        formatted_lines.append('  ' * indent_level + stripped)

        if stripped.endswith('{'):
            indent_level += 1

    return '\n'.join(formatted_lines)


def validate_terraform_code(generated_files: Dict[str, str]) -> Dict[str, Any]:
    """Validate generated Terraform code for common issues"""
    result = {'has_errors': False, 'errors': [], 'warnings': []}

    try:
        main_tf = generated_files.get('main.tf', '')
        variables_tf = generated_files.get('variables.tf', '')

        used_variables = set(re.findall(r'var\.(\w+)', main_tf))

        declared_variables = set()
        for line in variables_tf.split('\n'):
            if line.strip().startswith('variable "'):
                declared_variables.add(line.split('"')[1])

        undeclared = used_variables - declared_variables
        if undeclared:
            result['has_errors'] = True
            result['errors'].append(f"Undeclared variables: {', '.join(undeclared)}")

        unused = declared_variables - used_variables
        if unused:
            result['warnings'].append(f"Unused variables: {', '.join(unused)}")

        for filename, content in generated_files.items():
            if filename.endswith('.tf'):
                open_braces = content.count('{')
                close_braces = content.count('}')
                if open_braces != close_braces:
                    result['has_errors'] = True
                    result['errors'].append(
                        f"{filename}: Unmatched braces ({open_braces} open, {close_braces} close)"
                    )

                for i, line in enumerate(content.split('\n'), 1):
                    if '=' in line and not line.strip().startswith('#'):
                        if not any(k in line for k in ['resource "', 'variable "', 'output "']):
                            parts = line.split('=', 1)
                            if len(parts) == 2:
                                value = parts[1].strip()
                                if value and not (
                                    value.startswith('"') or value.startswith('[') or
                                    value.startswith('{') or value.isdigit() or
                                    value.startswith('var.') or value.startswith('data.') or
                                    value.startswith('aws_') or value in ['true', 'false']
                                ):
                                    result['warnings'].append(
                                        f"{filename}:{i}: Possible unquoted string: {value}"
                                    )

    except Exception as e:
        logger.error(f"Validation error: {e}")
        result['warnings'].append(f"Validation process error: {str(e)}")

    return result


def validate_file_consistency(files: Dict[str, str]) -> List[str]:
    """Check that variables used in main.tf are declared in variables.tf"""
    issues = []

    main_tf = files.get('main.tf', '')
    variables_tf = files.get('variables.tf', '')

    used_variables = set(re.findall(r'var\.(\w+)', main_tf))

    declared_variables = set()
    for line in variables_tf.split('\n'):
        if line.strip().startswith('variable "'):
            declared_variables.add(line.strip().split('"')[1])

    undeclared = used_variables - declared_variables
    if undeclared:
        issues.append(f"Variables used but not declared: {', '.join(undeclared)}")

    unused = declared_variables - used_variables
    if unused:
        issues.append(f"Variables declared but not used: {', '.join(unused)}")

    return issues


def auto_fix_consistency_issues(files: Dict[str, str], issues: List[str]) -> Dict[str, str]:
    """Auto-add missing variable declarations to variables.tf"""
    fixed_files = files.copy()

    for issue in issues:
        if "Variables used but not declared" in issue:
            var_names_str = re.findall(r'Variables used but not declared: (.+)', issue)
            if var_names_str:
                vars_to_add = [v.strip() for v in var_names_str[0].split(',')]
                variables_tf = fixed_files.get('variables.tf', '')
                for var_name in vars_to_add:
                    if var_name not in variables_tf:
                        variables_tf += f'\nvariable "{var_name}" {{\n  description = "Auto-generated variable for {var_name}"\n  type        = string\n}}\n'
                fixed_files['variables.tf'] = variables_tf
                logger.info(f"Auto-added missing variables: {', '.join(vars_to_add)}")

    return fixed_files
