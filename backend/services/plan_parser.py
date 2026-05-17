import io
import zipfile
import logging

logger = logging.getLogger(__name__)


def extract_plan_from_logs(logs: str) -> str:
    """Extract terraform plan output from GitHub Actions log text"""
    try:
        lines = logs.split('\n')
        plan_lines = []
        in_plan_section = False

        for line in lines:
            if "##[group]Terraform Plan Output" in line:
                in_plan_section = True
                continue
            if in_plan_section and "##[endgroup]" in line:
                break
            if not in_plan_section and "terraform plan -no-color" in line:
                in_plan_section = True
                continue
            if in_plan_section and ("##[group]" in line or "Post job cleanup" in line or "##[section]" in line):
                break

            if in_plan_section:
                clean_line = line
                if clean_line and len(clean_line) > 30 and clean_line[4] == '-' and clean_line[7] == '-':
                    if 'T' in clean_line[:30] and 'Z' in clean_line[:30]:
                        parts = clean_line.split(' ', 1)
                        if len(parts) > 1:
                            clean_line = parts[1]
                if clean_line.strip() and not clean_line.startswith('##['):
                    plan_lines.append(clean_line)

        if not plan_lines:
            return "No terraform plan output found in logs. The workflow might still be running or failed."

        cleaned = []
        for line in '\n'.join(plan_lines).split('\n'):
            if line.strip():
                cleaned.append(line)
            elif cleaned and cleaned[-1].strip():
                cleaned.append('')

        while cleaned and not cleaned[-1].strip():
            cleaned.pop()

        final = '\n'.join(cleaned)
        if len(final) < 50:
            return "Plan output seems incomplete. The workflow might still be running. Please try again."
        return final

    except Exception as e:
        logger.error(f"Failed to extract plan from logs: {e}")
        return f"Error extracting plan output: {str(e)}"


def extract_plan_summary(plan_output: str) -> str:
    """Return a short human-readable summary from a terraform plan output string"""
    try:
        summary_lines = []
        for line in plan_output.split('\n'):
            if 'Plan:' in line and ('to add' in line or 'to change' in line or 'to destroy' in line):
                summary_lines.append(f"**{line.strip()}**")
            elif 'No changes' in line and 'infrastructure is up-to-date' in line:
                summary_lines.append(f"**{line.strip()}**")
            elif line.strip().startswith(('+ ', '- ', '~ ')):
                if len(summary_lines) < 10:
                    resource_line = line.strip()
                    if '+ ' in resource_line:
                        summary_lines.append(f"Create: {resource_line[2:].split()[0]}")
                    elif '- ' in resource_line:
                        summary_lines.append(f"Destroy: {resource_line[2:].split()[0]}")
                    elif '~ ' in resource_line:
                        summary_lines.append(f"Modify: {resource_line[2:].split()[0]}")

        if summary_lines:
            return "**Plan Summary:**\n" + "\n".join(summary_lines[:8])
        return "**Plan Summary:** Plan output processed. Check the plan-output tab for details."

    except Exception as e:
        logger.error(f"Error extracting plan summary: {e}")
        return "**Plan Summary:** Plan output available in the plan-output tab."


def extract_plan_from_artifact(zip_content: bytes) -> str:
    """Extract terraform plan text from a downloaded GitHub Actions artifact zip"""
    try:
        zip_buffer = io.BytesIO(zip_content)
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            file_list = zip_file.namelist()
            logger.info(f"Files in artifact zip: {file_list}")

            plan_file_names = [
                'terraform-plan-output.txt', 'plan-output.txt',
                'terraform_plan_output.txt', 'plan.txt',
                'terraform-plan.txt', 'output.txt'
            ]

            plan_content = ""
            for filename in file_list:
                if any(pn in filename.lower() for pn in plan_file_names):
                    with zip_file.open(filename) as f:
                        plan_content = f.read().decode('utf-8')
                    break

            if not plan_content:
                for filename in file_list:
                    if filename.endswith('.txt'):
                        with zip_file.open(filename) as f:
                            plan_content = f.read().decode('utf-8')
                        break

            if plan_content:
                cleaned = []
                for line in plan_content.split('\n'):
                    clean_line = line
                    if clean_line and len(clean_line) > 30 and clean_line[4] == '-' and clean_line[7] == '-':
                        if 'T' in clean_line[:30] and 'Z' in clean_line[:30]:
                            parts = clean_line.split(' ', 1)
                            if len(parts) > 1:
                                clean_line = parts[1]
                    if clean_line.strip() and not clean_line.startswith('##['):
                        cleaned.append(clean_line)
                return '\n'.join(cleaned)

            return "No plan output found in artifact"

    except Exception as e:
        logger.error(f"Error extracting plan from artifact: {e}")
        return f"Error extracting plan from artifact: {str(e)}"
