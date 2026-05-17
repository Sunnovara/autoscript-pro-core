# AutoScript-Pro — Terraform AI Agent

AutoScript-Pro is a **production-grade AI-powered Terraform automation agent** that generates, modifies, and deploys AWS infrastructure using **natural language**, **GitHub**, and **CI/CD workflows**.

It is a **true AI agent** (not a script or template generator) built around **Model Context Protocol (MCP) tools** and an **agent-based reasoning loop**.

---

## 🤖 What This Is

AutoScript-Pro is an autonomous infrastructure agent that:

- Uses **ChatGPT (OpenAI API)** for reasoning and decision-making
- Employs **MCP (Model Context Protocol) tools** for structured, safe actions
- Uses the **LangChain agent framework** for tool selection and orchestration
- Provides a **web-based chat UI (React + Flask)**
- Interacts directly with **GitHub** and **Terraform workflows**
- Generates **production-ready Terraform code** using **official AWS provider documentation only**

This is **not** a stateless chatbot — the agent maintains context, files, and execution state across interactions.

---

## 🧠 High-Level Architecture

```
User (Web UI)
   ↓
React Frontend (web-ui)
   ↓
Flask Backend (ai_agent_app.py)
   ↓
Terraform AI Agent (terraform_ai_agent.py)
   ↓
MCP Tools
   ├── Terraform Code Generation
   ├── Code Modification
   ├── GitHub Push
   ├── Terraform Plan / Apply
   └── Plan Output Extraction
   ↓
GitHub + GitHub Actions + AWS
```

---

## 📂 Project Structure

```
AutoScript-Pro/
├── terraform_ai_agent.py      # Core AI agent + MCP tools
├── ai_agent_app.py            # Flask backend + API routes
├── run_ai_agent.py            # Application entry point
├── requirements.txt           # Python dependencies
├── .env.template              # Environment variables template
├── web-ui/                    # React frontend
│   ├── src/
│   ├── index.html
│   ├── package.json
│   └── dist/                  # Production build output
├── README.md                  # This file
└── README_original.md         # Original reference (unchanged)
```

---

## 🚀 Quick Start

### 1️⃣ Install Backend Dependencies
```bash
pip install -r requirements.txt
```

### 2️⃣ Install & Build Frontend
```bash
cd web-ui
npm install
npm run build
```

### 3️⃣ Configure Environment Variables
```bash
cp .env.template .env
```

Edit `.env`:

```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4.1
SECRET_KEY=your-secret-key
```

> Azure OpenAI is **not used** in this project.

---

### 4️⃣ Start the Application
```bash
python run_ai_agent.py
```

Open in browser:
```
http://localhost:5001
```

---

## 💬 How to Use

Interact with the agent using natural language via the web UI.

### Example Prompts
- `Generate Terraform code for an S3 bucket in us-east-1`
- `Modify the code to add encryption and versioning`
- `Push this to GitHub https://github.com/you/repo | ghp_xxx`
- `Run terraform plan and show me the output`
- `Apply the infrastructure`

---

## 🧩 Agent Capabilities

The agent can intelligently:

- Generate Terraform code using **official AWS provider documentation**
- Modify existing Terraform code safely
- Push generated code to a **user-specified GitHub repository**
- Trigger Terraform **plan** and **apply** via GitHub Actions
- Retrieve and display Terraform plan output
- Maintain state across interactions
- Handle errors and guide the user

---

## 🔧 MCP Tools

AutoScript-Pro includes the following MCP tools:

1. **`generate_terraform_code`**  
   Generates Terraform files from natural language descriptions.

2. **`modify_terraform_code`**  
   Modifies previously generated or uploaded Terraform code.

3. **`push_to_github`**  
   Pushes Terraform code and workflows to a GitHub repository.

4. **`trigger_terraform_plan`**  
   Triggers Terraform plan via GitHub Actions.

5. **`get_terraform_plan_output`**  
   Retrieves plan output from GitHub Actions logs.

6. **`trigger_terraform_apply`**  
   Applies infrastructure using Terraform.

---

## 🔐 GitHub Push Safety Model

AutoScript-Pro **never pushes code automatically or silently**.

A GitHub push happens **only when the user explicitly provides**:
1. A **GitHub repository URL**
2. A **GitHub Personal Access Token (PAT)**

Example:
```
https://github.com/username/repo | ghp_xxxxxxxxx
```

### Safety Guarantees
- Tokens are **never stored**
- No push occurs without explicit user intent
- Uses GitHub REST API (no local git, no shell access)
- Works with public and private repositories

---

## 📦 Generated Artifacts

### Terraform Files
- `main.tf`
- `variables.tf`
- `outputs.tf`
- `provider.tf`

### GitHub Workflows
- `.github/workflows/terraform-plan.yml`
- `.github/workflows/terraform-apply.yml`

---

## 📚 Official AWS Provider Documentation Only

The agent uses **exclusively** the official Terraform AWS Provider documentation:

https://registry.terraform.io/providers/hashicorp/aws/latest/docs

- No third-party examples
- No outdated syntax
- Uses AWS provider `~> 5.x`
- Production-ready code

---

## 🔑 Requirements

### GitHub
- Personal Access Token with:
  - `repo`
  - `workflow`

### AWS (via GitHub Secrets)
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

---

## 🔒 Security Notes

- Never commit `.env`
- Use GitHub secrets for credentials
- Review generated code before apply
- Monitor AWS costs

---

## 🛠 Troubleshooting

### OpenAI 429 / Quota Errors
- Backend is running correctly
- Add billing to OpenAI to enable responses

### GitHub Push Fails
- Check token permissions
- Verify repository URL
- Ensure repo exists

### Terraform Workflow Fails
- Check GitHub Actions logs
- Verify AWS credentials
- Confirm region and provider settings

---

## 📌 Summary

AutoScript-Pro is a **real autonomous infrastructure agent**, not a demo or wrapper.

With OpenAI API access enabled, **all capabilities work end-to-end without code changes**.