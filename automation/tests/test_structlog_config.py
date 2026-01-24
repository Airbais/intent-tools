"""Tests for structlog configuration."""
import json
import sys
import io
import pytest
import structlog

# Reset structlog between tests
@pytest.fixture(autouse=True)
def reset_structlog():
    """Reset structlog configuration between tests."""
    structlog.reset_defaults()
    yield
    structlog.reset_defaults()


class TestStructlogConfiguration:
    """Test structlog setup and output formats."""

    def test_configure_structlog_imports(self):
        """Configuration module should import without errors."""
        sys.path.insert(0, '/home/bill/Localcode/Airbais/tools/automation')
        from log_config.structlog_config import configure_structlog, get_logger
        assert callable(configure_structlog)
        assert callable(get_logger)

    def test_debug_mode_uses_console_renderer(self, capsys):
        """Debug mode should use ConsoleRenderer for pretty output."""
        sys.path.insert(0, '/home/bill/Localcode/Airbais/tools/automation')
        from log_config.structlog_config import configure_structlog, get_logger

        configure_structlog(debug=True)
        logger = get_logger('test')
        logger.info('test_event', foo='bar')

        captured = capsys.readouterr()
        # Console renderer outputs human-readable format
        assert 'test_event' in captured.err
        assert 'foo' in captured.err

    def test_production_mode_uses_json_renderer(self, monkeypatch, capsys):
        """Production mode (no tty) should use JSONRenderer."""
        sys.path.insert(0, '/home/bill/Localcode/Airbais/tools/automation')
        from log_config.structlog_config import configure_structlog, get_logger

        # Simulate non-tty environment
        monkeypatch.setattr(sys.stderr, 'isatty', lambda: False)

        configure_structlog(debug=False)
        logger = get_logger('test')
        logger.info('test_event', foo='bar')

        captured = capsys.readouterr()
        # JSON renderer outputs valid JSON
        lines = [l for l in captured.err.strip().split('\n') if l]
        assert len(lines) >= 1
        log_entry = json.loads(lines[-1])
        assert log_entry['event'] == 'test_event'
        assert log_entry['foo'] == 'bar'
        assert 'timestamp' in log_entry
        assert log_entry['level'] == 'info'

    def test_get_logger_returns_bound_logger(self):
        """get_logger should return a structlog BoundLogger."""
        sys.path.insert(0, '/home/bill/Localcode/Airbais/tools/automation')
        from log_config.structlog_config import configure_structlog, get_logger

        configure_structlog(debug=True)
        logger = get_logger('mymodule')
        assert logger is not None
        # Should have standard logging methods
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'debug')

    def test_context_variables_included(self, capsys, monkeypatch):
        """Bound context variables should appear in log output."""
        sys.path.insert(0, '/home/bill/Localcode/Airbais/tools/automation')
        from log_config.structlog_config import configure_structlog, get_logger

        monkeypatch.setattr(sys.stderr, 'isatty', lambda: False)
        configure_structlog(debug=False)

        # Bind context variable
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id='test-123')

        logger = get_logger('test')
        logger.info('with_context')

        captured = capsys.readouterr()
        lines = [l for l in captured.err.strip().split('\n') if l]
        log_entry = json.loads(lines[-1])
        assert log_entry.get('correlation_id') == 'test-123'

    def test_exception_formatting(self, capsys, monkeypatch):
        """Exceptions should be formatted as structured data in production."""
        sys.path.insert(0, '/home/bill/Localcode/Airbais/tools/automation')
        from log_config.structlog_config import configure_structlog, get_logger

        monkeypatch.setattr(sys.stderr, 'isatty', lambda: False)
        configure_structlog(debug=False)

        logger = get_logger('test')
        try:
            raise ValueError("test error")
        except ValueError:
            logger.exception('error_occurred')

        captured = capsys.readouterr()
        lines = [l for l in captured.err.strip().split('\n') if l]

        # Find the JSON log line (there may be a traceback after it)
        log_entry = None
        for line in lines:
            try:
                entry = json.loads(line)
                if entry.get('event') == 'error_occurred':
                    log_entry = entry
                    break
            except json.JSONDecodeError:
                continue

        assert log_entry is not None, "No JSON log entry found"
        assert log_entry['event'] == 'error_occurred'
        assert 'exception' in log_entry
