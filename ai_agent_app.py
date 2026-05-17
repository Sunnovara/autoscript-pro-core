# This file is a compatibility shim.
# All Flask routes and app factory have been moved to backend/api/.
#
# backend/api/app.py           — Flask factory, blueprint registration, SPA serving
# backend/api/auth.py          — load_credentials, require_auth decorator
# backend/api/routes/chat.py   — /chat, /agent routes
# backend/api/routes/terraform.py — /generate, /get-files, /modify, /push, /plan, /plan-output, /apply
# backend/api/routes/files.py  — /upload, /direct-push, /logout routes

from backend.api.app import app

__all__ = ["app"]
