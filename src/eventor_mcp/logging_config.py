from __future__ import annotations

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from eventor_mcp.config import Settings


def setup_logging(settings: Settings) -> None:
    """Configure root logger: console + optional timed rotating file logs."""

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, settings.log_level, logging.INFO))

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(root.level)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    if settings.log_dir:
        log_dir = Path(settings.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "eventor-mcp.log"
        fh = TimedRotatingFileHandler(
            log_path,
            when=settings.log_rotation_when,
            backupCount=settings.log_backup_count,
            encoding="utf-8",
        )
        fh.setLevel(root.level)
        fh.setFormatter(fmt)
        root.addHandler(fh)
