# UI/UX Test Suite

Automated test suite for the Stock Scanner Dashboard UI/UX improvements.

## Test Files

- **test_ui_improvements.py** - Quick CSS verification (HTTP-based, no browser needed)
- **test_accessibility_full.py** - WCAG 2.1 AA compliance tests (requires Chrome)
- **test_uiux_full.py** - Visual polish and interaction tests (requires Chrome)
- **check_console.js** - Browser console error checker (Puppeteer/Node.js)
- **run_all_tests.sh** - Master test runner

## Requirements

### Python Tests
```bash
pip install requests selenium
```

### Node.js Tests
```bash
npm install puppeteer
```

## Running Tests

### Quick CSS Test (No Browser Required)
```bash
python3 test_ui_improvements.py
```

### Full Test Suite
```bash
./run_all_tests.sh
```

### Individual Tests
```bash
# Accessibility tests
python3 test_accessibility_full.py

# UI/UX tests
python3 test_uiux_full.py

# Console error check
node check_console.js
```

## Test Coverage

- **12 CSS Improvement Tests** - Verify all CSS changes deployed
- **12 Accessibility Tests** - WCAG 2.1 AA compliance
- **16 UI/UX Tests** - Visual polish, responsiveness, interactions
- **Console Error Check** - Real browser console analysis

## Expected Results

All tests should pass when:
- Dashboard is deployed
- Backend API is healthy
- All UI/UX improvements are live

## CI/CD Integration

You can add these tests to your deployment pipeline:

```yaml
# Example GitHub Actions
- name: Run UI/UX Tests
  run: |
    cd tests/ui-ux
    python3 test_ui_improvements.py
```
