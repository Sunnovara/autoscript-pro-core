import os
from flask import Flask, send_from_directory
from dotenv import load_dotenv

load_dotenv()

from backend.api.routes.chat import chat_bp
from backend.api.routes.terraform import terraform_bp
from backend.api.routes.files import files_bp

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Register blueprints
app.register_blueprint(chat_bp)
app.register_blueprint(terraform_bp)
app.register_blueprint(files_bp)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    """Serve the React SPA from web-ui/dist for all non-API routes"""
    web_ui_path = os.path.join(os.getcwd(), "web-ui", "dist")
    if path and os.path.exists(os.path.join(web_ui_path, path)):
        return send_from_directory(web_ui_path, path)
    return send_from_directory(web_ui_path, "index.html")


if __name__ == '__main__':
    from backend.api.auth import VALID_CREDENTIALS
    host_ip = os.environ.get('HOST_IP', '0.0.0.0')
    port = int(os.environ.get('PORT', 5001))

    print(f"Starting AutoScript-Pro on {host_ip}:{port}")
    print(f"Available users: {', '.join(VALID_CREDENTIALS.keys()) or 'DEV_MODE (no auth)'}")
    print(f"Access URL: http://{host_ip}:{port}")

    app.run(debug=True, host=host_ip, port=port)
