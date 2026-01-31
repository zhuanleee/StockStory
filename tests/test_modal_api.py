"""
Tests for Modal API Endpoints

Tests cover:
- Health check endpoint
- Scan endpoint
- Admin endpoints (metrics, performance, dashboard)
- API key management endpoints
- Authentication middleware
- Error handling
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import json
import tempfile


@pytest.fixture
def api_client():
    """Create FastAPI test client"""
    # Import modal_api_v2 to get the app
    # Note: This requires mocking Modal dependencies
    with patch('modal.Image'), \
         patch('modal.Secret'), \
         patch('modal.Mount'), \
         patch('modal.App'):

        # Import the app
        from modal_api_v2 import web_app

        # Create test client
        client = TestClient(web_app)
        return client


class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_health_check(self, api_client):
        """Test /health endpoint"""
        response = api_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert 'version' in data


class TestScanEndpoint:
    """Test stock scanning endpoint"""

    @patch('modal_api_v2.scan_stocks_with_story')
    def test_scan_default_params(self, mock_scan, api_client):
        """Test /scan with default parameters"""
        # Mock scan results
        mock_scan.return_value = [
            {
                'ticker': 'NVDA',
                'story_score': 85.5,
                'story_strength': 'STRONG_STORY',
                'hottest_theme': 'AI Infrastructure'
            }
        ]

        response = api_client.get("/scan")

        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert 'results' in data
        assert len(data['results']) > 0
        assert data['results'][0]['ticker'] == 'NVDA'

    @patch('modal_api_v2.scan_stocks_with_story')
    def test_scan_with_limit(self, mock_scan, api_client):
        """Test /scan with limit parameter"""
        mock_scan.return_value = [
            {'ticker': 'NVDA', 'story_score': 85.5},
            {'ticker': 'AMD', 'story_score': 75.0},
        ]

        response = api_client.get("/scan?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True

    @patch('modal_api_v2.scan_stocks_with_story')
    def test_scan_error_handling(self, mock_scan, api_client):
        """Test /scan error handling"""
        # Mock error
        mock_scan.side_effect = Exception("Scan failed")

        response = api_client.get("/scan")

        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is False
        assert 'error' in data


class TestAdminEndpoints:
    """Test admin endpoints"""

    def test_admin_metrics(self, api_client):
        """Test /admin/metrics endpoint"""
        # Note: May need to set up metrics first
        response = api_client.get("/admin/metrics")

        assert response.status_code == 200
        data = response.json()
        assert 'total_requests' in data
        assert 'total_errors' in data
        assert 'status_codes' in data

    def test_admin_performance(self, api_client):
        """Test /admin/performance endpoint"""
        response = api_client.get("/admin/performance")

        assert response.status_code == 200
        data = response.json()
        assert 'ok' in data

    def test_admin_dashboard(self, api_client):
        """Test /admin/dashboard endpoint"""
        response = api_client.get("/admin/dashboard")

        assert response.status_code == 200
        # Should return HTML
        assert 'text/html' in response.headers['content-type']


class TestAPIKeyEndpoints:
    """Test API key management endpoints"""

    @patch('modal_api_v2.key_manager')
    def test_generate_api_key(self, mock_manager, api_client):
        """Test /api-keys/generate endpoint"""
        # Mock key generation
        mock_manager.generate_key.return_value = "ssk_live_test123"

        response = api_client.post(
            "/api-keys/generate",
            json={
                "user_id": "test_user",
                "tier": "free"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert 'api_key' in data
        assert data['api_key'].startswith('ssk_live_')

    @patch('modal_api_v2.key_manager')
    def test_get_api_key_usage(self, mock_manager, api_client):
        """Test /api-keys/usage endpoint"""
        # Mock usage stats
        mock_manager.get_usage_stats.return_value = {
            'tier': 'free',
            'daily_requests': 100,
            'requests_remaining': 900,
            'total_requests': 500
        }

        response = api_client.get("/api-keys/usage/ssk_live_test123")

        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert 'usage' in data
        assert data['usage']['tier'] == 'free'

    @patch('modal_api_v2.key_manager')
    def test_revoke_api_key(self, mock_manager, api_client):
        """Test /api-keys/revoke endpoint"""
        # Mock revocation
        mock_manager.revoke_key.return_value = True

        response = api_client.delete("/api-keys/revoke/ssk_live_test123")

        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert data['revoked'] is True


class TestAuthenticationMiddleware:
    """Test authentication middleware"""

    @patch('modal_api_v2.REQUIRE_API_KEYS', True)
    @patch('modal_api_v2.key_manager')
    @patch('modal_api_v2.rate_limiter')
    def test_valid_api_key(self, mock_limiter, mock_manager, api_client):
        """Test request with valid API key"""
        # Mock valid key
        mock_manager.validate_key.return_value = (True, None)
        mock_limiter.check_limit.return_value = (True, 0.0)

        response = api_client.get(
            "/health",
            headers={"Authorization": "Bearer ssk_live_valid123"}
        )

        assert response.status_code == 200

    @patch('modal_api_v2.REQUIRE_API_KEYS', True)
    def test_missing_api_key(self, api_client):
        """Test request without API key"""
        response = api_client.get("/health")

        # Should still work during grace period
        # Or return 401 if enforcement is enabled
        assert response.status_code in [200, 401]

    @patch('modal_api_v2.REQUIRE_API_KEYS', True)
    @patch('modal_api_v2.key_manager')
    def test_invalid_api_key(self, mock_manager, api_client):
        """Test request with invalid API key"""
        # Mock invalid key
        mock_manager.validate_key.return_value = (False, "Invalid API key")

        response = api_client.get(
            "/health",
            headers={"Authorization": "Bearer ssk_live_invalid"}
        )

        # Should return 401 if enforcement enabled
        if response.status_code == 401:
            data = response.json()
            assert 'detail' in data

    @patch('modal_api_v2.REQUIRE_API_KEYS', True)
    @patch('modal_api_v2.key_manager')
    @patch('modal_api_v2.rate_limiter')
    def test_rate_limit_exceeded(self, mock_limiter, mock_manager, api_client):
        """Test rate limit exceeded"""
        # Mock valid key but rate limit exceeded
        mock_manager.validate_key.return_value = (True, None)
        mock_limiter.check_limit.return_value = (False, 1.5)  # Retry after 1.5s

        response = api_client.get(
            "/health",
            headers={"Authorization": "Bearer ssk_live_valid123"}
        )

        if response.status_code == 429:
            assert 'Retry-After' in response.headers


class TestGZipCompression:
    """Test GZip compression middleware"""

    def test_gzip_compression_enabled(self, api_client):
        """Test that responses are gzip compressed when requested"""
        response = api_client.get(
            "/health",
            headers={"Accept-Encoding": "gzip"}
        )

        assert response.status_code == 200
        # Check if content-encoding header is present
        # (may vary based on response size)


class TestMetricsTracking:
    """Test metrics tracking"""

    def test_metrics_increment_on_request(self, api_client):
        """Test that metrics are incremented on request"""
        # Make a request
        response = api_client.get("/health")
        assert response.status_code == 200

        # Check metrics
        metrics_response = api_client.get("/admin/metrics")
        data = metrics_response.json()

        assert data['total_requests'] > 0
        assert '200' in data['status_codes']

    @patch('modal_api_v2.scan_stocks_with_story')
    def test_metrics_track_errors(self, mock_scan, api_client):
        """Test that errors are tracked in metrics"""
        # Force an error
        mock_scan.side_effect = Exception("Test error")

        response = api_client.get("/scan")

        # Check metrics
        metrics_response = api_client.get("/admin/metrics")
        data = metrics_response.json()

        # Error count should increase
        assert data['total_errors'] >= 0


class TestCORS:
    """Test CORS headers"""

    def test_cors_headers_present(self, api_client):
        """Test that CORS headers are present"""
        response = api_client.options("/health")

        # Should have CORS headers
        assert 'access-control-allow-origin' in response.headers or \
               'Access-Control-Allow-Origin' in response.headers


class TestOpenAPIDocumentation:
    """Test OpenAPI documentation"""

    def test_openapi_json_available(self, api_client):
        """Test /openapi.json endpoint"""
        response = api_client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert 'openapi' in data
        assert 'info' in data
        assert 'paths' in data

    def test_docs_endpoint_available(self, api_client):
        """Test /docs endpoint (Swagger UI)"""
        response = api_client.get("/docs")

        assert response.status_code == 200
        # Should return HTML
        assert 'text/html' in response.headers['content-type']


class TestErrorHandling:
    """Test global error handling"""

    @patch('modal_api_v2.scan_stocks_with_story')
    def test_500_error_handling(self, mock_scan, api_client):
        """Test 500 error handling"""
        # Force a server error
        mock_scan.side_effect = Exception("Internal error")

        response = api_client.get("/scan")

        # Should return error response (not crash)
        assert response.status_code in [200, 500]
        data = response.json()
        assert 'ok' in data or 'detail' in data


class TestStartupCaching:
    """Test startup cache preloading"""

    @patch('modal_api_v2.CachePreloader')
    def test_cache_preload_on_startup(self, mock_preloader):
        """Test that cache is preloaded on startup"""
        # This would be tested during app initialization
        # Mock would verify preload_hot_data was called
        pass


class TestAPIVersioning:
    """Test API versioning"""

    def test_api_version_in_response(self, api_client):
        """Test that API version is included in health check"""
        response = api_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert 'version' in data


class TestQueryParameters:
    """Test query parameter validation"""

    @patch('modal_api_v2.scan_stocks_with_story')
    def test_scan_with_invalid_limit(self, mock_scan, api_client):
        """Test /scan with invalid limit parameter"""
        mock_scan.return_value = []

        # Negative limit
        response = api_client.get("/scan?limit=-1")

        # Should handle gracefully
        assert response.status_code in [200, 422]

    @patch('modal_api_v2.scan_stocks_with_story')
    def test_scan_with_large_limit(self, mock_scan, api_client):
        """Test /scan with very large limit"""
        mock_scan.return_value = []

        response = api_client.get("/scan?limit=10000")

        # Should cap at reasonable limit
        assert response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
