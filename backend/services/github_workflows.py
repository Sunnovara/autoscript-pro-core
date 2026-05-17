from typing import Dict


def create_github_workflows(provider: str = "aws") -> Dict[str, str]:
    """Return a dict of GitHub Actions workflow YAML strings for the given cloud provider"""
    if provider == "azure":
        return {
            ".github/workflows/terraform-plan.yml": _azure_plan_workflow(),
            ".github/workflows/terraform-apply.yml": _azure_apply_workflow(),
            ".github/workflows/terraform-destroy.yml": _azure_destroy_workflow(),
        }
    return {
        ".github/workflows/terraform-plan.yml": _aws_plan_workflow(),
        ".github/workflows/terraform-apply.yml": _aws_apply_workflow(),
        ".github/workflows/terraform-destroy.yml": _aws_destroy_workflow(),
    }


# ---------------------------------------------------------------------------
# AWS workflows
# ---------------------------------------------------------------------------

def _aws_plan_workflow() -> str:
    return """name: Terraform Plan

on:
  workflow_dispatch:
  pull_request:
    branches: [ main ]

permissions:
  contents: write
  actions: read

jobs:
  terraform-plan:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Setup Terraform
      uses: hashicorp/setup-terraform@v3
      with:
        terraform_version: 1.5.0
        terraform_wrapper: false

    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ vars.AWS_REGION || 'us-east-1' }}

    - name: Cache Terraform providers
      uses: actions/cache@v4
      with:
        path: .terraform
        key: ${{ runner.os }}-terraform-${{ hashFiles('**/.terraform.lock.hcl') }}
        restore-keys: |
          ${{ runner.os }}-terraform-

    - name: Terraform Init
      run: terraform init

    - name: Terraform Plan
      run: |
        echo "::group::Terraform Plan Output"
        if terraform plan -no-color -out=tfplan | tee plan_output.txt; then
          echo "Plan completed successfully"
        else
          echo "Plan failed with exit code $?"
          echo "Plan failed - see output above" > plan_output.txt
          exit 1
        fi
        echo "::endgroup::"

    - name: Upload Plan Output
      uses: actions/upload-artifact@v4
      with:
        name: terraform-plan-output
        path: plan_output.txt
        retention-days: 30
      if: always()

    - name: Upload Plan File
      uses: actions/upload-artifact@v4
      with:
        name: terraform-plan-file
        path: tfplan
        retention-days: 30
      if: success()

    - name: Commit Terraform Configuration
      run: |
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"
        git remote set-url origin https://x-access-token:${{ secrets.GITHUB_TOKEN }}@github.com/${{ github.repository }}
        if [ -f ".terraform.lock.hcl" ]; then git add -f .terraform.lock.hcl; fi
        if [ -f "tfplan" ]; then git add -f tfplan; fi
        if ls terraform.tfstate* 1> /dev/null 2>&1; then git add -f terraform.tfstate*; fi
        if git diff --staged --quiet; then
          echo "No changes to commit"
        else
          git commit -m "Update Terraform configuration after plan [skip ci]"
          git push origin HEAD:${{ github.ref_name }}
        fi
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

    - name: Comment Plan Output (if PR)
      if: github.event_name == 'pull_request'
      uses: actions/github-script@v7
      with:
        script: |
          const fs = require('fs');
          const planOutput = fs.readFileSync('plan_output.txt', 'utf8');
          github.rest.issues.createComment({
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            body: `## Terraform Plan Output\n\`\`\`hcl\n${planOutput}\n\`\`\``
          });
"""


def _aws_apply_workflow() -> str:
    return """name: Terraform Apply

on:
  workflow_dispatch:

permissions:
  contents: write
  actions: read

jobs:
  terraform-apply:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Setup Terraform
      uses: hashicorp/setup-terraform@v3
      with:
        terraform_version: 1.5.0
        terraform_wrapper: false

    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ vars.AWS_REGION || 'us-east-1' }}

    - name: Cache Terraform providers
      uses: actions/cache@v4
      with:
        path: .terraform
        key: ${{ runner.os }}-terraform-${{ hashFiles('**/.terraform.lock.hcl') }}
        restore-keys: |
          ${{ runner.os }}-terraform-

    - name: Terraform Init
      run: terraform init

    - name: Download Plan File (if available)
      uses: actions/download-artifact@v4
      with:
        name: terraform-plan-file
        path: .
      continue-on-error: true

    - name: Terraform Apply
      run: |
        if [ -f "tfplan" ]; then
          terraform apply -auto-approve tfplan
        else
          terraform apply -auto-approve
        fi

    - name: Commit Terraform State After Apply
      run: |
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"
        git remote set-url origin https://x-access-token:${{ secrets.GITHUB_TOKEN }}@github.com/${{ github.repository }}
        if [ -f ".terraform.lock.hcl" ]; then git add -f .terraform.lock.hcl; fi
        if ls terraform.tfstate* 1> /dev/null 2>&1; then git add -f terraform.tfstate*; fi
        if [ -f "tfplan" ]; then git rm -f tfplan || true; fi
        if git diff --staged --quiet; then
          echo "No changes to commit"
        else
          git commit -m "Update Terraform state after apply [skip ci]"
          git push origin HEAD:${{ github.ref_name }}
        fi
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

    - name: Upload Apply Logs
      uses: actions/upload-artifact@v4
      with:
        name: terraform-apply-logs
        path: |
          terraform.tfstate
          .terraform.lock.hcl
        retention-days: 90
      if: always()
"""


