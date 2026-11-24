# GitHub Repository Setup Guide

This guide walks you through creating a GitHub repository and pushing the Agri Supply Chain Blockchain MVP project.

---

## Prerequisites

- [ ] GitHub account (create at https://github.com if needed)
- [ ] Git installed locally (https://git-scm.com/)
- [ ] GitHub CLI (optional but recommended): `winget install GitHub.cli` or `brew install gh`

---

## Step 1: Initialize Local Git Repository

```bash
# Navigate to project root
cd C:\VP\MajorProjectDemo\agri-blockchain-mvp

# Initialize git repository
git init

# Verify initialization
git status
```

---

## Step 2: Create .gitignore

Create a `.gitignore` file to exclude sensitive and generated files:

```bash
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
ENV/
env/
.pytest_cache/
.coverage
htmlcov/
.tox/
.mypy_cache/
*.egg-info/
dist/
build/

# Database
*.db
*.sqlite
*.sqlite3

# Environment
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Blockchain/Foundry
out/
cache/
broadcast/
anvil/deployment.json

# Logs
*.log
logs/

# Temporary files
*.tmp
*.temp
.tmp/
.temp/

# Test outputs
test-results/
coverage/
EOF
```

---

## Step 3: Create Initial Commit

```bash
# Add all files
git add .

# Check what will be committed
git status

# Create initial commit
git commit -m "feat: Initial commit - Phase 1 Foundation & Database

- Smart contract (DataAnchor.sol) for minimal hash anchoring
- SQLite database with 7 tables (farms, crops, events, anomalies, reviews, anchors)
- FastAPI backend with 6 route modules
- IsolationForest anomaly detection with 7 features
- SARIMA time-series integration
- Merkle tree batch anchoring service
- Admin UI (dashboard, review queue, traceability)
- Sample data generator for demo scenario
- Comprehensive test suite
- Full documentation"

# Verify commit
git log --oneline -1
```

---

## Step 4: Create GitHub Repository

### Option A: Using GitHub CLI (Recommended)

```bash
# Login to GitHub CLI (if not already)
gh auth login

# Create repository and push
gh repo create agri-blockchain-mvp \
  --public \
  --description "Database-first agricultural supply chain MVP with AI anomaly detection and blockchain anchoring" \
  --source=. \
  --remote=origin \
  --push
```

### Option B: Using GitHub Web Interface

1. Go to https://github.com/new
2. Repository name: `agri-blockchain-mvp`
3. Description: `Database-first agricultural supply chain MVP with AI anomaly detection and blockchain anchoring`
4. Set to **Public** (or Private if preferred)
5. **DO NOT** initialize with README, .gitignore, or license (we already have them)
6. Click "Create repository"

Then push from local:

```bash
# Add remote origin (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/agri-blockchain-mvp.git

# Push to GitHub
git branch -M main
git push -u origin main
```

---

## Step 5: Verify Repository

```bash
# Check remote
git remote -v

# Check branches
git branch -a

# View on GitHub (opens browser)
gh repo view --web
```

---

## Step 6: Set Up Branch Protection (Optional but Recommended)

### Using GitHub CLI:

```bash
# Enable branch protection on main
gh api repos/YOUR_USERNAME/agri-blockchain-mvp/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":[]}' \
  --field enforce_admins=false \
  --field required_pull_request_reviews='{"required_approving_review_count":1}' \
  --field restrictions='{}'
```

### Using Web Interface:
1. Go to Settings → Branches
2. Click "Add rule" for `main`
3. Enable:
   - Require pull request reviews before merging
   - Require status checks to pass before merging
   - Require branches to be up to date before merging

---

## Step 7: Configure Repository Settings

### Add Topics (for discoverability)

```bash
gh repo edit agri-blockchain-mvp \
  --add-topic "blockchain" \
  --add-topic "supply-chain" \
  --add-topic "anomaly-detection" \
  --add-topic "fastapi" \
  --add-topic "sqlite" \
  --add-topic "solidity" \
  --add-topic "foundry" \
  --add-topic "machine-learning" \
  --add-topic "agriculture" \
  --add-topic "mvp"
```

### Enable Features

```bash
# Enable Issues
gh repo edit agri-blockchain-mvp --enable-issues

# Enable Discussions
gh repo edit agri-blockchain-mvp --enable-discussions

# Enable Wiki
gh repo edit agri-blockchain-mvp --enable-wiki
```

---

## Step 8: Create Release (Optional)

```bash
# Create first release tag
git tag -a v0.1.0 -m "Phase 1: Foundation & Database Complete"
git push origin v0.1.0

# Create GitHub release
gh release create v0.1.0 \
  --title "v0.1.0 - Phase 1 Foundation & Database" \
  --notes "Initial release with complete Phase 1 implementation:
- Smart contract for hash anchoring
- SQLite database with 7 tables
- FastAPI backend with 6 route modules
- IsolationForest anomaly detection
- Admin review UI
- Merkle tree batch anchoring
- Sample data generator"
```

---

## Step 9: Set Up GitHub Actions (CI/CD)

Create a basic CI workflow:

```bash
mkdir -p .github/workflows

cat > .github/workflows/ci.yml << 'EOF'
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run linting
      run: |
        pip install ruff
        ruff check backend/
    
    - name: Run tests
      run: |
        python -m pytest tests/ -v
    
    - name: Test database init
      run: |
        python scripts/init_db.py
EOF
```

Commit and push the workflow:

```bash
git add .github/workflows/ci.yml
git commit -m "ci: Add GitHub Actions workflow for testing"
git push
```

---

## Step 10: Add Collaborators (If Team Project)

```bash
# Add collaborator with write access
gh api repos/YOUR_USERNAME/agri-blockchain-mvp/collaborators/COLLABORATOR_USERNAME \
  --method PUT \
  --field permission=write
```

---

## Common Commands Reference

| Task | Command |
|------|---------|
| Check status | `git status` |
| View changes | `git diff` |
| Stage changes | `git add .` |
| Commit | `git commit -m "message"` |
| Push | `git push` |
| Pull | `git pull` |
| Create branch | `git checkout -b feature-name` |
| Switch branch | `git checkout main` |
| Merge branch | `git merge feature-name` |
| View history | `git log --oneline -10` |
| View remote | `git remote -v` |

---

## Troubleshooting

### "Repository not found" error
```bash
# Check remote URL
git remote -v

# Fix if needed
git remote set-url origin https://github.com/YOUR_USERNAME/agri-blockchain-mvp.git
```

### Authentication failed
```bash
# Use GitHub CLI for auth
gh auth login

# Or use personal access token
git remote set-url origin https://TOKEN@github.com/YOUR_USERNAME/agri-blockchain-mvp.git
```

### Large file rejected
```bash
# Remove from history if accidentally committed
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch PATH_TO_LARGE_FILE" \
  --prune-empty --tag-name-filter cat -- --all
```

---

## Next Steps After GitHub Setup

1. ✅ Repository created and code pushed
2. 🔄 Set up GitHub Actions CI (Step 9)
3. 🔄 Configure branch protection (Step 6)
4. 🔄 Add project board for task tracking
5. 🔄 Create issue templates for bugs/features
6. 🔄 Set up dependabot for dependency updates
7. 🔄 Document contribution guidelines (CONTRIBUTING.md)

---

## Security Notes

- **Never commit** `.env` files with real secrets
- **Never commit** private keys or deployment artifacts
- **Review** `.gitignore` covers all sensitive files
- **Use** GitHub Secrets for CI/CD credentials
- **Rotate** any accidentally exposed keys immediately

---

*Last Updated: 2026-11-24*