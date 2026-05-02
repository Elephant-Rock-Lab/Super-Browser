"""PromptInjectionDetector — regex + Unicode injection scanning."""

from __future__ import annotations

import re
import time
from typing import Optional

from super_browser.security.types import (
    InjectionMatch,
    InjectionPattern,
    InjectionVerdict,
    RiskLevel,
    SecurityConfig,
)

_BUILTIN_PATTERNS: list[tuple[InjectionPattern, str, str, RiskLevel]] = [
    (InjectionPattern.SYSTEM_OVERRIDE, "system_override_1",
     r"ignore\s+(all\s+)?previous\s+instructions", RiskLevel.CRITICAL),
    (InjectionPattern.SYSTEM_OVERRIDE, "system_override_2",
     r"disregard\s+(all\s+)?(above|previous)", RiskLevel.CRITICAL),
    (InjectionPattern.SYSTEM_OVERRIDE, "system_override_3",
     r"forget\s+(all\s+)?(your\s+)?(previous\s+)?instructions", RiskLevel.CRITICAL),
    (InjectionPattern.ROLE_MANIPULATION, "role_manipulation_1",
     r"you\s+are\s+now\s+", RiskLevel.HIGH),
    (InjectionPattern.ROLE_MANIPULATION, "role_manipulation_2",
     r"new\s+instruction", RiskLevel.HIGH),
    (InjectionPattern.ROLE_MANIPULATION, "role_manipulation_3",
     r"act\s+as\s+(if\s+)?you\s+(are|were)\s+", RiskLevel.HIGH),
    (InjectionPattern.DATA_EXFILTRATION, "data_exfiltration_1",
     r"send\s+(your\s+)?(prompt|system\s+message|instructions)", RiskLevel.CRITICAL),
    (InjectionPattern.DATA_EXFILTRATION, "data_exfiltration_2",
     r"reveal\s+your\s+(system|hidden|internal)\s+", RiskLevel.HIGH),
    (InjectionPattern.DATA_EXFILTRATION, "data_exfiltration_3",
     r"repeat\s+(back\s+)?(everything|your\s+instructions)", RiskLevel.HIGH),
    (InjectionPattern.JAILBREAK, "jailbreak_1",
     r"\bDAN\b", RiskLevel.CRITICAL),
    (InjectionPattern.JAILBREAK, "jailbreak_2",
     r"do\s+anything\s+now", RiskLevel.CRITICAL),
    (InjectionPattern.JAILBREAK, "jailbreak_3",
     r"jailbreak", RiskLevel.HIGH),
    (InjectionPattern.INSTRUCTION_INJECTION, "instruction_injection_1",
     r"hidden\s+instruction", RiskLevel.MEDIUM),
    (InjectionPattern.INSTRUCTION_INJECTION, "instruction_injection_2",
     r"execute\s+this", RiskLevel.MEDIUM),
    (InjectionPattern.INSTRUCTION_INJECTION, "instruction_injection_3",
     r"system\s*:\s*", RiskLevel.HIGH),
    (InjectionPattern.CONTEXT_POISONING, "context_poisoning_1",
     r"adversarial\s+context", RiskLevel.MEDIUM),
    (InjectionPattern.CONTEXT_POISONING, "context_poisoning_2",
     r"injected\s+(content|payload|text)", RiskLevel.MEDIUM),
]

_UNICODE_RANGES: list[tuple[int, int, str, str]] = [
    (0x200B, 0x200B, "zero-width space (U+200B)", "ZWSP"),
    (0x200C, 0x200C, "zero-width non-joiner (U+200C)", "ZWNJ"),
    (0x200D, 0x200D, "zero-width joiner (U+200D)", "ZWJ"),
    (0x202A, 0x202E, "bidirectional override", "BIDI"),
    (0x00AD, 0x00AD, "soft hyphen (U+00AD)", "SHY"),
    (0x2060, 0x2060, "word joiner (U+2060)", "WJ"),
    (0xFEFF, 0xFEFF, "BOM/zero-width no-break (U+FEFF)", "BOM"),
]

