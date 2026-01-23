"""
Flask-Talisman security headers configuration.

Provides comprehensive security headers:
- HSTS (Strict-Transport-Security)
- CSP (Content-Security-Policy)
- X-Frame-Options
- X-Content-Type-Options
- Referrer-Policy

NOTE: This is for the API server only. Dashboard has separate CSP needs
due to Dash inline scripts (requires csp_hashes()).
"""
import os
import logging
from flask_talisman import Talisman

logger = logging.getLogger(__name__)


def get_api_csp():
    """
    Get Content Security Policy for API server.

    API server serves JSON responses, so CSP is restrictive.
    No scripts, no styles, no fonts needed.
    """
    return {
        'default-src': "'none'",  # Deny everything by default
        'frame-ancestors': "'none'",  # Prevent embedding (clickjacking)
        'base-uri': "'none'",  # Prevent base tag hijacking
        'form-action': "'self'",  # Allow forms to submit to same origin
    }


def configure_talisman(app, force_https: bool = None):
    """
    Configure Flask-Talisman security headers.

    Args:
        app: Flask application
        force_https: Force HTTPS redirects. Default: True in production, False in debug

    Security headers applied:
    - Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
    - X-Frame-Options: DENY
    - X-Content-Type-Options: nosniff
    - Referrer-Policy: strict-origin-when-cross-origin
    - Content-Security-Policy: restrictive for API

    NOTE: force_https should be True in production but may need
    to be False when behind a reverse proxy that handles TLS.
    Set TALISMAN_FORCE_HTTPS=false env var to disable.
    """
    # Determine force_https setting
    if force_https is None:
        # Check environment variable first
        env_force_https = os.getenv('TALISMAN_FORCE_HTTPS', '').lower()
        if env_force_https in ('false', '0', 'no'):
            force_https = False
        elif env_force_https in ('true', '1', 'yes'):
            force_https = True
        else:
            # Default: force HTTPS in production, not in debug
            force_https = not app.debug

    csp = get_api_csp()

    talisman = Talisman(
        app,
        # Content Security Policy
        content_security_policy=csp,
        content_security_policy_report_only=False,

        # Strict Transport Security (HSTS)
        strict_transport_security=True,
        strict_transport_security_max_age=31536000,  # 1 year
        strict_transport_security_include_subdomains=True,
        strict_transport_security_preload=True,

        # Force HTTPS redirects (configurable for proxy setups)
        force_https=force_https,

        # X-Frame-Options: DENY (prevent clickjacking)
        frame_options='DENY',
        frame_options_allow_from=None,

        # X-Content-Type-Options: nosniff (prevent MIME sniffing)
        x_content_type_options=True,

        # X-XSS-Protection: Deprecated, but Talisman includes it
        # Modern browsers use CSP instead

        # Referrer-Policy
        referrer_policy='strict-origin-when-cross-origin',

        # Feature-Policy / Permissions-Policy
        # Restrict browser features for API (not needed)
        feature_policy={},

        # Session cookie settings (if using sessions)
        session_cookie_secure=force_https,
        session_cookie_http_only=True,
    )

    if force_https:
        logger.info("Talisman configured with HTTPS enforcement")
    else:
        logger.info("Talisman configured without HTTPS enforcement (debug mode or proxy)")

    return talisman
