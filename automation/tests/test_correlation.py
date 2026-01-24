"""Tests for correlation ID middleware."""

import pytest
import uuid
from flask import Flask
from log_config.correlation import (
    configure_correlation,
    get_correlation_id,
    CORRELATION_HEADER,
)


@pytest.fixture
def app():
    """Create a test Flask app with correlation middleware."""
    test_app = Flask(__name__)
    configure_correlation(test_app)

    @test_app.route('/test')
    def test_endpoint():
        """Test endpoint that returns correlation ID."""
        return {'correlation_id': get_correlation_id()}

    @test_app.route('/error')
    def error_endpoint():
        """Test endpoint that raises an error."""
        raise ValueError("Test error")

    return test_app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


def test_generates_correlation_id_when_not_provided(client):
    """Test that correlation ID is generated when not provided in request."""
    response = client.get('/test')

    # Response should include correlation ID header
    assert CORRELATION_HEADER in response.headers
    correlation_id = response.headers[CORRELATION_HEADER]

    # Should be valid UUID format
    try:
        uuid.UUID(correlation_id)
    except ValueError:
        pytest.fail(f"Generated correlation ID '{correlation_id}' is not a valid UUID")

    # Response body should also have it
    assert response.json['correlation_id'] == correlation_id


def test_preserves_provided_correlation_id(client):
    """Test that provided correlation ID is preserved."""
    provided_id = str(uuid.uuid4())

    response = client.get('/test', headers={CORRELATION_HEADER: provided_id})

    # Response should return the same correlation ID
    assert response.headers[CORRELATION_HEADER] == provided_id
    assert response.json['correlation_id'] == provided_id


def test_different_requests_get_different_ids(client):
    """Test that different requests without correlation ID get different UUIDs."""
    response1 = client.get('/test')
    response2 = client.get('/test')

    id1 = response1.headers[CORRELATION_HEADER]
    id2 = response2.headers[CORRELATION_HEADER]

    # Each request should get a unique correlation ID
    assert id1 != id2


def test_correlation_id_on_error_response(client):
    """Test that correlation ID is included even on error responses."""
    provided_id = str(uuid.uuid4())

    # Make request to endpoint that raises error
    response = client.get('/error', headers={CORRELATION_HEADER: provided_id})

    # Even on error (500), correlation ID should be in response
    assert response.status_code == 500
    assert CORRELATION_HEADER in response.headers
    assert response.headers[CORRELATION_HEADER] == provided_id


def test_correlation_id_on_not_found(client):
    """Test that correlation ID is included on 404 responses."""
    provided_id = str(uuid.uuid4())

    response = client.get('/nonexistent', headers={CORRELATION_HEADER: provided_id})

    # 404 response should still include correlation ID
    assert response.status_code == 404
    assert CORRELATION_HEADER in response.headers
    assert response.headers[CORRELATION_HEADER] == provided_id


def test_correlation_id_format_preserved(client):
    """Test that non-UUID correlation IDs are preserved as-is."""
    # Some systems use custom correlation ID formats (not UUID)
    custom_id = "custom-correlation-12345"

    response = client.get('/test', headers={CORRELATION_HEADER: custom_id})

    # Should preserve the custom format
    assert response.headers[CORRELATION_HEADER] == custom_id
    assert response.json['correlation_id'] == custom_id
