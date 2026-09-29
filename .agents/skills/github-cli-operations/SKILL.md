---
name: github-cli-operations
description: 'Expert in using GitHub CLI (`gh`) for repository management, secrets, workflows, PRs, and GitHub automation.'
---

# GitHub CLI Operations Skill

**Expert in using the GitHub CLI (`gh`) command-line tool to manage repositories, secrets, workflows, pull requests, and perform automated GitHub operations.**

## Core Capabilities

- Authenticate with GitHub using `gh auth`
- Manage repository secrets (view, create, delete)
- Monitor and manage GitHub Actions workflows
- View pipeline/workflow run statuses
- Manage pull requests and issues
- Create and manage releases
- Clone and configure repositories
- Execute GitHub API calls from command line

## Installation & Authentication

### Install GitHub CLI

```bash
# Windows (via winget)
winget install GitHub.cli

# macOS (via Homebrew)
brew install gh

# Ubuntu/Debian
sudo apt-get install gh

# Verify installation
gh --version
```

### Authenticate with GitHub

```bash
gh auth login
```

Follow the interactive prompts:
- Select **GitHub.com** as host
- Choose **HTTPS** for git protocol
- Select **Login with a web browser**
- Authorize the GitHub CLI app

**Verify authentication:**

```bash
gh auth status
```

### Using Personal Access Token (Alternative)

For automation or CI/CD:

```bash
# Set via environment variable
$env:GH_TOKEN = "your-personal-access-token"

# Or authenticate with token
echo "your-token" | gh auth login --with-token
```

## Repository Secrets Management

### View All Secrets

List all secrets in the current repository:

```bash
gh secret list
```

or with formatting:

```bash
gh secret list --json name,updatedAt -q '.[] | [.name, .updatedAt] | @csv'
```

### View Individual Secret (Name Only)

```bash
# Only shows the secret name and last update, not the value
gh secret list -L 10
```

### Create/Update a Secret

```bash
# Create a new secret
gh secret set SECRET_NAME --body "secret-value"

# Or from a file
gh secret set SECRET_NAME < secret-file.txt

# Or from stdin with pipe
echo "my-secret-value" | gh secret set MY_SECRET
```

### Delete a Secret

```bash
gh secret delete SECRET_NAME
```

Confirm when prompted.

### View Secrets for Different Environments

For environment-specific secrets:

```bash
# List secrets in production environment
gh secret list --env production

# Set secret in specific environment
gh secret set MY_SECRET --env production --body "value"

# Delete secret from environment
gh secret delete MY_SECRET --env production
```

## GitHub Actions Workflows

### View Workflow Status

List all workflows:

```bash
gh workflow list
```

View specific workflow runs:

```bash
gh run list --workflow=main.yml
```

### View Run Details

```bash
# List recent runs
gh run list -L 10

# View specific run status
gh run view <run-id>

# View logs for a run
gh run view <run-id> --log
```

### Trigger Workflow Manually

```bash
gh workflow run workflow-name.yml
```

### Cancel a Running Workflow

```bash
gh run cancel <run-id>
```

### Rerun a Failed Workflow

```bash
gh run rerun <run-id>
```

### Watch Workflow Execution (Real-Time)

```bash
gh run watch <run-id>
```

## Pull Requests

### Create a Pull Request

```bash
gh pr create --title "PR Title" --body "PR description"
```

With options:

```bash
gh pr create \
  --title "Fix: Update README" \
  --body "This PR updates the documentation" \
  --base main \
  --head feature/my-feature
```

### List Pull Requests

```bash
# List open PRs
gh pr list

# List PRs with specific state
gh pr list --state merged -L 5

# List PRs assigned to you
gh pr list --assignee "@me"
```

### View PR Details

```bash
gh pr view <pr-number>
```

### Check PR Status

```bash
gh pr status
```

### Review a PR

```bash
# Request changes
gh pr review <pr-number> --request-changes -b "Review comments"

# Approve PR
gh pr review <pr-number> --approve

# Comment on PR
gh pr comment <pr-number> -b "This looks great!"
```

### Merge a PR

```bash
# Merge with default strategy
gh pr merge <pr-number>

# Squash merge
gh pr merge <pr-number> --squash

# Rebase and merge
gh pr merge <pr-number> --rebase
```

## Issues

### Create an Issue

```bash
gh issue create --title "Issue Title" --body "Description"
```

### List Issues

```bash
# Open issues
gh issue list

# Closed issues
gh issue list --state closed

# Issues assigned to you
gh issue list --assignee "@me"
```

### View Issue Details

```bash
gh issue view <issue-number>
```

### Close an Issue

```bash
gh issue close <issue-number>
```

### Reopen an Issue

```bash
gh issue reopen <issue-number>
```

### Comment on Issue

```bash
gh issue comment <issue-number> -b "Your comment here"
```

## Releases

### Create a Release

```bash
gh release create v1.0.0 --title "Release v1.0.0" --notes "Release notes here"
```

With asset upload:

```bash
gh release create v1.0.0 ./build/app.zip -t "v1.0.0" -n "First release"
```

### List Releases

