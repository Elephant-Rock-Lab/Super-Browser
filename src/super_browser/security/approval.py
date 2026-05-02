"""CommandApprover — dangerous command pattern matching with optional LLM classify."""

from __future__ import annotations

import re
import time
from typing import Optional

from super_browser.security.types import (
    CommandSafety,
    CommandVerdict,
    SecurityConfig,
)

_DANGEROUS_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("rm -rf", re.compile(r"\brm\s+-rf\b"), "Recursive force file deletion"),
    ("rm -r", re.compile(r"\brm\s+-r\b"), "Recursive file deletion"),
    ("rmdir", re.compile(r"\brmdir\b"), "Directory removal"),
    ("del /s/q", re.compile(r"\bdel\s+/[sq]"), "Force file deletion (Windows)"),
    ("sudo", re.compile(r"\bsudo\b"), "Privilege escalation"),
    ("su", re.compile(r"\bsu\s+\w"), "User switch"),
    ("chmod 777", re.compile(r"\bchmod\s+777\b"), "Insecure permissions"),
    ("chown", re.compile(r"\bchown\b"), "Ownership change"),
    ("curl pipe sh", re.compile(r"curl\s+.*\|\s*(?:ba)?sh"), "Remote code execution"),
    ("wget pipe sh", re.compile(r"wget\s+.*\|\s*(?:ba)?sh"), "Remote code execution"),
    ("nc listen", re.compile(r"\bnc\s+-l\b"), "Network listener"),
    ("iptables", re.compile(r"\biptables\b"), "Firewall modification"),
    ("mkfs", re.compile(r"\bmkfs\b"), "Filesystem format"),
    ("dd", re.compile(r"\bdd\s+if="), "Disk dump"),
    ("mount", re.compile(r"\bmount\b"), "Filesystem mount"),
    ("kill -9", re.compile(r"\bkill\s+-9\b"), "Force kill process"),
    ("shutdown", re.compile(r"\bshutdown\b"), "System shutdown"),
    ("reboot", re.compile(r"\breboot\b"), "System reboot"),
    ("eval", re.compile(r"\beval\s+\("), "Dynamic code execution"),
    ("exec", re.compile(r"\bexec\s+\("), "Process replacement"),
    ("format", re.compile(r"\bformat\s+[A-Za-z]:", re.IGNORECASE), "Disk format (Windows)"),
    ("rd /s/q", re.compile(r"\brd\s+/[sq]", re.IGNORECASE), "Directory removal (Windows)"),
    ("taskkill", re.compile(r"\btaskkill\b", re.IGNORECASE), "Process kill (Windows)"),
    ("net user", re.compile(r"\bnet\s+user\b", re.IGNORECASE), "User management"),
    ("net localgroup", re.compile(r"\bnet\s+localgroup\b", re.IGNORECASE), "Group management"),
    ("reg add", re.compile(r"\breg\s+add\b", re.IGNORECASE), "Registry modification"),
    ("reg delete", re.compile(r"\breg\s+delete\b", re.IGNORECASE), "Registry deletion"),
    ("powershell encodedcommand", re.compile(r"-EncodedCommand", re.IGNORECASE), "Encoded PowerShell"),
    ("bash -c", re.compile(r"\bbash\s+-c\b"), "Shell command execution"),
    ("python -c", re.compile(r"\bpython\d?\s+-c\b"), "Python code execution"),
]

_SAFE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ls", re.compile(r"\bls\b")),
    ("cat", re.compile(r"\bcat\s+")),
    ("head", re.compile(r"\bhead\b")),
    ("tail", re.compile(r"\btail\b")),
    ("wc", re.compile(r"\bwc\b")),
    ("echo", re.compile(r"\becho\s+(?!\s*>)")),
    ("pwd", re.compile(r"\bpwd\b")),
    ("whoami", re.compile(r"\bwhoami\b")),
    ("which", re.compile(r"\bwhich\b")),
    ("type", re.compile(r"\btype\s+")),
    ("dir", re.compile(r"\bdir\b", re.IGNORECASE)),
    ("find", re.compile(r"\bfind\s+")),
    ("grep", re.compile(r"\bgrep\b")),
    ("git status", re.compile(r"\bgit\s+status\b")),
    ("git log", re.compile(r"\bgit\s+log\b")),
    ("git diff", re.compile(r"\bgit\s+diff\b")),
]


class CommandApprover:

    def __init__(self, config: SecurityConfig) -> None:
        self._config = config

    async def evaluate(self, command: str, context: str = "") -> CommandVerdict:
        start = time.perf_counter()

        for name, compiled in _SAFE_PATTERNS:
            if compiled.search(command):
                elapsed = (time.perf_counter() - start) * 1000
                return CommandVerdict(
                    safety=CommandSafety.SAFE,
                    matched_pattern=name,
                    classification_time_ms=elapsed,
                )

        for name, compiled, reason in _DANGEROUS_PATTERNS:
            if compiled.search(command):
                elapsed = (time.perf_counter() - start) * 1000
                return CommandVerdict(
                    safety=CommandSafety.DANGEROUS,
                    matched_pattern=name,
                    reason=reason,
                    classification_time_ms=elapsed,
                )

        if self._config.llm_auto_approve_enabled and self._config.llm_auto_approve_client:
            return await self._llm_classify(command, context)

        elapsed = (time.perf_counter() - start) * 1000
        return CommandVerdict(safety=CommandSafety.SAFE, classification_time_ms=elapsed)

    async def _llm_classify(self, command: str, context: str) -> CommandVerdict:
        start = time.perf_counter()
        try:
            client = self._config.llm_auto_approve_client
            prompt = (
                f"Is this command safe to execute in a browser automation context? "
                f"Command: {command}. Context: {context}. Answer SAFE or DANGEROUS."
            )
            result = client(prompt)
            if hasattr(result, '__await__'):
                result = await result
            answer = str(result).strip().upper()
            elapsed = (time.perf_counter() - start) * 1000
            if "DANGEROUS" in answer:
                return CommandVerdict(
                    safety=CommandSafety.LLM_DENIED,
                    reason="LLM classified as dangerous",
                    classification_time_ms=elapsed,
                )
            return CommandVerdict(
                safety=CommandSafety.LLM_APPROVED,
                reason="LLM classified as safe",
                classification_time_ms=elapsed,
            )
        except Exception:
            elapsed = (time.perf_counter() - start) * 1000
            return CommandVerdict(
                safety=CommandSafety.DANGEROUS,
                reason="LLM classification failed",
                classification_time_ms=elapsed,
            )
