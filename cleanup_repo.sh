#!/bin/bash
# Repository Cleanup Script
# Reorganizes files into a clean structure

set -e  # Exit on error

echo "=========================================="
echo "  REPOSITORY CLEANUP"
echo "=========================================="
echo ""

# Backup first
echo "Creating backup..."
git stash push -m "Pre-cleanup backup" || true

# Create new directory structure
echo "Creating directory structure..."
mkdir -p docs/{guides,deployment,development,api,archive}
mkdir -p tests/{unit,integration,verification,fixtures}
mkdir -p scripts/{deployment,verification,data}
mkdir -p data/{cache,learning,user}

# Move documentation files
echo "Moving documentation..."

# Guides
mv EXIT_STRATEGY_GUIDE.md docs/guides/ 2>/dev/null || true
mv EXIT_IMPLEMENTATION_STATUS.md docs/guides/ 2>/dev/null || true
mv WATCHLIST_QUICK_START.md docs/guides/ 2>/dev/null || true
mv WATCHLIST_SYSTEM.md docs/guides/ 2>/dev/null || true
mv LEARNING_QUICK_START.md docs/guides/ 2>/dev/null || true
mv TELEGRAM_SETUP_GUIDE.md docs/guides/ 2>/dev/null || true
mv XAI_X_INTELLIGENCE_QUICK_START.md docs/guides/ 2>/dev/null || true

# Deployment
mv DIGITALOCEAN_MIGRATION_GUIDE.md docs/deployment/ 2>/dev/null || true
mv RAILWAY_DEPLOYMENT_GUIDE.md docs/deployment/ 2>/dev/null || true
mv RESOURCE_OPTIMIZATION.md docs/deployment/ 2>/dev/null || true
mv DEPLOYMENT_STATUS.md docs/deployment/ 2>/dev/null || true

# Development
mv CLAUDE.md docs/development/ 2>/dev/null || true
mv IMPLEMENTATION_SUMMARY.md docs/development/ 2>/dev/null || true
mv IMPLEMENTATION_COMPLETE.md docs/development/ 2>/dev/null || true
mv COMPLETE_INTEGRATION_SUMMARY.md docs/development/ 2>/dev/null || true

# API/Dashboard
mv DASHBOARD_FORENSIC_REPORT.md docs/api/ 2>/dev/null || true
mv DASHBOARD_FIX_SUMMARY.md docs/api/ 2>/dev/null || true
mv DASHBOARD_INTEGRATION_STATUS.md docs/api/ 2>/dev/null || true
mv DASHBOARD_ENHANCEMENTS_PLAN.md docs/api/ 2>/dev/null || true
mv FORENSIC_SUMMARY.md docs/api/ 2>/dev/null || true
mv FORENSIC_ANALYSIS_REPORT.md docs/api/ 2>/dev/null || true

# Archive old docs
mv BUGS_FIXED_2026-01-29.md docs/archive/ 2>/dev/null || true
mv BEFORE_AFTER_COMPARISON.md docs/archive/ 2>/dev/null || true
mv PRICING_CORRECTION_SUMMARY.md docs/archive/ 2>/dev/null || true
mv FEATURES_2-9_IMPLEMENTATION_SUMMARY.md docs/archive/ 2>/dev/null || true
mv SELF_LEARNING_SYSTEM_COMPLETE.md docs/archive/ 2>/dev/null || true
mv WATCHLIST_IMPLEMENTATION_COMPLETE.md docs/archive/ 2>/dev/null || true
mv WATCHLIST_BRAIN_INTEGRATION.md docs/archive/ 2>/dev/null || true
mv EARNINGS_COMPONENT_38_COMPLETE.md docs/archive/ 2>/dev/null || true
mv EARNINGS_GUIDANCE_ANALYSIS.md docs/archive/ 2>/dev/null || true
mv COMPREHENSIVE_AGENTIC_BRAIN_SUMMARY.md docs/archive/ 2>/dev/null || true
mv EVOLUTIONARY_SYSTEM_IMPLEMENTATION.md docs/archive/ 2>/dev/null || true
mv INTEGRATION_PROGRESS_2026-01-29.md docs/archive/ 2>/dev/null || true
mv INTEGRATION_SESSION_2_COMPLETE.md docs/archive/ 2>/dev/null || true
mv XAI_IMPLEMENTATION_SUMMARY.md docs/archive/ 2>/dev/null || true
mv XAI_OPPORTUNITIES_SUMMARY.md docs/archive/ 2>/dev/null || true
mv XAI_X_INTELLIGENCE_IMPLEMENTATION.md docs/archive/ 2>/dev/null || true

