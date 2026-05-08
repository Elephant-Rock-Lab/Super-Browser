"""CLI subpackage — interactive mode, script execution, replay, and memory commands."""

from __future__ import annotations

import argparse
from pathlib import Path


def memory_handler(args: argparse.Namespace) -> None:
    """Handle ``super-browser memory`` CLI commands: list, show, clear, prune."""
    from super_browser.memory.store import MemoryStore

    memory_dir = getattr(args, "dir", None) or "~/.config/super-browser/memory"
    ttl = getattr(args, "ttl", 30)
    store = MemoryStore(Path(memory_dir).expanduser(), ttl_days=ttl)

    if args.memory_command == "list":
        domains = store.list_domains()
        if not domains:
            print("No domains with memory.")
        else:
            print(f"Domains with memory ({len(domains)}):")
            for d in domains:
                mem = store.load(d)
                seq_count = len(mem.sequences)
                sel_count = len(mem.selectors)
                print(f"  {d}  ({seq_count} sequences, {sel_count} selectors)")
        return

    if args.memory_command == "show":
        mem = store.load(args.domain)
        if not mem.sequences and not mem.selectors and not mem.preferences:
            print(f"No memory for domain: {args.domain}")
        else:
            print(f"Memory for {args.domain}:")
            if mem.sequences:
                print(f"  Sequences ({len(mem.sequences)}):")
                for seq in mem.sequences:
                    status = "✓" if seq.success else "✗"
                    print(f"    {status} {seq.task} ({len(seq.actions)} actions, used {seq.used_count}x)")
            if mem.selectors:
                print(f"  Selectors ({len(mem.selectors)}):")
                for element, selector in mem.selectors.items():
                    print(f"    {element}: {selector}")
            if mem.preferences:
                print("  Preferences:")
                for key, value in mem.preferences.items():
                    print(f"    {key}: {value}")
        return

    if args.memory_command == "clear":
        store.clear(args.domain)
        print(f"Cleared memory for domain: {args.domain}")
        return

    if args.memory_command == "prune":
        removed = store.prune()
        print(f"Pruned {removed} expired entries.")
        return

    print("Usage: super-browser memory {list|show|clear|prune}")
