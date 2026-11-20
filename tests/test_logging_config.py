import logging
import os

import pytest

from eventor_mcp.config import Settings
from eventor_mcp.logging_config import setup_logging


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permissions")
def test_unwritable_log_dir_falls_back_to_stderr(tmp_path):
    locked = tmp_path / "locked"
    locked.mkdir(mode=0o500)
    settings = Settings(_env_file=None, LOG_DIR=str(locked / "logs"))

    try:
        setup_logging(settings)
        handlers = logging.getLogger().handlers
        assert len(handlers) == 1
        assert isinstance(handlers[0], logging.StreamHandler)
    finally:
        locked.chmod(0o700)
        logging.getLogger().handlers.clear()