# Move test files
echo "Moving test files..."

# Integration tests
mv test_learning_system.py tests/integration/ 2>/dev/null || true
mv test_watchlist.py tests/integration/ 2>/dev/null || true
mv test_earnings_learning_integration.py tests/integration/ 2>/dev/null || true
mv test_watchlist_learned_weights.py tests/integration/ 2>/dev/null || true
mv test_earnings_capabilities.py tests/integration/ 2>/dev/null || true
mv test_gov_contracts_integration.py tests/integration/ 2>/dev/null || true
mv test_patent_integration.py tests/integration/ 2>/dev/null || true
mv test_theme_discovery_integration.py tests/integration/ 2>/dev/null || true
mv test_xai_integration.py tests/integration/ 2>/dev/null || true
mv test_xai_x_intelligence.py tests/integration/ 2>/dev/null || true

# Unit tests
mv test_agentic_brain.py tests/unit/ 2>/dev/null || true
mv test_ai_enhancements.py tests/unit/ 2>/dev/null || true
mv test_comprehensive_agentic_brain.py tests/unit/ 2>/dev/null || true
mv test_evolutionary_agentic_brain.py tests/unit/ 2>/dev/null || true

# Verification scripts
mv verify_deployment.py scripts/verification/ 2>/dev/null || true
mv verify_dashboard_integration.py scripts/verification/ 2>/dev/null || true
mv verify_digitalocean.py scripts/verification/ 2>/dev/null || true
mv test_dashboard.sh scripts/verification/ 2>/dev/null || true

# Move other scripts
echo "Moving scripts..."
mv setup_telegram.py scripts/deployment/ 2>/dev/null || true
mv get_chat_id.py scripts/deployment/ 2>/dev/null || true

# Move data directories
echo "Moving data directories..."
mv cache_data data/cache_old 2>/dev/null || true
mv ai_data data/ 2>/dev/null || true
mv learning_data data/learning 2>/dev/null || true
mv ai_learning_data data/ai_learning 2>/dev/null || true
mv theme_data data/ 2>/dev/null || true
mv universe_data data/ 2>/dev/null || true
mv evolution_data data/ 2>/dev/null || true
mv parameter_data data/ 2>/dev/null || true
mv dashboard_data data/ 2>/dev/null || true

# Remove stub Python files at root
echo "Removing stub files..."
rm -f app.py async_scanner.py backtest.py backtester.py 2>/dev/null || true
rm -f bot_listener.py cache_manager.py charts.py config.py 2>/dev/null || true
rm -f dashboard.py deepseek_intelligence.py earnings.py 2>/dev/null || true
rm -f ecosystem_intelligence.py evolution_engine.py fact_checker.py 2>/dev/null || true
rm -f fast_stories.py market_health.py multi_timeframe.py 2>/dev/null || true
rm -f news_analyzer.py param_helper.py parameter_learning.py 2>/dev/null || true
rm -f relationship_graph.py scanner_automation.py screener.py 2>/dev/null || true
rm -f sector_rotation.py self_learning.py signal_ranker.py 2>/dev/null || true
rm -f storage.py story_alerts.py story_scorer.py story_scoring.py 2>/dev/null || true
rm -f tam_estimator.py theme_learner.py theme_registry.py 2>/dev/null || true
rm -f universe_manager.py ai_ecosystem_generator.py ai_learning.py 2>/dev/null || true
rm -f alt_sources.py 2>/dev/null || true

# Remove test result files
echo "Removing test results..."
rm -f ai_ab_test_results_*.json 2>/dev/null || true
rm -f ai_comparison_simulated.json 2>/dev/null || true
rm -f ai_stress_test_results.json 2>/dev/null || true

# Remove old scan CSVs
rm -f scan_*.csv 2>/dev/null || true

# Remove state files (will be regenerated)
rm -f scanner_state.json sector_state.json 2>/dev/null || true
rm -f weekly_stats.json cluster_history.json 2>/dev/null || true
rm -f telegram_offset.json learned_stories.json learned_themes.json 2>/dev/null || true
rm -f theme_history.json 2>/dev/null || true

