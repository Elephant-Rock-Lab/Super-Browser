"""Interactive REPL mode for Super Browser CLI.

Provides a persistent browser session where commands can be issued one at a
time.  The browser stays alive between commands (HB-24-01).

Usage::

    from super_browser.cli.interactive import run_interactive
    await run_interactive()

Or from the command line::

    super-browser interactive
"""

from __future__ import annotations

import sys

from super_browser import SuperBrowser
from super_browser.testing import MockLLMClient
from super_browser.cli.commands import dispatch


async def run_interactive(
    *,
    prompt: str = "sb> ",
    output: object = sys.stdout,
    input_stream: object | None = None,
) -> None:
    """Run the interactive REPL loop.

    Creates a single ``SuperBrowser`` backed by ``MockLLMClient`` (no API key
    needed — HB-24-03) and keeps it alive until the user types ``close``,
    ``quit``, ``exit``, or EOF.

    :param prompt: REPL prompt string.
    :param output: Writable file-like for output (default: stdout).
    :param input_stream: Readable file-like for input (default: stdin).
    """
    sb = SuperBrowser(llm_client=MockLLMClient())
    await sb.start()

    _write = output.write if hasattr(output, "write") else sys.stdout.write
    _flush = output.flush if hasattr(output, "flush") else sys.stdout.flush
    _readline = (
        input_stream.readline
        if input_stream and hasattr(input_stream, "readline")
        else sys.stdin.readline
    )

    _write("Super Browser Interactive REPL\n")
    _write("Type 'help' for available commands.\n\n")
    _flush()

    try:
        while True:
            try:
                _write(prompt)
                _flush()
                line = _readline()
                if not line:
                    # EOF
                    _write("\n")
                    _flush()
                    break
                line = line.rstrip("\n").rstrip("\r")
            except (KeyboardInterrupt, EOFError):
                _write("\n")
                _flush()
                break

            result = await dispatch(sb, line)

            if result.output:
                _write(str(result))
                _write("\n")
            _flush()

            if result.should_exit:
                break
    finally:
        # Ensure browser is stopped even on unexpected exit
        if sb.is_running:
            await sb.stop()
