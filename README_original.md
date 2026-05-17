# Terraform MCP AI Agent

A proper AI agent using Model Context Protocol (MCP) tools for generating, deploying, and managing AWS infrastructure with Terraform.

## 🤖 What This Is

This is a **true AI agent** (not a simple script) that:
- Uses **MCP (Model Context Protocol)** tools for structured interactions
- Employs **LangChain agent framework** for intelligent decision making
- Provides **natural conversation interface** for Terraform operations
- Makes **intelligent tool selections** based on user requests
- Uses **official AWS provider documentation** for accurate code generation

## 🗂️ Files Structure

```
terraform-ai-agent/
├── terraform_ai_agent.py     # Core AI agent with LangChain tools
├── ai_agent_app.py           # Flask web interface for the agent
├── templates/
│   └── index.html            # Chat-based web UI
├── requirements.txt          # Agent dependencies
├── run_ai_agent.py          # Startup script
├── .env.template            # Environment template
└── README.md                # This file
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.template .env
# Edit .env with your Azure OpenAI credentials
```

### 3. Start the Agent
```bash
python run_ai_agent.py
```

### 4. Open Browser
Navigate to: http://localhost:

## 💬 How to Use

### Chat Interface
Simply chat with the agent naturally:

**Examples:**
- "Create an S3 bucket with versioning in us-east-1"
- "Modify the code to add encryption"
- "Push this to my GitHub repository"
- "Run terraform plan and show me the output"
- "Deploy the infrastructure"

### Agent Capabilities
The agent can intelligently:
- Generate Terraform code using official AWS documentation
- Modify existing code based on your requests
- Push code and workflows to GitHub
- Trigger and monitor Terraform plan/apply
- Extract and display plan outputs in the UI
- Handle errors and provide guidance

## 🔧 MCP Tools

The agent includes these MCP tools:

1. **`generate_terraform_code`** - Creates Terraform code from descriptions
2. **`modify_terraform_code`** - Modifies existing code
3. **`push_to_github`** - Pushes code and workflows to GitHub
4. **`trigger_terraform_plan`** - Runs Terraform plan workflow
5. **`get_terraform_plan_output`** - Retrieves plan output for UI display
6. **`trigger_terraform_apply`** - Deploys infrastructure

## 📋 Requirements

### Environment Variables (.env file)
```
AZURE_OPENAI_KEY=your_azure_openai_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
SECRET_KEY=your-secret-key-here
```

### GitHub Setup
- Personal Access Token with `repo` and `workflow` permissions
- Repository secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

## 🏛️ Official AWS Provider Documentation ONLY

This agent uses **EXCLUSIVELY** the official Terraform AWS Provider documentation from:
https://registry.terraform.io/providers/hashicorp/aws/latest/docs

### 🎯 Pure Official Sources:
- ✅ **Real-time Documentation**: Fetches live documentation from Terraform Registry
- ✅ **Official Examples**: Uses only examples from official provider documentation
- ✅ **Latest Features**: Always uses the most current AWS provider (~> 5.0)
- ✅ **Accurate Syntax**: Uses exact resource syntax from official docs
- ✅ **Best Practices**: Follows HashiCorp's recommended patterns
- ✅ **Production Ready**: Generates deployable, enterprise-grade code
- ✅ **No Unofficial Sources**: Does not use any third-party or custom examples

### Supported Resources:
- **S3 Buckets** with versioning and encryption
- **EC2 Instances** with security groups and user data
- **VPC Networks** with subnets and routing
- **RDS Databases** with security and backup configuration
- **And many more** based on official documentation

## Generated Files

The agent creates these files in your repository:

### Terraform Files
- `main.tf` - Main infrastructure configuration
- `variables.tf` - Variable definitions
- `outputs.tf` - Output definitions
- `provider.tf` - Provider configuration

### GitHub Workflows
- `.github/workflows/terraform-plan.yml` - Plan workflow
- `.github/workflows/terraform-apply.yml` - Apply workflow

## Security Notes

- Never commit your `.env` file to version control
- Use GitHub secrets for AWS credentials
- Review generated code before deployment
- Monitor AWS costs and resources

## Troubleshooting

### Common Issues

1. **Environment variables not set**
   - Check your `.env` file
   - Ensure all required variables are present

2. **GitHub push fails**
   - Verify your GitHub token has correct permissions
   - Check repository URL format
   - Ensure repository exists

3. **Workflow fails**
   - Check GitHub repository secrets
   - Verify AWS credentials are valid
   - Review workflow logs in GitHub Actions

## File Structure

```
terraform-agent/
├── terraform_agent.py      # Core agent logic
├── app.py                  # Flask web application
├── run.py                  # Startup script
├── requirements_new.txt    # Python dependencies
├── .env.template          # Environment template
├── templates/
│   └── index.html         # Web interface
└── README.md              # This file
```

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review GitHub workflow logs
3. Check AWS CloudTrail for deployment issues