# Update .gitignore
echo "Updating .gitignore..."
cat > .gitignore << 'GITIGNORE_EOF'
# Cache and temp data
data/cache/
data/cache_old/
data/learning/
data/user/
data/ai_data/
cache/
cache_data/

# Test results
*.json
!requirements.json
!package.json
!package-lock.json
!tsconfig.json

# Environment
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Logs
*.log
logs/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Temporary
tmp/
temp/
*.tmp
*.bak
*.swp

# Documentation builds
site/
docs/_build/

# Never ignore
!.gitignore
!.github/
!.do/

# Specific data dirs to keep structure
!data/.gitkeep
!data/cache/.gitkeep
!data/learning/.gitkeep
!data/user/.gitkeep
GITIGNORE_EOF

# Create .gitkeep files
touch data/.gitkeep
touch data/cache/.gitkeep
touch data/learning/.gitkeep
touch data/user/.gitkeep
touch tests/fixtures/.gitkeep

# Create index files for docs
echo "Creating README files..."

cat > docs/README.md << 'DOC_README_EOF'
# Documentation

## Guides
User-facing guides and tutorials:
- [Exit Strategy Guide](guides/EXIT_STRATEGY_GUIDE.md)
- [Watchlist Quick Start](guides/WATCHLIST_QUICK_START.md)
- [Learning System Guide](guides/LEARNING_QUICK_START.md)
- [Telegram Setup](guides/TELEGRAM_SETUP_GUIDE.md)

## Deployment
Deployment and infrastructure guides:
- [DigitalOcean Migration](deployment/DIGITALOCEAN_MIGRATION_GUIDE.md)
- [Railway Deployment](deployment/RAILWAY_DEPLOYMENT_GUIDE.md)
- [Resource Optimization](deployment/RESOURCE_OPTIMIZATION.md)

## API & Dashboard
API and dashboard documentation:
- [Dashboard Forensic Report](api/DASHBOARD_FORENSIC_REPORT.md)
- [API Integration Status](api/DASHBOARD_INTEGRATION_STATUS.md)

## Development
Development and implementation docs:
- [Implementation Summary](development/IMPLEMENTATION_SUMMARY.md)
- [Claude Guidelines](development/CLAUDE.md)

## Archive
Historical documentation and old implementation notes.
DOC_README_EOF

cat > tests/README.md << 'TEST_README_EOF'
# Tests

## Running Tests

```bash
# Run all tests
pytest

# Run specific test category
pytest tests/unit/
pytest tests/integration/

# Run with coverage
pytest --cov=src --cov-report=html
```

## Test Structure

- `unit/` - Unit tests for individual components
- `integration/` - Integration tests for system features
- `verification/` - Deployment and system verification scripts
- `fixtures/` - Test data and fixtures
TEST_README_EOF

cat > scripts/README.md << 'SCRIPT_README_EOF'
# Scripts

## Deployment
Scripts for deployment and setup:
- `deployment/setup_telegram.py` - Telegram bot setup wizard
- `deployment/get_chat_id.py` - Get Telegram chat ID

## Verification
Scripts for verifying deployment:
- `verification/verify_deployment.py` - Verify Railway/DigitalOcean
- `verification/verify_dashboard_integration.py` - Verify dashboard
- `verification/test_dashboard.sh` - Dashboard smoke tests

## Data
Data processing and migration scripts.
SCRIPT_README_EOF

echo ""
echo "=========================================="
echo "  CLEANUP COMPLETE"
echo "=========================================="
echo ""
echo "Summary:"
echo "  ✓ Moved documentation to docs/"
echo "  ✓ Moved tests to tests/"
echo "  ✓ Moved scripts to scripts/"
echo "  ✓ Moved data to data/"
echo "  ✓ Removed stub files"
echo "  ✓ Removed test results"
echo "  ✓ Updated .gitignore"
echo "  ✓ Created README files"
echo ""
echo "Next steps:"
echo "  1. Review changes: git status"
echo "  2. Test that main.py still works: python main.py --help"
echo "  3. Commit changes: git add -A && git commit -m 'Reorganize repository structure'"
echo "  4. Push to GitHub: git push origin main"
echo ""
