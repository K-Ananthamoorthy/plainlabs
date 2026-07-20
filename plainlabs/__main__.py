"""CLI: python -m plainlabs <report.pdf|.png|.txt>"""
import sys

from plainlabs.graph import run


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: python -m plainlabs <report.pdf|.png|.txt>")
    print(run(sys.argv[1]))


if __name__ == "__main__":
    main()
