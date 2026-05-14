"""
Tests for tool execution logging in api_server.py.

Verifies:
- Job creation returns valid UUIDs
- Analyze endpoint accepts requests and returns job_id
- Status endpoint validates job ID format
- Status endpoint returns 404 for nonexistent jobs
"""

import json
import pytest
import uuid
from unittest.mock import patch, MagicMock
import sys
import os

# Disable HTTPS redirect for tests BEFORE importing app
os.environ['TALISMAN_FORCE_HTTPS'] = '0'

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_server import app, create_job, jobs, job_lock


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def clear_jobs():
    """Clear jobs dictionary before each test."""
    with job_lock:
        jobs.clear()
    yield
    with job_lock:
        jobs.clear()


class TestJobCreation:
    """Tests for job creation functionality."""

    def test_create_job_returns_valid_uuid(self, clear_jobs):
        """Test that create_job returns a valid UUID."""
        job_id = create_job('intentcrawler')

        # Verify it's a valid UUID
        try:
            uuid_obj = uuid.UUID(job_id)
            assert str(uuid_obj) == job_id
        except ValueError:
            pytest.fail(f"create_job returned invalid UUID: {job_id}")

    def test_create_job_stores_job_data(self, clear_jobs):
        """Test that create_job stores job in jobs dictionary."""
        job_id = create_job('intentcrawler')

        assert job_id in jobs
        assert jobs[job_id]['tool'] == 'intentcrawler'
        assert jobs[job_id]['status'] == 'queued'
        assert jobs[job_id]['id'] == job_id


class TestAnalyzeEndpoint:
    """Tests for /<tool_name>/analyze POST endpoint."""

    @patch('api_server.threading.Thread')
    @patch('api_server.TOOL_CONFIGS', {
        'intentcrawler': {
            'name': 'Intent Crawler',
            'required_params': ['url'],
            'optional_params': ['max_pages']
        }
    })
    def test_analyze_accepts_valid_request(self, mock_thread, client, clear_jobs):
        """Test that analyze endpoint accepts valid requests and returns job_id."""
        response = client.post(
            '/intentcrawler/analyze',
            data=json.dumps({'url': 'https://example.com'}),
            content_type='application/json'
        )

        assert response.status_code == 202
        data = json.loads(response.data)
        assert 'job_id' in data
        assert 'status' in data
        assert data['status'] == 'queued'

        # Verify job_id is valid UUID
        try:
            uuid.UUID(data['job_id'])
        except ValueError:
            pytest.fail(f"Returned job_id is not valid UUID: {data['job_id']}")

        # Verify thread was started
        mock_thread.assert_called_once()

    @patch('api_server.TOOL_CONFIGS', {})
    def test_analyze_returns_404_for_unknown_tool(self, client, clear_jobs):
        """Test that analyze endpoint returns 404 for unknown tools."""
        response = client.post(
            '/unknowntool/analyze',
            data=json.dumps({'url': 'https://example.com'}),
            content_type='application/json'
        )

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Unknown tool' in data['error']


class TestStatusEndpoint:
    """Tests for /status/<job_id> GET endpoint."""

    def test_status_returns_400_for_invalid_job_id_format(self, client, clear_jobs):
        """Test that status endpoint validates job ID format."""
        invalid_ids = [
            'not-a-uuid',
            '12345',
            'invalid-uuid-format',
            'XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX',  # Invalid characters
            '12345678-1234-1234-1234-12345678901',  # Wrong length
        ]

        for invalid_id in invalid_ids:
            response = client.get(f'/status/{invalid_id}')
            assert response.status_code == 400, f"Expected 400 for invalid ID: {invalid_id}"
            data = json.loads(response.data)
            assert 'error' in data
            assert 'Invalid job ID format' in data['error']

    def test_status_returns_404_for_nonexistent_job(self, client, clear_jobs):
        """Test that status endpoint returns 404 for nonexistent valid UUID."""
        # Generate a valid UUID that doesn't exist in jobs
        nonexistent_job_id = str(uuid.uuid4())

        response = client.get(f'/status/{nonexistent_job_id}')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Job not found' in data['error']
        assert data['job_id'] == nonexistent_job_id

    def test_status_returns_200_for_existing_job(self, client, clear_jobs):
        """Test that status endpoint returns job details for existing job."""
        # Create a job
        job_id = create_job('intentcrawler')

        response = client.get(f'/status/{job_id}')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['job_id'] == job_id
        assert data['tool'] == 'intentcrawler'
        assert data['status'] == 'queued'
        assert 'created_at' in data
        assert 'updated_at' in data


class TestHealthEndpoint:
    """Tests for /health GET endpoint."""

    def test_health_check_returns_200(self, client):
        """Test that health check endpoint returns 200."""
        response = client.get('/health')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert 'tools' in data
        assert 'active_jobs' in data
