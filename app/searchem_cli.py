# Author: Marcus Wallin

from config.settings import setup
from core.embedder import Embedder
from core.scanner import Scanner
from core.searcher import Searcher
from models.cli.args import parse_args
from services.cli.repl import run_repl


def main() -> None:
    args = parse_args()
    args, settings, logger = setup(args)

    assert args.database is not None

    if args.refresh or args.update:
        scanner = Scanner(args.dir, args.database, settings.extensions)
        result = scanner.scan(force_reprocess=args.update)

        if result.to_process:
            embedder = Embedder(args.model, args.dir, args.database)
            embedder.embed_index(result.to_process)
            embedder.commit()
            result.commit(args.dir, args.database)
        else:
            logger.info("No new or changed files found.")
    else:
        logger.info("Skipping indexing. Use --refresh or --update to embed files.")

    try:
        searcher = Searcher(
            database=args.database,
            directory=args.dir,
            model_id=args.model,
        )
        run_repl(searcher, k=args.top_k)
    except (FileNotFoundError, IndexError) as e:
        logger.error("%s", e)


if __name__ == "__main__":
    main()
