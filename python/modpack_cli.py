import argparse
import os
import sys

from modpack_providers import ProviderFactory


def choose_interactive(results):
    for idx, item in enumerate(results, 1):
        name = item.get("name") or item.get("title") or item.get("slug")
        ident = item.get("id") or item.get("slug") or item.get("project_id")
        print(f"{idx}. {name} ({ident})")
    while True:
        choice = input(f"Select modpack [1-{len(results)}]: ")
        if choice.isdigit() and 1 <= int(choice) <= len(results):
            return results[int(choice) - 1]
        print("Invalid selection")


def guess_best_match(results):
    return results[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Search and download modpacks")
    parser.add_argument("name", help="Name of the modpack to search for")
    parser.add_argument("--provider", "-p", default="curseforge",
                        choices=ProviderFactory.PROVIDERS.keys(),
                        help="Modpack provider")
    parser.add_argument("--dest", "-d", default=".", help="Download destination")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--interactive", "-i", action="store_true",
                     help="Pick a result interactively")
    mode.add_argument("--noninteractive", "-y", action="store_true",
                     help="Automatically pick the best match")
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    verbosity.add_argument("--quiet", "-q", action="store_true", help="Minimal output")
    args = parser.parse_args(argv)

    provider = ProviderFactory.create(args.provider)
    if args.verbose:
        print(f"Searching for '{args.name}' on {args.provider}")

    results = provider.search_modpacks(args.name)
    if not results:
        print("No modpacks found", file=sys.stderr)
        return 1

    if args.interactive and not args.noninteractive:
        chosen = choose_interactive(results)
    else:
        chosen = guess_best_match(results)
        if args.verbose:
            name = chosen.get("name") or chosen.get("title")
            print(f"Best match: {name}")

    modpack_id = chosen.get("id") or chosen.get("slug") or chosen.get("project_id")
    os.makedirs(args.dest, exist_ok=True)

    if not args.quiet:
        print(f"Downloading {modpack_id}...")
    path = provider.download_modpack(modpack_id, args.dest)
    if not args.quiet:
        print(f"Downloaded to {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
