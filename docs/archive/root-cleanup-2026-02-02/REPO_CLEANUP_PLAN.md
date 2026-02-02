# Repository Cleanup Plan

## Current Issues

❌ **Root Directory Clutter:**
- 38 markdown documentation files
- 14 test files
- Stub Python files (symlinks to src/)
- Multiple JSON result files
- 16MB cache_data directory

❌ **Poor Organization:**
- Documentation scattered everywhere
- Tests not in dedicated directory
- Cache and temp data in repo
- Old test results committed

## Proposed Structure

```
stock_scanner_bot/
├── .github/              # GitHub workflows and configs
├── docs/                 # All documentation (organized)
│   ├── guides/          # User guides and tutorials
│   ├── api/             # API documentation
│   ├── deployment/      # Deployment guides
│   ├── development/     # Development docs
│   └── archive/         # Old/historical docs
├── src/                 # Source code (already clean!)
│   ├── api/
│   ├── core/
│   ├── intelligence/
│   ├── trading/
│   ├── learning/
│   └── ... (existing structure)
├── tests/               # All test files
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── scripts/             # Utility scripts
│   ├── deployment/
│   ├── data/
│   └── verification/
├── data/                # Persistent data (gitignored)
│   ├── cache/
│   ├── learning/
│   └── user/
├── .gitignore           # Improved ignore rules
├── README.md            # Main readme
├── requirements.txt
├── main.py
├── Procfile
└── runtime.txt
```

## Cleanup Actions

### 1. Move Documentation (38 files)
```bash
docs/
├── guides/
│   ├── EXIT_STRATEGY_GUIDE.md
│   ├── WATCHLIST_QUICK_START.md
│   ├── LEARNING_QUICK_START.md
│   └── TELEGRAM_SETUP_GUIDE.md
├── deployment/
│   ├── DIGITALOCEAN_MIGRATION_GUIDE.md
│   ├── RAILWAY_DEPLOYMENT_GUIDE.md
│   └── RESOURCE_OPTIMIZATION.md
├── development/
│   ├── CLAUDE.md
│   └── IMPLEMENTATION_SUMMARY.md
└── archive/
    ├── BUGS_FIXED_2026-01-29.md
    ├── AI_AB_TEST_*.md
    └── ... (old docs)
```

### 2. Move Tests (14 files)
```bash
tests/
├── integration/
│   ├── test_learning_system.py
│   ├── test_watchlist.py
│   └── test_earnings_learning_integration.py
├── unit/
│   ├── test_agentic_brain.py
│   └── test_ai_enhancements.py
└── verification/
    ├── verify_deployment.py
    ├── verify_dashboard_integration.py
    └── verify_digitalocean.py
```

### 3. Move Scripts
```bash
scripts/
├── deployment/
│   ├── setup_telegram.py
│   └── get_chat_id.py
├── verification/
│   └── test_dashboard.sh
└── data/
    └── (any data processing scripts)
```

### 4. Clean Up Root
- Remove stub Python files (they're in src/)
- Delete test result JSON files
- Move cache directories to data/
- Update .gitignore

### 5. Update .gitignore
```gitignore
# Cache and temp data
data/cache/
data/learning/
data/user/
cache_data/
ai_data/
learning_data/

# Test results
*.json
!requirements.json
!package.json

# Environment
.env
.env.local

# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/
```

## Benefits

✅ **Cleaner root** - Only essential files
✅ **Organized docs** - Easy to find information
✅ **Proper test structure** - Industry standard
✅ **Smaller repo** - Remove unnecessary files
✅ **Better git history** - No cache/temp data
✅ **Professional appearance** - Easier for collaborators