_HOMOGLYPHS: dict[int, tuple[str, str]] = {
    0x0430: ("Cyrillic a (U+0430)", "HOMOGLYPH"),
    0x0435: ("Cyrillic e (U+0435)", "HOMOGLYPH"),
    0x043E: ("Cyrillic o (U+043E)", "HOMOGLYPH"),
    0x0440: ("Cyrillic p (U+0440)", "HOMOGLYPH"),
    0x0441: ("Cyrillic c (U+0441)", "HOMOGLYPH"),
    0x0456: ("Cyrillic i (U+0456)", "HOMOGLYPH"),
}


class PromptInjectionDetector:

    def __init__(self, config: SecurityConfig) -> None:
        self._patterns: list[tuple[InjectionPattern, str, re.Pattern[str], RiskLevel]] = []
        self._config = config
        self._load_patterns()

    def _load_patterns(self) -> None:
        for pattern_type, name, regex, risk in _BUILTIN_PATTERNS:
            self._patterns.append((pattern_type, name, re.compile(regex, re.IGNORECASE), risk))

    def scan(self, text: str) -> InjectionVerdict:
        start = time.perf_counter()
        matches = self._scan_regex(text)
        if self._config.unicode_detection_enabled:
            matches.extend(self._scan_unicode(text))
        matches.sort(key=lambda m: m.position)

        max_risk = RiskLevel.LOW
        for m in matches:
            if m.risk_level == RiskLevel.CRITICAL:
                max_risk = RiskLevel.CRITICAL
                break
            if m.risk_level == RiskLevel.HIGH:
                max_risk = RiskLevel.HIGH
        blocked = max_risk in (RiskLevel.HIGH, RiskLevel.CRITICAL)

        sanitized = self._sanitize(text, matches) if matches else text
        elapsed = (time.perf_counter() - start) * 1000
        return InjectionVerdict(
            blocked=blocked,
            matches=matches,
            sanitized_text=sanitized,
            risk_level=max_risk,
            scan_time_ms=elapsed,
        )

    def _scan_regex(self, text: str) -> list[InjectionMatch]:
        matches: list[InjectionMatch] = []
        for pattern_type, name, compiled, risk in self._patterns:
            for m in compiled.finditer(text):
                matches.append(InjectionMatch(
                    pattern=pattern_type,
                    pattern_name=name,
                    matched_text=m.group(),
                    position=m.start(),
                    risk_level=risk,
                ))
        return matches

    def _scan_unicode(self, text: str) -> list[InjectionMatch]:
        matches: list[InjectionMatch] = []
        for i, ch in enumerate(text):
            cp = ord(ch)
            for lo, hi, desc, _tag in _UNICODE_RANGES:
                if lo <= cp <= hi:
                    matches.append(InjectionMatch(
                        pattern=InjectionPattern.UNICODE_OBFUSCATION,
                        pattern_name=desc,
                        matched_text=ch,
                        position=i,
                        risk_level=RiskLevel.HIGH,
                    ))
                    break
            else:
                info = _HOMOGLYPHS.get(cp)
                if info is not None:
                    matches.append(InjectionMatch(
                        pattern=InjectionPattern.UNICODE_OBFUSCATION,
                        pattern_name=info[0],
                        matched_text=ch,
                        position=i,
                        risk_level=RiskLevel.MEDIUM,
                    ))
        return matches

    def _sanitize(self, text: str, matches: list[InjectionMatch]) -> str:
        result = list(text)
        offset = 0
        for m in sorted(matches, key=lambda x: x.position):
            start = m.position + offset
            end = start + len(m.matched_text)
            replacement = "[INJECTION:blocked]"
            result[start:end] = list(replacement)
            offset += len(replacement) - len(m.matched_text)
        return "".join(result)

    @property
    def pattern_count(self) -> int:
        return len(self._patterns)
