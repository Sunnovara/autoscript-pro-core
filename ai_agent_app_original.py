# This file is a compatibility shim (was the original Flask app before refactoring).
# All routes from this file have been migrated to backend/api/routes/.
#
# Routes previously defined here and their new locations:
#   GET  /                  → backend/api/app.py (serve_react)
#   POST /agent             → backend/api/routes/chat.py
#   POST /chat              → backend/api/routes/chat.py
#   POST /generate          → backend/api/routes/terraform.py
#   GET  /get-files         → backend/api/routes/terraform.py
#   POST /modify            → backend/api/routes/terraform.py
#   POST /push              → backend/api/routes/terraform.py
#   POST /plan              → backend/api/routes/terraform.py
#   GET  /plan-output       → backend/api/routes/terraform.py
#   POST /apply             → backend/api/routes/terraform.py
#   POST /upload            → backend/api/routes/files.py
#   POST /direct-push       → backend/api/routes/files.py
#   POST /logout            → backend/api/routes/files.py

from backend.api.app import app

__all__ = ["app"]
