# Author: Marcus Wallin
# TODO: Should perhaps be moved from config.
import argparse
from pathlib import Path

DEFAULT_MODEL: str = (
    "Qwen/Qwen3-VL-Embedding-2B"  # Quite heavy depending on hardware. Consider switching default to a lighter-weight model, and see if it is possible to use different models for different extensions.
)
WORKING_DIR_PATH: Path = Path.cwd()


class CommonArgs(argparse.Namespace):
    dir: Path
    database: Path | None
    logging_path: Path | None
    model: str
    extensions: list[str] | None


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Register shared flags onto any parser. The shared flags deal with core functionality independent of ingress (CLI/REST)."""
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
        nargs="+",
        default=None,
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


def resolve_common_paths(args: CommonArgs) -> None:
    """Resolve dependent paths in-place. Call after parsing."""
    if args.database is None:
        args.database = args.dir / ".SearchEm"
    if args.logging_path is None:
        args.logging_path = args.database / "logs"
    if args.extensions is not None:
        args.extensions = [e if e.startswith(".") else f".{e}" for e in args.extensions]
