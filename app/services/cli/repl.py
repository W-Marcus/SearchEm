# Author: Marcus Wallin

from core.searcher import Searcher


def run_repl(searcher: Searcher, k: int = 5) -> None:
    print("\nSearchEm — type a query to search, or 'exit' / Ctrl+C to quit.")
    print(f"Returning top {k} results per query.\n")

    while True:
        try:
            query = input("query> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

        if not query:
            continue
        if query.lower() in {"exit", "quit", "q"}:
            print("Exiting.")
            break

        results = searcher.search(query, k=k)

        if not results:
            print("No results found.\n")
            continue

        print(f"\n{len(results)} result(s) for '{query}':")
        for result in results:
            print(result.display())
        print()
