from flask import Blueprint, request, jsonify
from backend.api.auth import require_auth
from backend.agent import terraform_agent

terraform_bp = Blueprint('terraform', __name__)


@terraform_bp.route('/generate', methods=['POST'])
@require_auth
def generate_terraform():
    """Generate Terraform code via the agent"""
    data = request.get_json()
    user_request = data.get('request', '')
    aws_region = data.get('region', 'us-east-1')

    if not user_request:
        return jsonify({'error': 'Please provide a request'}), 400

    try:
        response = terraform_agent.run(f"Generate Terraform code for: {user_request} in region {aws_region}")
        return jsonify({'success': True, 'files': terraform_agent.generated_files, 'agent_response': response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@terraform_bp.route('/get-files', methods=['GET'])
@require_auth
def get_current_files():
    """Return currently generated files"""
    try:
        return jsonify({'success': True, 'files': terraform_agent.generated_files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@terraform_bp.route('/modify', methods=['POST'])
@require_auth
def modify_terraform():
    """Modify existing Terraform code via the agent"""
    data = request.get_json()
    modification_request = data.get('modification_request', '')

    if not modification_request:
        return jsonify({'error': 'Please provide a modification request'}), 400

    try:
        response = terraform_agent.run(modification_request)
        return jsonify({'success': True, 'files': terraform_agent.generated_files, 'agent_response': response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@terraform_bp.route('/push', methods=['POST'])
@require_auth
def push_to_github():
    """Push generated Terraform code to GitHub"""
    data = request.get_json()
    repo_url = data.get('repo_url', '')
    github_token = data.get('github_token', '')

    if not repo_url or not github_token:
        return jsonify({'error': 'Please provide repo_url and github_token'}), 400

    try:
        response = terraform_agent.run(f"Push to GitHub: {repo_url}|{github_token}")
        return jsonify({'success': True, 'agent_response': response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@terraform_bp.route('/plan', methods=['POST'])
@require_auth
def trigger_plan():
    """Trigger a Terraform plan via GitHub Actions"""
    try:
        response = terraform_agent.run("Trigger terraform plan")
        return jsonify({'success': True, 'agent_response': response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@terraform_bp.route('/plan-output', methods=['GET'])
@require_auth
def get_plan_output():
    """Get the latest Terraform plan output"""
    try:
        response = terraform_agent.run("Get terraform plan output")
        return jsonify({'success': True, 'plan_output': terraform_agent.terraform_plan_output, 'agent_response': response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@terraform_bp.route('/apply', methods=['POST'])
@require_auth
def trigger_apply():
    """Trigger a Terraform apply via GitHub Actions"""
    try:
        response = terraform_agent.run("Trigger terraform apply")
        return jsonify({'success': True, 'agent_response': response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
