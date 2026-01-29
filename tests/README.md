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
