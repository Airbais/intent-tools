"""
Pytest configuration for automation tests.

This file is loaded before any test modules, allowing us to set
environment variables that affect module imports.
"""
import os

# Disable Talisman HTTPS redirect for all tests
# Must be set before api_server module is imported
os.environ['TALISMAN_FORCE_HTTPS'] = 'false'
