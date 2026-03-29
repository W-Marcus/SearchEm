import argparse

from config.args import CommonArgs, add_common_args, resolve_common_paths


class CliArgs(CommonArgs):
    top_k: int
    refresh: bool
    update: bool


def parse_args(args: list[str] | None = None) -> CliArgs:
    parser = argparse.ArgumentParser(
        description="A seMantic search tool.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_common_args(parser)
    parser.add_argument(
        "--refresh", "-r",
        action="store_true",
        help="Embed new or changed files.",
    )
    parser.add_argument(
        "--top-k", "-k",
        default=5,
        type=int,
        metavar="K",
        help="Number of results to return per query.",
    )
    parser.add_argument(
        "--update", "-u",
        action="store_true",
        help="Re-embed all files. Also embeds new or changed files. Required if changing model.",
    )

    parsed = parser.parse_args(args, namespace=CliArgs())
    resolve_common_paths(parsed)
    return parsed