def _aws_destroy_workflow() -> str:
    return """name: Terraform Destroy

on:
  workflow_dispatch:
    inputs:
      confirm_destroy:
        description: 'Type "DESTROY" to confirm resource destruction'
        required: true
        default: ''
      repository_name:
        description: 'Repository name for safety check'
        required: true
        default: ''

permissions:
  contents: write
  actions: read

jobs:
  terraform-destroy:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Setup Terraform
      uses: hashicorp/setup-terraform@v3
      with:
        terraform_version: 1.5.0

    - name: Safety Check - Confirm Destroy
      run: |
        if [ "${{ github.event.inputs.confirm_destroy }}" != "DESTROY" ]; then
          echo "ERROR: You must type 'DESTROY' to confirm resource destruction"
          exit 1
        fi
        echo "Destroy confirmation received"

    - name: Safety Check - Repository Name
      run: |
        EXPECTED_REPO="${{ github.repository }}"
        PROVIDED_REPO="${{ github.event.inputs.repository_name }}"
        if [ "$PROVIDED_REPO" != "$EXPECTED_REPO" ]; then
          echo "ERROR: Repository name mismatch. Expected: $EXPECTED_REPO, Got: $PROVIDED_REPO"
          exit 1
        fi
        echo "Repository name verified: $EXPECTED_REPO"

    - name: Safety Check - Verify State File Exists
      run: |
        if [ ! -f "terraform.tfstate" ]; then
          echo "ERROR: No terraform.tfstate file found — nothing to destroy"
          exit 1
        fi
        echo "State file found — proceeding with destroy"

    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ vars.AWS_REGION || 'us-east-1' }}

    - name: Cache Terraform providers
      uses: actions/cache@v4
      with:
        path: .terraform
        key: ${{ runner.os }}-terraform-${{ hashFiles('**/.terraform.lock.hcl') }}
        restore-keys: |
          ${{ runner.os }}-terraform-

    - name: Terraform Init
      run: terraform init

    - name: Terraform Destroy
      run: terraform destroy -auto-approve -no-color

    - name: Commit Updated State After Destroy
      run: |
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"
        git remote set-url origin https://x-access-token:${{ secrets.GITHUB_TOKEN }}@github.com/${{ github.repository }}
        if ls terraform.tfstate* 1> /dev/null 2>&1; then git add -f terraform.tfstate*; fi
        if [ -f ".terraform.lock.hcl" ]; then git add -f .terraform.lock.hcl; fi
        if git diff --staged --quiet; then
          echo "No changes to commit"
        else
          git commit -m "Update Terraform state after destroy [skip ci]"
          git push origin HEAD:${{ github.ref_name }}
        fi
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
"""


# ---------------------------------------------------------------------------
# Azure workflows
# ---------------------------------------------------------------------------

def _azure_plan_workflow() -> str:
    return """name: Terraform Plan (Azure)

on:
  workflow_dispatch:
  pull_request:
    branches: [ main ]

permissions:
  contents: write
  actions: read
  id-token: write

jobs:
  terraform-plan:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Setup Terraform
      uses: hashicorp/setup-terraform@v3
      with:
        terraform_version: 1.5.0
        terraform_wrapper: false

    - name: Configure Azure credentials
      uses: azure/login@v1
      with:
        creds: ${{ secrets.AZURE_CREDENTIALS }}

    - name: Set Terraform environment variables
      run: |
        echo "ARM_CLIENT_ID=${{ secrets.AZURE_CLIENT_ID }}" >> $GITHUB_ENV
        echo "ARM_CLIENT_SECRET=${{ secrets.AZURE_CLIENT_SECRET }}" >> $GITHUB_ENV
        echo "ARM_TENANT_ID=${{ secrets.AZURE_TENANT_ID }}" >> $GITHUB_ENV
        echo "ARM_SUBSCRIPTION_ID=${{ secrets.AZURE_SUBSCRIPTION_ID }}" >> $GITHUB_ENV

    - name: Terraform Init
      run: terraform init

    - name: Terraform Plan
      run: |
        terraform plan -no-color -out=tfplan | tee plan_output.txt || (echo "Plan failed" > plan_output.txt; exit 1)

    - name: Upload Plan Output
      uses: actions/upload-artifact@v4
      with:
        name: terraform-plan-output
        path: plan_output.txt
        retention-days: 30
      if: always()

    - name: Commit Terraform Configuration
      run: |
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"
        git remote set-url origin https://x-access-token:${{ secrets.GITHUB_TOKEN }}@github.com/${{ github.repository }}
        if [ -f ".terraform.lock.hcl" ]; then git add -f .terraform.lock.hcl; fi
        if git diff --staged --quiet; then echo "No changes"; else git commit -m "Update Terraform config after plan [skip ci]" && git push origin HEAD:${{ github.ref_name }}; fi
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
"""


