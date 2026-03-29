# Author: Marcus Wallin

import logging
from pathlib import Path

import yaml
from pydantic import BaseModel

from config.args import CommonArgs, DEFAULT_MODEL

SETTINGS_FILENAME = "settings.yaml"

DEFAULT_EXTENSIONS: list[str] = [
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".pdf",
    ".docx",
    ".txt",
    ".md",
    ".java",
    ".py",
    ".epub",
]


class Settings(BaseModel):
    model: str = DEFAULT_MODEL
    extensions: list[str] = DEFAULT_EXTENSIONS

    @classmethod
    def load(cls, database: Path) -> "Settings":
        """Load settings from database directory, returning defaults if not found."""
        path = database / SETTINGS_FILENAME
        if not path.exists():
            return cls()
        with path.open("r") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            return cls()
        return cls.model_validate(data)

    def save(self, database: Path) -> None:
        """Save settings to database directory."""
        with (database / SETTINGS_FILENAME).open("w") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False)

    def resolve_model(self, args: CommonArgs) -> str:
        """Use args model if explicitly provided, otherwise fall back to settings."""
        if args.model != DEFAULT_MODEL:
            return args.model
        return self.model

    def resolve_extensions(self, args: CommonArgs) -> list[str]:
        """Use args extensions if explicitly provided, otherwise fall back to settings."""
        if args.extensions is not None:
            return args.extensions
        return self.extensions


def _setup_logging(logging_path: Path, level: int = logging.INFO) -> logging.Logger:
    """Set up logging to both file and console."""
    logging_path.mkdir(parents=True, exist_ok=True)
    log_file = logging_path / "SearchEm.log"

    logger = logging.getLogger("searchem")
    logger.setLevel(level)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def setup(args: CommonArgs) -> tuple[CommonArgs, Settings, logging.Logger]:
    """Create directories, load settings, resolve model and extensions, save updated settings."""
    assert args.database is not None, "database path must be resolved before setup"
    assert args.logging_path is not None, "logging path must be resolved before setup"

    args.database.mkdir(parents=True, exist_ok=True)
    args.logging_path.mkdir(parents=True, exist_ok=True)

    logger = _setup_logging(args.logging_path)
    logger.info("Starting SearchEm")
    logger.info("Database: %s", args.database)

    settings = Settings.load(args.database)

    args.model = settings.resolve_model(args)
    settings.model = args.model

    settings.extensions = settings.resolve_extensions(args)
    logger.info("Extensions: %s", settings.extensions)

    settings.save(args.database)

    return args, settings, logger
