# Author: Marcus Wallin

import argparse
from pathlib import Path

DEFAULT_MODEL: str = "Qwen/Qwen3-VL-Embedding-2B"
WORKING_DIR_PATH: Path = Path.cwd()


class Args(argparse.Namespace):
    dir: Path
    database: Path | None
    logging_path: Path | None
    model: str
    extensions: list[str] | None
    top_k: int
    refresh: bool
    update: bool


def parse_args(args: list[str] | None = None) -> Args:
    parser = argparse.ArgumentParser(
        description="A seMantic search tool.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--dir",
        "-d",
        default=WORKING_DIR_PATH,
        type=Path,
        help="Directory of files to embed.",
    )
    parser.add_argument(
        "--database",
        "-db",
        default=None,
        type=Path,
        help="Database directory. Defaults to <dir>/.SearchEm",
    )
    parser.add_argument(
        "--extensions",
        "-e",
        nargs="+",  # accepts one or more values
        default=None,  # None means use those in settings.yaml, else default values."
        metavar="EXT",
        help="File extensions to index e.g. .jpg .png .pdf. Overrides settings.",
    )
    parser.add_argument(
        "--logging-path",
        "-lp",
        default=None,
        type=Path,
        help="Directory where log files will be written. Defaults to <database>/logs",
    )
    parser.add_argument(
        "--model",
        "-m",
        default=DEFAULT_MODEL,
        help="HuggingFace model ID to use for embedding.",
    )

    parser.add_argument(
        "--refresh",
        "-r",
        action="store_true",
        help="Embed new or changed files.",
    )
    parser.add_argument(
        "--top-k",
        "-k",
        default=5,
        type=int,
        metavar="K",
        help="Number of results to return per query.",
    )
    parser.add_argument(
        "--update",
        "-u",
        action="store_true",
        help="Re-embed files that have already been processed. Also embeds new or changed files. Required if changing model.",
    )

    parsed = parser.parse_args(args, namespace=Args())

    # Normalise extensions to always have a leading dot
    if parsed.extensions is not None:
        parsed.extensions = [
            e if e.startswith(".") else f".{e}" for e in parsed.extensions
        ]

    # Dependent paths unless user-provided
    if parsed.database is None:
        parsed.database = parsed.dir / ".SearchEm"
    if parsed.logging_path is None:
        parsed.logging_path = parsed.database / "logs"

    return parsed