```bash
gh release list
```

### View Release Details

```bash
gh release view v1.0.0
```

### Delete a Release

```bash
gh release delete v1.0.0
```

## Repository Information

### Get Repository Details

```bash
# Current repository
gh repo view

# Specific repository
gh repo view owner/repo-name

# View in JSON format
gh repo view --json name,description,owner,isPrivate
```

### Clone a Repository

```bash
gh repo clone owner/repo-name
```

### Create a Repository

```bash
gh repo create my-repo --public
```

with description:

```bash
gh repo create my-repo --public --description "My project" --source=.
```

### Archive a Repository

```bash
gh repo archive owner/repo-name
```

## Advanced: Using GitHub API

### Run Raw API Calls

```bash
# GET request
gh api repos/Wish-Hunter/wish-hunter

# Get specific fields
gh api repos/Wish-Hunter/wish-hunter -q '.name, .description'

# POST request
gh api -X POST repos/Wish-Hunter/wish-hunter/issues -f title="New issue" -f body="Issue body"

# List with pagination
gh api repos/Wish-Hunter/wish-hunter/actions/runs -L 30
```

### Query Repository Workflows

```bash
gh api repos/Wish-Hunter/wish-hunter/actions/workflows
```

## Scripting Examples

### Bulk Update Secrets

```powershell
#!/usr/bin/env pwsh

$secrets = @{
    'DB_HOST' = 'localhost'
    'DB_USER' = 'admin'
    'DB_PASS' = 'password'
}

foreach ($key in $secrets.Keys) {
    gh secret set $key --body $secrets[$key]
    Write-Host "Secret '$key' updated"
}
```

### Monitor Workflow and Report Status

```bash
#!/bin/bash

WORKFLOW="main.yml"
STATUS_FILE="workflow_status.txt"

while true; do
    STATUS=$(gh run list --workflow=$WORKFLOW -L 1 --json conclusion -q '.[0].conclusion')
    
    echo "$(date): Workflow status: $STATUS" >> $STATUS_FILE
    
    if [ "$STATUS" = "failure" ]; then
        echo "Workflow failed! Getting logs..."
        RUN_ID=$(gh run list --workflow=$WORKFLOW -L 1 --json databaseId -q '.[0].databaseId')
        gh run view $RUN_ID --log
        break
    fi
    
    sleep 30
done
```

### Extract PR Information

```bash
#!/bin/bash

# Get all open PRs with author, title, and state
gh pr list --json author,title,state -q '.[] | [.author.login, .title, .state] | @csv'
```

### List All Repository Secrets for Governance

```bash
#!/bin/bash

echo "Repository Secrets:"
echo "=================="

gh secret list --json name,updatedAt -q '.[] | "\(.name) - Updated: \(.updatedAt)"'
```

## Common Workflows

### Complete PR Review and Merge Workflow

```bash
#!/bin/bash

PR_NUMBER=$1

# View PR details
gh pr view $PR_NUMBER

# Check PR status
gh pr status

# Review and approve
gh pr review $PR_NUMBER --approve

# Merge PR
gh pr merge $PR_NUMBER --squash
```

### Sync Secrets Across Environments

```bash
#!/bin/bash

SECRET_NAME="API_KEY"
SOURCE_ENV="development"
TARGET_ENV="staging"

# Get secret from source
VALUE=$(gh secret list --env $SOURCE_ENV --json updatedAt -q '.[] | select(.name=="'$SECRET_NAME'") | .updatedAt')

# Set in target environment
gh secret set $SECRET_NAME --env $TARGET_ENV --body "$VALUE"
```

## Troubleshooting

### Authentication Issues

```bash
# Check authentication status
gh auth status

# Re-authenticate
gh auth logout
gh auth login

# Set token manually
$env:GH_TOKEN = "your-token"
gh auth status
```

### Command Not Found

Verify installation:

```bash
which gh  # macOS/Linux
Get-Command gh  # PowerShell
```

Update GitHub CLI:

```bash
gh version
# Then update via your package manager (winget, brew, apt, etc.)
```

### API Rate Limits

Check rate limits:

```bash
gh api rate_limit
```

### Workflow Not Triggering

Verify workflow file exists and is accessible:

```bash
gh api repos/Wish-Hunter/wish-hunter/actions/workflows
```

## Tips & Best Practices

- **Store token securely** — Use environment variables or OS credential storage, never hardcode
- **Use aliases** — Create PowerShell functions for frequently-used commands
- **Leverage JSON output** — Use `-q` flag with JQ for complex queries
- **Automate secret rotation** — Script secret updates for scheduled rotation
- **Monitor workflows** — Use `gh run watch` to track CI/CD progress
- **Limit token scope** — Create tokens with minimal required permissions
- **Document workflows** — Add comments to complex gh scripts

## PowerShell Aliases

Add to your PowerShell profile:

```powershell
function gh-secrets-list { gh secret list }
function gh-status { gh run list -L 5 -q '.[] | "\(.name): \(.conclusion)"' }
function gh-open-pr { gh pr create --web }
function gh-check-workflow { gh run list --workflow=$args[0] -L 5 }
```
