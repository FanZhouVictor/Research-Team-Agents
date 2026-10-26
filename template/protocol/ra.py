"""Command-line entry point: python protocol/ra.py <command>.

This file only starts the command line in ra/cli.py. Inside this script, 'import ra' finds
the package that sits next to it: a package directory wins over a same-named .py file in
the same directory, and the script itself runs as __main__.
"""

import io
import sys

from ra.cli import main

if __name__ == "__main__":
    # Paths and names can be non-ASCII. Write them as UTF-8 even where pipes default to a
    # legacy code page (cp1252 on many Windows setups): a created path must not be lost to
    # an encoding error after its file exists.
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")
    sys.exit(main())
