# This file is a compatibility shim.
# All logic has been moved to backend/agent/ and backend/services/.
#
# backend/agent/core.py       — TerraformAIAgent class
# backend/agent/tools/        — individual tool factories
# backend/services/           — aws_docs, code_validator, file_builder,
#                               github_api, github_workflows, plan_parser

from backend.agent.core import TerraformAIAgent
from backend.agent import terraform_agent

__all__ = ["TerraformAIAgent", "terraform_agent"]
