# Testing Patterns

**Analysis Date:** 2026-01-21

## Test Framework

**Runner:**
- pytest (version 7.4.0+)
- Config: No `pytest.ini` or `pyproject.toml` at root; tests run with default pytest discovery

**Assertion Library:**
- Built-in pytest assertions: `assert`, `assert is True`, `assert any(...)`
- No explicit assertion library required

**Run Commands:**
```bash
pytest                                      # Run all tests
pytest -v                                   # Verbose output
pytest rulesevaluator/tests/                # Run specific tool tests
pytest -m integration                       # Run only integration tests (marked)
pytest --tb=short                          # Short traceback format
```

**Additional packages:**
- `pytest-asyncio>=0.21.0` - For async test support (available but not heavily used in observed tests)

## Test File Organization

**Location:**
- `tests/` directory at tool root: `rulesevaluator/tests/`, `graspevaluator/tests/`
- Tests co-located with source but in separate directory (not inline)
- Pattern: `tool/tests/` parallel to `tool/src/`

**Naming:**
- Test files: `test_*.py` or `*_test.py` (observed: `test_*.py`)
- Test classes: `Test[ComponentName]` (e.g., `TestRulesValidator`, `TestIntegrationWorkflow`)
- Test methods: `test_[scenario]` (e.g., `test_valid_rules_file`, `test_missing_prompts_node`)

**Structure:**
```
rulesevaluator/
├── src/
│   ├── rules_validator.py
│   ├── evaluator.py
│   └── ...
└── tests/
    ├── __init__.py
    ├── test_rules_validator.py
    ├── test_content_ingestion.py
    ├── test_integration.py
    └── test_rag_database.py
```

## Test Structure

**Suite Organization:**
```python
class TestRulesValidator:
    """Test cases for RulesValidator"""

    def setup_method(self):
        """Set up test fixtures"""
        self.validator = RulesValidator()

    def teardown_method(self):
        """Clean up after tests"""
        pass

    def test_valid_rules_file(self):
        """Test validation of a valid rules file"""
        # Arrange
        valid_rules = {...}

        # Act
        is_valid, data, errors = self.validator.validate_file(temp_path)

        # Assert
        assert is_valid is True
```

**Patterns:**
- `setup_method()` called before each test for per-test fixtures
- `teardown_method()` called after each test for cleanup
- Test method names describe the scenario being tested
- Docstrings explain what each test validates
- Arrange-Act-Assert (AAA) pattern typically followed

**Example from `test_rules_validator.py`:**
```python
def test_valid_rules_file(self):
    """Test validation of a valid rules file"""
    valid_rules = {
        "prompts": [
            {
                "prompt": "Test prompt",
                "rules": [
                    {
                        "ruletype": "critical",
                        "ruledescription": "Must do something"
                    }
                ]
            }
        ]
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(valid_rules, f)
        temp_path = f.name

    try:
        is_valid, data, errors = self.validator.validate_file(temp_path)
        assert is_valid is True
        assert len(errors) == 0
    finally:
        Path(temp_path).unlink()
```

## Mocking

**Framework:** No explicit mocking library (like `unittest.mock` or `pytest-mock`) observed in requirements

**Patterns:**
- Tests create actual objects rather than mocks
- Temporary files used for file-based tests: `tempfile.NamedTemporaryFile()`
- Temporary directories for integration tests: `tempfile.mkdtemp()` with cleanup
- Configuration objects passed directly rather than mocked

**What to Mock:**
- External API calls would be mocked (not observed in test files)
- File I/O typically uses tempfiles instead of mocking

**What NOT to Mock:**
- Core validation logic tested directly
- Configuration objects created fresh for each test
- Content processors tested with actual content transformations

## Fixtures and Factories

**Test Data:**
```python
def setup_method(self):
    """Set up test fixtures"""
    self.validator = RulesValidator()

    # Inline fixture for simple tests
    self.valid_rules = {
        "prompts": [
            {
                "prompt": "Test prompt",
                "rules": [
                    {
                        "ruletype": "critical",
                        "ruledescription": "Must do something"
                    }
                ]
            }
        ]
    }
```

