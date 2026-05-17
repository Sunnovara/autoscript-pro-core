from flask import Blueprint, request, jsonify, session
from werkzeug.utils import secure_filename
from backend.api.auth import require_auth
from backend.agent import terraform_agent

files_bp = Blueprint('files', __name__)


@files_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})


@files_bp.route('/upload', methods=['POST'])
@require_auth
def upload_files():
    """Accept .tf/.hcl/.json/.txt files and load them into the agent"""
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400

    uploaded = request.files.getlist('files')
    if not uploaded:
        return jsonify({'error': 'No files selected'}), 400

    code_files = {}
    attachments = {}

    for file in uploaded:
        if not file.filename:
            continue
        filename = secure_filename(file.filename)
        content = file.read()

        if filename.endswith(('.tf', '.hcl', '.json', '.txt')):
            try:
                code_files[filename] = content.decode('utf-8')
            except UnicodeDecodeError:
                attachments[filename] = content
        else:
            attachments[filename] = content

    response_parts = []

    if code_files:
        tool = next((t for t in terraform_agent.tools if t.name == "load_existing_code"), None)
        if tool:
            response_parts.append(tool.func(code_files))

    if attachments:
        tool = next((t for t in terraform_agent.tools if t.name == "load_attachments"), None)
        if tool:
            response_parts.append(tool.func(attachments))

    if not response_parts:
        return jsonify({'error': 'No valid files uploaded'}), 400

    display_files = (
        terraform_agent.existing_code
        if hasattr(terraform_agent, 'existing_code') and terraform_agent.existing_code
        else terraform_agent.generated_files
    )

    return jsonify({
        'success': True,
        'response': "\n\n".join(response_parts),
        'files': display_files,
    })


@files_bp.route('/direct-push', methods=['POST'])
@require_auth
def direct_push():
    """Push to GitHub using credentials provided in the request body"""
    data = request.get_json()
    repo_url = data.get('repo_url')
    github_token = data.get('github_token')

    if not repo_url or not github_token:
        return jsonify({'error': 'Repo URL and token required'}), 400

    push_tool = next((t for t in terraform_agent.tools if t.name == "push_to_github"), None)
    if not push_tool:
        return jsonify({'error': 'Push tool not found'}), 500

    try:
        result = push_tool.func(f"{repo_url}|{github_token}")
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
