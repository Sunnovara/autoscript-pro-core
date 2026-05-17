#!/usr/bin/env python3
"""
Startup script for AutoScript-Pro Terraform AI Agent
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()


def check_environment():
    """Warn if the OpenAI API key is missing (non-fatal — app still starts)"""
    if not os.getenv('OPENAI_API_KEY'):
        print("WARNING: OPENAI_API_KEY is not set.")
        print("  The app will start but AI features will not work.")
        print("  Copy .env.template to .env and add your key.")
        return False
    print("Environment variables OK.")
    return True


def test_ai_agent():
    """Verify agent imports and initialises without errors"""
    try:
        from backend.agent import terraform_agent
        print("AI Agent initialised successfully.")
        return True
    except Exception as e:
        print(f"AI Agent initialisation failed: {e}")
        return False


def main():
    print("Starting AutoScript-Pro...")
    print("=" * 50)

    check_environment()

    print("Testing AI Agent...")
    if not test_ai_agent():
        print("Agent test failed, but continuing anyway...")

    print("Starting web server...")
    print("Open your browser at: http://localhost:5001")
    print("=" * 50)

    from backend.api.app import app
    host_ip = os.environ.get('HOST_IP', '0.0.0.0')
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host=host_ip, port=port)


if __name__ == '__main__':
    main()