**Location:**
- `setup_method()` for per-test setup in test classes
- Inline fixture data in test methods for simplicity
- Temporary directories created per-test using `tempfile.mkdtemp()`

**Example from `test_integration.py`:**
```python
def setup_method(self):
    """Set up test fixtures"""
    # Skip if required API keys not available
    if not os.getenv('OPENAI_API_KEY'):
        pytest.skip("OpenAI API key required for integration tests")

    # Create temporary directories
    self.temp_dir = Path(tempfile.mkdtemp())
    self.content_dir = self.temp_dir / "content"
    self.content_dir.mkdir()

    # Create test content
    (self.content_dir / "policy.txt").write_text("""
Our Return Policy
...
    """)

    # Create test configuration
    self.config_data = {...}
```

## Coverage

**Requirements:** Not enforced; no coverage configuration found

**View Coverage:**
```bash
pytest --cov=src/             # Generate coverage report
pytest --cov=src/ --cov-report=html  # HTML coverage report
```

Coverage tools available in test environments but not required by CI/CD.

## Test Types

**Unit Tests:**
- Scope: Individual functions and classes in isolation
- Location: `test_rules_validator.py`, `test_content_ingestion.py`
- Approach: Create objects, call methods, assert results
- Example: `TestRulesValidator.test_missing_prompts_node()` tests validation error handling

**Integration Tests:**
- Scope: Complete workflows combining multiple components
- Location: `test_integration.py` (marked with `@pytest.mark.integration`)
- Approach: Full pipeline setup with real config and content
- Example: `TestIntegrationWorkflow.test_complete_evaluation_workflow()` runs full Rules Evaluator pipeline
- Requirements: May require external API keys (tests skip if unavailable)

**E2E Tests:**
- Framework: Not observed in current test suite
- Could be added via shell scripts or additional test modules

## Common Patterns

**Async Testing:**
- `pytest-asyncio>=0.21.0` available in requirements
- Async patterns not observed in examined test files
- Usage: Would use `@pytest.mark.asyncio` decorator for async tests

**Error Testing:**
```python
def test_invalid_rule_type(self):
    """Test validation fails with invalid rule type"""
    invalid_rules = {
        "prompts": [
            {
                "prompt": "Test prompt",
                "rules": [
                    {
                        "ruletype": "invalid_type",  # Invalid type
                        "ruledescription": "Test rule"
                    }
                ]
            }
        ]
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(invalid_rules, f)
        temp_path = f.name

    try:
        is_valid, data, errors = self.validator.validate_file(temp_path)
        assert is_valid is False  # Should fail
        assert any("invalid ruletype" in e for e in errors)  # Should have specific error
    finally:
        Path(temp_path).unlink()
```

**File Testing:**
```python
def test_file_not_found(self):
    """Test validation fails when file doesn't exist"""
    is_valid, data, errors = self.validator.validate_file("nonexistent.json")
    assert is_valid is False
    assert any("Rules file not found" in e for e in errors)
```

**Tempfile Cleanup Pattern:**
```python
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    json.dump(test_data, f)
    temp_path = f.name

try:
    # Test code here
    result = validator.validate_file(temp_path)
    assert ...
finally:
    Path(temp_path).unlink()  # Explicit cleanup
```

## Test Quality Observations

**Strong Patterns:**
- Explicit setup/teardown with resource cleanup
- Clear test naming describes exact scenario
- Use of temporary files/directories for isolation
- Docstrings on all test methods
- Error message assertions use `any()` to find specific error text

**Coverage Gaps:**
- No observed tests for happy-path scenarios in some modules
- Integration tests require external API keys (may not run in CI)
- No explicit performance/load testing
- Mock-free approach means external API testing requires real credentials

---

*Testing analysis: 2026-01-21*
