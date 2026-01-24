"""
Tests for request/response logging middleware.
"""
import pytest
from flask import Flask
from automation.log_config import configure_request_logging, redact_sensitive


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

    def test_logs_get_request(self, client, capsys):
        """Test that GET request is logged."""
        response = client.get('/test')
        assert response.status_code == 200

        # Check that request start and completion are logged (structlog outputs to stdout)
        captured = capsys.readouterr()
        assert 'api_request_started' in captured.out
        assert 'api_request_completed' in captured.out
        assert 'GET' in captured.out
        assert '/test' in captured.out

    def test_logs_post_request(self, client, capsys):
        """Test that POST request is logged."""
        response = client.post('/test', json={'key': 'value'})
        assert response.status_code == 200

        captured = capsys.readouterr()
        assert 'api_request_started' in captured.out
        assert 'api_request_completed' in captured.out
        assert 'POST' in captured.out

    def test_logs_status_code(self, client, capsys):
        """Test that status code is logged."""
        response = client.get('/error')
        assert response.status_code == 404

        captured = capsys.readouterr()
        assert 'api_request_completed' in captured.out
        assert '404' in captured.out

    def test_logs_duration(self, client, capsys):
        """Test that duration is logged."""
        response = client.get('/test')
        assert response.status_code == 200

        captured = capsys.readouterr()
        assert 'api_request_completed' in captured.out
        assert 'duration_ms' in captured.out

    def test_redacts_sensitive_query_params(self, client, capsys):
        """Test that sensitive query params are redacted in logs."""
        response = client.get('/test?api_key=secret123&url=example.com')
        assert response.status_code == 200

        captured = capsys.readouterr()
        # Check logs don't contain the actual API key
        assert 'secret123' not in captured.out
        assert '[REDACTED]' in captured.out
        assert 'url' in captured.out
        assert 'example.com' in captured.out
