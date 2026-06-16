"""Entry point for ``python -m super_browser``.

Delegates to the CLI dispatcher so users can run either::

    superbrowser version
    python -m super_browser version
"""

from super_browser.cli import main

if __name__ == "__main__":
    main()
