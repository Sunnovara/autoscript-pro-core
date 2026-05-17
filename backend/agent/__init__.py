from backend.agent.core import TerraformAIAgent

# Global singleton — imported by Flask routes
terraform_agent = TerraformAIAgent()
