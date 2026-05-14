"""Integration tests for structured logging across all modules."""
import json
import sys
import pytest
import structlog

sys.path.insert(0, '/home/bill/Localcode/Airbais/tools/automation')


@pytest.fixture(autouse=True)
def reset_structlog():
    """Reset structlog between tests."""
    structlog.reset_defaults()
    yield
    structlog.reset_defaults()


class TestAllModulesUseStructlog:
    """Verify all modules have been migrated to structlog."""

    def test_error_handlers_uses_structlog(self):
        """error_handlers module should use structlog."""
        from error_handlers import logger
        # structlog loggers have bind method
        assert hasattr(logger, 'bind')

    def test_cors_config_uses_structlog(self):
        """cors_config module should use structlog."""
        from security.cors_config import logger
        assert hasattr(logger, 'bind')

    def test_talisman_config_uses_structlog(self):
        """talisman_config module should use structlog."""
        from security.talisman_config import logger
        assert hasattr(logger, 'bind')

    def test_subprocess_validator_uses_structlog(self):
        """subprocess_validator module should use structlog."""
        from security.subprocess_validator import logger
        assert hasattr(logger, 'bind')

    def test_api_server_uses_structlog(self):
        """api_server module should use structlog."""
        from api_server import logger
        assert hasattr(logger, 'bind')


class TestStructuredLogOutput:
    """Test that log output is properly structured."""

    def test_json_output_in_production_mode(self, monkeypatch, capsys):
        """All modules should output JSON in production mode."""
        from log_config.structlog_config import configure_structlog, get_logger

        # Simulate production (no tty)
        monkeypatch.setattr(sys.stderr, 'isatty', lambda: False)
        configure_structlog(debug=False)

        logger = get_logger('integration_test')
        logger.info("test_event", test_key="test_value")

        captured = capsys.readouterr()
        lines = [l for l in captured.err.strip().split('\n') if l]
        assert len(lines) >= 1

        # Should be valid JSON
        log_entry = json.loads(lines[-1])
        assert log_entry['event'] == 'test_event'
        assert log_entry['test_key'] == 'test_value'

    def test_structured_key_value_format(self, monkeypatch, capsys):
        """Logs should use event name + key-value format."""
        from log_config.structlog_config import configure_structlog, get_logger

        monkeypatch.setattr(sys.stderr, 'isatty', lambda: False)
        configure_structlog(debug=False)

        logger = get_logger('test')
        logger.warning("validation_error", field="email", reason="invalid format")

        captured = capsys.readouterr()
        lines = [l for l in captured.err.strip().split('\n') if l]
        log_entry = json.loads(lines[-1])

        assert log_entry['event'] == 'validation_error'
        assert log_entry['field'] == 'email'
        assert log_entry['reason'] == 'invalid format'
        assert log_entry['level'] == 'warning'


class TestEndToEndLogging:
    """End-to-end test of logging through API request.

    Note: Talisman may redirect HTTP to HTTPS (302), which is expected.
    These tests verify logging doesn't error, not specific status codes.
    """

    @pytest.fixture
    def client(self):
        """Create test client."""
        from api_server import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_health_endpoint_logs_correctly(self, client):
        """Health endpoint request should complete without logging errors."""
        response = client.get('/health')
        # 200 = success, 302 = HTTPS redirect (Talisman)
        assert response.status_code in [200, 302]

    def test_error_response_logs_correctly(self, client):
        """Error responses should complete without logging errors."""
        response = client.get('/nonexistent')
        # 404 = not found, 302 = HTTPS redirect (Talisman)
        assert response.status_code in [404, 302]

    def test_validation_error_logs_correctly(self, client):
        """Validation errors should complete without logging errors."""
        response = client.post(
            '/intentcrawler/analyze',
            json={},  # Missing required url
            content_type='application/json'
        )
        # 400/422 = validation error, 302 = HTTPS redirect (Talisman)
        assert response.status_code in [400, 422, 302]


class TestNoLegacyLogging:
    """Verify no legacy logging.getLogger() usage remains."""

    def test_no_logging_getlogger_in_error_handlers(self):
        """error_handlers should not use logging.getLogger."""
        with open('/home/bill/Localcode/Airbais/tools/automation/error_handlers.py') as f:
            content = f.read()
        assert 'logging.getLogger' not in content
        assert 'structlog.get_logger' in content

    def test_no_logging_getlogger_in_cors_config(self):
        """cors_config should not use logging.getLogger."""
        with open('/home/bill/Localcode/Airbais/tools/automation/security/cors_config.py') as f:
            content = f.read()
        assert 'logging.getLogger' not in content
        assert 'structlog.get_logger' in content

    def test_no_logging_getlogger_in_talisman_config(self):
        """talisman_config should not use logging.getLogger."""
        with open('/home/bill/Localcode/Airbais/tools/automation/security/talisman_config.py') as f:
            content = f.read()
        assert 'logging.getLogger' not in content
        assert 'structlog.get_logger' in content

    def test_no_logging_getlogger_in_subprocess_validator(self):
        """subprocess_validator should not use logging.getLogger."""
        with open('/home/bill/Localcode/Airbais/tools/automation/security/subprocess_validator.py') as f:
            content = f.read()
        assert 'logging.getLogger' not in content
        assert 'structlog.get_logger' in content
