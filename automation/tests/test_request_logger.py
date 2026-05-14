"""
Tests for request/response logging middleware.
"""
import sys
import pytest
import structlog
from flask import Flask
from automation.log_config import configure_request_logging, redact_sensitive
from automation.log_config.structlog_config import configure_structlog


class TestRedactSensitive:
    """Test sensitive data redaction."""

    def test_redacts_password_field(self):
        """Test that password field is redacted."""
        data = {'username': 'user', 'password': 'secret123'}
        result = redact_sensitive(data)
        assert result['username'] == 'user'
        assert result['password'] == '[REDACTED]'

    def test_redacts_token_field(self):
        """Test that token field is redacted."""
        data = {'user_id': 123, 'token': 'abc123xyz'}
        result = redact_sensitive(data)
        assert result['user_id'] == 123
        assert result['token'] == '[REDACTED]'

    def test_redacts_api_key_variations(self):
        """Test that various API key field names are redacted."""
        data = {
            'api_key': 'key1',
            'apikey': 'key2',
            'api-key': 'key3'
        }
        result = redact_sensitive(data)
        assert result['api_key'] == '[REDACTED]'
        assert result['apikey'] == '[REDACTED]'
        assert result['api-key'] == '[REDACTED]'

    def test_redacts_nested_sensitive_fields(self):
        """Test that nested sensitive fields are redacted."""
        data = {
            'user': {
                'name': 'John',
                'password': 'secret',
                'email': 'john@example.com'
            }
        }
        result = redact_sensitive(data)
        assert result['user']['name'] == 'John'
        assert result['user']['password'] == '[REDACTED]'
        assert result['user']['email'] == 'john@example.com'

    def test_case_insensitive_redaction(self):
        """Test that redaction is case-insensitive."""
        data = {
            'PASSWORD': 'secret',
            'Password': 'secret',
            'Token': 'abc123'
        }
        result = redact_sensitive(data)
        assert result['PASSWORD'] == '[REDACTED]'
        assert result['Password'] == '[REDACTED]'
        assert result['Token'] == '[REDACTED]'

    def test_non_sensitive_fields_preserved(self):
        """Test that non-sensitive fields are preserved."""
        data = {
            'url': 'https://example.com',
            'max_pages': 100,
            'crawl_depth': 3
        }
        result = redact_sensitive(data)
        assert result == data

    def test_handles_non_dict_input(self):
        """Test that non-dict input is returned unchanged."""
        assert redact_sensitive('string') == 'string'
        assert redact_sensitive(123) == 123
        assert redact_sensitive(None) is None
        assert redact_sensitive([1, 2, 3]) == [1, 2, 3]

    def test_empty_dict(self):
        """Test that empty dict is handled."""
        assert redact_sensitive({}) == {}


class TestRequestLoggingIntegration:
    """Integration tests for request logging middleware."""

    @pytest.fixture(autouse=True)
    def reset_structlog(self, monkeypatch):
        """Reset and configure structlog for test capturing."""
        structlog.reset_defaults()
        # Force non-tty to get JSON output to stderr
        monkeypatch.setattr(sys.stderr, 'isatty', lambda: False)
        configure_structlog(debug=False)
        yield
        structlog.reset_defaults()

    @pytest.fixture
    def app(self):
        """Create test Flask app with request logging."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        configure_request_logging(app)

        @app.route('/test', methods=['GET', 'POST'])
        def test_endpoint():
            return {'message': 'success'}, 200

        @app.route('/error')
        def error_endpoint():
            return {'error': 'not found'}, 404

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_logs_get_request(self, client, caplog):
        """Test that GET request is logged."""
        with caplog.at_level('INFO'):
            response = client.get('/test')
        assert response.status_code == 200

        # Check that request start and completion are logged via caplog records
        log_messages = [r.message for r in caplog.records]
        log_output = ' '.join(log_messages)
        assert 'api_request_started' in log_output
        assert 'api_request_completed' in log_output
        assert 'GET' in log_output
        assert '/test' in log_output

    def test_logs_post_request(self, client, caplog):
        """Test that POST request is logged."""
        with caplog.at_level('INFO'):
            response = client.post('/test', json={'key': 'value'})
        assert response.status_code == 200

        log_messages = [r.message for r in caplog.records]
        log_output = ' '.join(log_messages)
        assert 'api_request_started' in log_output
        assert 'api_request_completed' in log_output
        assert 'POST' in log_output

    def test_logs_status_code(self, client, caplog):
        """Test that status code is logged."""
        with caplog.at_level('INFO'):
            response = client.get('/error')
        assert response.status_code == 404

        log_messages = [r.message for r in caplog.records]
        log_output = ' '.join(log_messages)
        assert 'api_request_completed' in log_output
        assert '404' in log_output

    def test_logs_duration(self, client, caplog):
        """Test that duration is logged."""
        with caplog.at_level('INFO'):
            response = client.get('/test')
        assert response.status_code == 200

        log_messages = [r.message for r in caplog.records]
        log_output = ' '.join(log_messages)
        assert 'api_request_completed' in log_output
        assert 'duration_ms' in log_output

    def test_redacts_sensitive_query_params(self, client, caplog):
        """Test that sensitive query params are redacted in logs."""
        with caplog.at_level('INFO'):
            response = client.get('/test?api_key=secret123&url=example.com')
        assert response.status_code == 200

        log_messages = [r.message for r in caplog.records]
        log_output = ' '.join(log_messages)
        # Check logs don't contain the actual API key
        assert 'secret123' not in log_output
        assert '[REDACTED]' in log_output
        assert 'url' in log_output
        assert 'example.com' in log_output
