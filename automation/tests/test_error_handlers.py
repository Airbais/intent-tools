"""
Tests for error handler sanitization.

Verifies that error responses:
- Hide stack traces and internal implementation details
- Return consistent JSON structure
- Don't expose file paths or system internals
- Log full error details for debugging
"""

import pytest
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_server import app


@pytest.fixture
def client():
    """Create test client with Flask test mode enabled."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestErrorResponses:
    """Test error response sanitization and structure."""

    def test_404_does_not_expose_paths(self, client):
        """404 errors should not echo requested paths in response."""
        response = client.get('/nonexistent/endpoint/with/path')
        assert response.status_code == 404

        data = json.loads(response.data)
        assert 'error' in data
        assert data['error'] == 'Not found'

        # Verify path is not echoed in response
        response_str = response.data.decode('utf-8')
        assert 'nonexistent' not in response_str.lower()
        assert '/endpoint/' not in response_str

    def test_invalid_json_returns_400(self, client):
        """Invalid JSON should return 400 without exposing internals."""
        response = client.post(
            '/intentcrawler/analyze',
            data='{"invalid": json}',  # Malformed JSON
            content_type='application/json'
        )

        # Should return 400 (bad request)
        assert response.status_code in (400, 404)  # 404 if tool not recognized first

        data = json.loads(response.data)
        assert 'error' in data

        # Should not contain traceback or file paths
        response_str = response.data.decode('utf-8')
        assert 'Traceback' not in response_str
        assert 'File "' not in response_str
        assert '.py' not in response_str or 'py' in data.get('message', '').lower()

    def test_missing_required_params_returns_400(self, client):
        """Missing required parameters should return structured 400 error."""
        # Try to analyze without required 'url' parameter
        response = client.post(
            '/intentcrawler/analyze',
            json={},  # Empty body, missing required params
            content_type='application/json'
        )

        assert response.status_code == 400

        data = json.loads(response.data)
        assert 'error' in data

        # Should mention required parameters
        response_str = response.data.decode('utf-8').lower()
        assert 'required' in response_str or 'missing' in response_str

        # Should not contain file paths or tracebacks
        assert 'traceback' not in response_str
        assert '/home/' not in response_str
        assert 'file "' not in response_str

    def test_unknown_tool_returns_404(self, client):
        """Unknown tool should return 404 with safe error message."""
        response = client.post(
            '/nonexistent_tool/analyze',
            json={'url': 'https://example.com'},
            content_type='application/json'
        )

        assert response.status_code == 404

        data = json.loads(response.data)
        assert 'error' in data

        # Should not expose internal configuration or file paths
        response_str = response.data.decode('utf-8')
        assert '.py' not in response_str
        assert '/tools/' not in response_str

    def test_error_response_format_consistent(self, client):
        """All error responses should have consistent JSON structure."""
        # Test 404
        response_404 = client.get('/nonexistent')
        data_404 = json.loads(response_404.data)
        assert 'error' in data_404
        assert isinstance(data_404['error'], str)

        # Test 400 (missing params)
        response_400 = client.post(
            '/intentcrawler/analyze',
            json={},
            content_type='application/json'
        )
        data_400 = json.loads(response_400.data)
        assert 'error' in data_400
        assert isinstance(data_400['error'], str)


class TestJobErrorSanitization:
    """Test that job errors don't expose internal details."""

    def test_job_not_found_returns_404(self, client):
        """Non-existent job ID should return 404."""
        response = client.get('/status/nonexistent-job-id')
        assert response.status_code == 404

        data = json.loads(response.data)
        assert 'error' in data

        # Should not expose job storage implementation
        response_str = response.data.decode('utf-8')
        assert 'dict' not in response_str.lower()
        assert 'jobs[' not in response_str

    def test_results_for_incomplete_job_returns_400(self, client):
        """Requesting results for incomplete job should return 400."""
        # First create a job
        response = client.post(
            '/intentcrawler/analyze',
            json={'url': 'https://example.com'},
            content_type='application/json'
        )

        if response.status_code == 202:
            data = json.loads(response.data)
            job_id = data.get('job_id')

            # Try to get results immediately (before completion)
            results_response = client.get(f'/results/{job_id}')

            # Should return 400 or 404, not 500
            assert results_response.status_code in (400, 404)

            results_data = json.loads(results_response.data)
            assert 'error' in results_data


class TestHealthEndpoint:
    """Test health endpoint returns expected data."""

    def test_health_check_succeeds(self, client):
        """Health endpoint should return 200 with status."""
        response = client.get('/health')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'status' in data
        assert data['status'] == 'healthy'
        assert 'tools' in data
        assert 'timestamp' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
