from flask import Blueprint, request, jsonify
from backend.api.auth import require_auth
from backend.agent import terraform_agent

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/agent', methods=['POST'])
@require_auth
def agent_interaction():
    """Direct agent interaction — passes input straight to the LangChain executor"""
    data = request.get_json()
    user_input = data.get('input', '')
    if not user_input:
        return jsonify({'error': 'Please provide input'}), 400

    try:
        response = terraform_agent.run(user_input)
        return jsonify({'success': True, 'response': response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/chat', methods=['POST'])
def chat():
    """
    General chat interface with smart keyword routing.
    Common intents are dispatched directly to the appropriate tool
    without going through the full LLM reasoning loop.
    """
    data = request.get_json()
    message = data.get('message', '')
    if not message:
        return jsonify({'error': 'Please provide a message'}), 400

    msg_lower = message.lower().strip()

    # ── Cloud provider selection ──────────────────────────────────────────
    for keyword, provider in [
        (['select aws', 'choose aws', 'use aws', 'aws provider'], 'aws'),
        (['select azure', 'choose azure', 'use azure', 'azure provider'], 'azure'),
    ]:
        if any(k in msg_lower for k in keyword):
            result = terraform_agent.select_cloud_provider(provider)
            return jsonify({'success': True, 'response': result, 'files': {}, 'action': 'cloud_provider_selected', 'provider': provider})

    # ── Describe existing code ────────────────────────────────────────────
    describe_keywords = ['describe existing code', 'describe the code', 'explain the code',
                         'what does the code do', 'read the code', 'understand the code']
    if any(k in msg_lower for k in describe_keywords):
        tool = _get_tool('describe_existing_code')
        if tool:
            result = tool.func()
            return jsonify({'success': True, 'response': result, 'files': _current_files(), 'action': 'describe_existing_code'})

    # ── GitHub push (URL|token format) ───────────────────────────────────
    if 'github.com' in message and '|' in message:
        parts = message.split('|')
        if len(parts) == 2:
            tool = _get_tool('push_to_github')
            if tool:
                result = tool.func(f"{parts[0].strip()}|{parts[1].strip()}")
                return jsonify({'success': True, 'response': result, 'files': _current_files(), 'action': 'github_push'})

    # ── Get plan output ───────────────────────────────────────────────────
    if any(k in msg_lower for k in ['get plan output', 'show plan output', 'terraform plan output', 'existing terraform plan']):
        tool = _get_tool('get_terraform_plan_output')
        if tool:
            result = tool.func("")
            return jsonify({'success': True, 'response': result, 'files': _current_files(), 'action': 'get_plan_output'})

    # ── Trigger plan ──────────────────────────────────────────────────────
    if any(k in msg_lower for k in ['run terraform plan', 'trigger terraform plan', 'run plan']):
        tool = _get_tool('trigger_terraform_plan')
        if tool:
            result = tool.func("")
            return jsonify({'success': True, 'response': result, 'files': _current_files(), 'action': 'terraform_plan'})

    # ── Trigger apply / deploy ────────────────────────────────────────────
    if any(k in msg_lower for k in ['terraform apply', 'apply infrastructure', 'deploy']):
        tool = _get_tool('trigger_terraform_apply')
        if tool:
            result = tool.func("")
            return jsonify({'success': True, 'response': result, 'files': _current_files(), 'action': 'terraform_apply'})

    # ── Default: full agent reasoning ────────────────────────────────────
    try:
        response = terraform_agent.run(message)
        return jsonify({'success': True, 'response': response, 'files': _current_files()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_tool(name: str):
    return next((t for t in terraform_agent.tools if t.name == name), None)


def _current_files() -> dict:
    return getattr(terraform_agent, 'generated_files', {})
