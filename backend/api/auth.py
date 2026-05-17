import os
from flask import session, jsonify

DEV_MODE = True


def load_credentials() -> dict:
    """Load username:password pairs from the INITIAL_USERS env var"""
    credentials = {}
    for user in os.environ.get("INITIAL_USERS", "").split(","):
        try:
            username, password = user.split(":")
            credentials[username.strip()] = password.strip()
        except ValueError:
            continue
    return credentials


VALID_CREDENTIALS = load_credentials()


def require_auth(f):
    """Decorator: skip auth in DEV_MODE, otherwise require session flag"""
    def decorated_function(*args, **kwargs):
        if not DEV_MODE and not session.get("authenticated"):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function