def _azure_apply_workflow() -> str:
    return """name: Terraform Apply (Azure)

on:
  workflow_dispatch:

permissions:
  contents: write
  actions: read
  id-token: write

jobs:
  terraform-apply:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Setup Terraform
      uses: hashicorp/setup-terraform@v3
      with:
        terraform_version: 1.5.0
        terraform_wrapper: false

    - name: Configure Azure credentials
      uses: azure/login@v1
      with:
        creds: ${{ secrets.AZURE_CREDENTIALS }}

    - name: Set Terraform environment variables
      run: |
        echo "ARM_CLIENT_ID=${{ secrets.AZURE_CLIENT_ID }}" >> $GITHUB_ENV
        echo "ARM_CLIENT_SECRET=${{ secrets.AZURE_CLIENT_SECRET }}" >> $GITHUB_ENV
        echo "ARM_TENANT_ID=${{ secrets.AZURE_TENANT_ID }}" >> $GITHUB_ENV
        echo "ARM_SUBSCRIPTION_ID=${{ secrets.AZURE_SUBSCRIPTION_ID }}" >> $GITHUB_ENV

    - name: Terraform Init
      run: terraform init

    - name: Download Plan File (if available)
      uses: actions/download-artifact@v4
      with:
        name: terraform-plan-file
        path: .
      continue-on-error: true

    - name: Terraform Apply
      run: |
        if [ -f "tfplan" ]; then terraform apply -auto-approve tfplan; else terraform apply -auto-approve; fi

    - name: Commit Terraform State After Apply
      run: |
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"
        git remote set-url origin https://x-access-token:${{ secrets.GITHUB_TOKEN }}@github.com/${{ github.repository }}
        if ls terraform.tfstate* 1> /dev/null 2>&1; then git add -f terraform.tfstate*; fi
        if git diff --staged --quiet; then echo "No changes"; else git commit -m "Update state after apply [skip ci]" && git push origin HEAD:${{ github.ref_name }}; fi
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
"""


def _azure_destroy_workflow() -> str:
    return """name: Terraform Destroy (Azure)

on:
  workflow_dispatch:
    inputs:
      confirm_destroy:
        description: 'Type "DESTROY" to confirm'
        required: true
        default: ''
      repository_name:
        description: 'Repository name for safety check'
        required: true
        default: ''

permissions:
  contents: write
  actions: read
  id-token: write

jobs:
  terraform-destroy:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Safety Check - Confirm Destroy
      run: |
        if [ "${{ github.event.inputs.confirm_destroy }}" != "DESTROY" ]; then echo "Confirmation required"; exit 1; fi

    - name: Safety Check - Repository Name
      run: |
        if [ "${{ github.event.inputs.repository_name }}" != "${{ github.repository }}" ]; then echo "Repository mismatch"; exit 1; fi

    - name: Safety Check - State File Exists
      run: |
        if [ ! -f "terraform.tfstate" ]; then echo "No state file — nothing to destroy"; exit 1; fi

    - name: Configure Azure credentials
      uses: azure/login@v1
      with:
        creds: ${{ secrets.AZURE_CREDENTIALS }}

    - name: Set Terraform environment variables
      run: |
        echo "ARM_CLIENT_ID=${{ secrets.AZURE_CLIENT_ID }}" >> $GITHUB_ENV
        echo "ARM_CLIENT_SECRET=${{ secrets.AZURE_CLIENT_SECRET }}" >> $GITHUB_ENV
        echo "ARM_TENANT_ID=${{ secrets.AZURE_TENANT_ID }}" >> $GITHUB_ENV
        echo "ARM_SUBSCRIPTION_ID=${{ secrets.AZURE_SUBSCRIPTION_ID }}" >> $GITHUB_ENV

    - name: Terraform Init
      run: terraform init

    - name: Terraform Destroy
      run: terraform destroy -auto-approve -no-color

    - name: Commit Updated State
      run: |
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"
        git remote set-url origin https://x-access-token:${{ secrets.GITHUB_TOKEN }}@github.com/${{ github.repository }}
        if ls terraform.tfstate* 1> /dev/null 2>&1; then git add -f terraform.tfstate*; fi
        if git diff --staged --quiet; then echo "No changes"; else git commit -m "Update state after destroy [skip ci]" && git push origin HEAD:${{ github.ref_name }}; fi
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
"""
