"""Command-line entry point: python protocol/ra.py <command>.

This file only starts the command line in ra/cli.py. Inside this script, 'import ra' finds
the package that sits next to it: a package directory wins over a same-named .py file in
the same directory, and the script itself runs as __main__.
"""

import sys

from ra.cli import main

if __name__ == "__main__":
    sys.exit(main())
