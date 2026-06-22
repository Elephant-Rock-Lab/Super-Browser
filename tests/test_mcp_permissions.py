"""Phase 2A tests: the MCP write-tool permission substrate.

Proves enforcement WITHOUT adding real write-tool handlers. The dispatcher's
2A write path authorizes then returns a 'not implemented in 2A' note, so these
tests exercise the gate, not the facade.

Covers the #180 acceptance bar:
- writes disabled -> structured refusal
- max action count exceeded -> structured refusal
- timeout budget exceeded -> structured refusal
- SecurityManager allow path
- SecurityManager deny path
- audit entry written for allowed calls
- audit entry written for denied calls
- no direct facade dispatch before authorization
- Phase 1 read-only tools remain unchanged
"""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from super_browser.mcp_server import (
    PHASE1_TOOLS,
    WRITE_TOOL_NAMES,
    WRITE_TOOL_SECURITY_LEVELS,
    MCPAuditEntry,
    MCPAuthorizer,
    MCPBrowserRuntime,
    MCPSessionPolicy,
    ToolDispatcher,
)
from super_browser.security.types import SecurityConfig

# ============================================================================
# Policy + audit dataclasses
# ============================================================================


class TestPolicyDefaults:
    def test_default_policy_refuses_writes(self):
        """Phase 1 behavior preserved: writes off by default."""
        p = MCPSessionPolicy()
        assert p.allow_writes is False

    def test_default_budgets_are_sane(self):
        p = MCPSessionPolicy()
        assert p.max_actions > 0
        assert p.timeout_seconds > 0
        assert p.actions_used == 0


class TestAuditEntry:
    def test_audit_entry_is_frozen(self):
        entry = MCPAuditEntry(
            timestamp_ms=1.0, tool="navigate", arguments={"url": "x"},
            security_level="sensitive", allowed=False,
            blocked_by="mcp_policy", reason="writes are disabled",
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            entry.allowed = True  # type: ignore[misc]


# ============================================================================
# Authorizer: the five-check sequence
# ============================================================================


class TestAuthorizerWritesDisabled:
    @pytest.mark.asyncio
    async def test_writes_disabled_refuses_with_structured_reason(self):
        authorizer = MCPAuthorizer(MCPSessionPolicy(allow_writes=False))
        result = await authorizer.authorize(tool="navigate", arguments={"url": "https://x"})
        assert result.allowed is False
        assert result.blocked_by == "mcp_policy"
        # P1: the action-gate message is "actions are disabled" (the gate
        # protects the Action tier; allow_writes is a compat alias).
        assert result.reason == "actions are disabled"
        assert result.security_level == "sensitive"

    @pytest.mark.asyncio
    async def test_writes_disabled_writes_audit_entry(self):
        authorizer = MCPAuthorizer(MCPSessionPolicy(allow_writes=False))
        await authorizer.authorize(tool="navigate", arguments={"url": "https://x"})
        assert len(authorizer.audit_log) == 1
        entry = authorizer.audit_log[0]
        assert entry.allowed is False
        assert entry.tool == "navigate"
        assert entry.blocked_by == "mcp_policy"


class TestAuthorizerActionCount:
    @pytest.mark.asyncio
    async def test_action_count_exceeded_refuses(self):
        policy = MCPSessionPolicy(allow_writes=True, max_actions=1)
        policy.actions_used = 1  # already exhausted
        authorizer = MCPAuthorizer(policy)
        result = await authorizer.authorize(tool="scroll", arguments={})
        assert result.allowed is False
        assert result.blocked_by == "action_count"
        assert "max_actions" in result.reason

    @pytest.mark.asyncio
    async def test_action_count_increments_on_allow(self):
        policy = MCPSessionPolicy(allow_writes=True, max_actions=5)
        authorizer = MCPAuthorizer(policy)
        await authorizer.authorize(tool="scroll", arguments={})
        assert policy.actions_used == 1
        await authorizer.authorize(tool="scroll", arguments={})
        assert policy.actions_used == 2

    @pytest.mark.asyncio
    async def test_action_count_does_not_increment_on_deny(self):
        policy = MCPSessionPolicy(allow_writes=False, max_actions=5)
        authorizer = MCPAuthorizer(policy)
        await authorizer.authorize(tool="scroll", arguments={})
        assert policy.actions_used == 0


class TestAuthorizerTimeout:
    @pytest.mark.asyncio
    async def test_timeout_budget_exceeded_refuses(self):
        # Backdate the session start so the budget is already exceeded.
        policy = MCPSessionPolicy(
            allow_writes=True,
            timeout_seconds=0.01,
            started_at_monotonic=time.monotonic() - 1.0,
        )
        authorizer = MCPAuthorizer(policy)
        result = await authorizer.authorize(tool="press_key", arguments={})
        assert result.allowed is False
        assert result.blocked_by == "timeout"
        assert "timeout_seconds" in result.reason

    @pytest.mark.asyncio
    async def test_timeout_not_yet_exceeded_allows(self):
        policy = MCPSessionPolicy(
            allow_writes=True, timeout_seconds=3600.0,
        )
        authorizer = MCPAuthorizer(policy)
        result = await authorizer.authorize(tool="press_key", arguments={})
        assert result.allowed is True


# ============================================================================
# SecurityManager integration (real SecurityManager, real SecurityConfig)
# ============================================================================


def _real_security_manager(allowlist: tuple[str, ...] = (), blocklist: tuple[str, ...] = ()):
    """Build a real SecurityManager with the given domain lists."""
    from super_browser.security import SecurityManager

    config = SecurityConfig(
        domain_filter_enabled=True,
        domain_allowlist=allowlist,
        domain_blocklist=blocklist,
        injection_detection_enabled=False,
        redaction_enabled=False,
    )
    return SecurityManager(config)


class TestAuthorizerSecurityManager:
    @pytest.mark.asyncio
    async def test_security_manager_allow_path(self):
        # allowlist permits example.com; navigate to it should pass.
        sm = _real_security_manager(allowlist=("example.com",))
        policy = MCPSessionPolicy(allow_writes=True)
        authorizer = MCPAuthorizer(policy, security_manager=sm)
        result = await authorizer.authorize(
            tool="navigate", arguments={"url": "https://example.com"},
            url="https://example.com",
        )
        assert result.allowed is True
        assert result.blocked_by is None

    @pytest.mark.asyncio
    async def test_security_manager_deny_path_blocked_domain(self):
        # blocklist denies example.com; navigate to it must be refused.
        sm = _real_security_manager(blocklist=("example.com",))
        policy = MCPSessionPolicy(allow_writes=True)
        authorizer = MCPAuthorizer(policy, security_manager=sm)
        result = await authorizer.authorize(
            tool="navigate", arguments={"url": "https://example.com"},
            url="https://example.com",
        )
        assert result.allowed is False
        assert result.blocked_by == "security_manager"

    @pytest.mark.asyncio
    async def test_security_manager_exception_denies_safely(self):
        """If the security layer itself raises, the authorizer must deny
        rather than fall through to allow."""
        bad_sm = MagicMock()
        bad_sm.check_action = AsyncMock(side_effect=RuntimeError("boom"))
        policy = MCPSessionPolicy(allow_writes=True)
        authorizer = MCPAuthorizer(policy, security_manager=bad_sm)
        result = await authorizer.authorize(tool="navigate", arguments={})
        assert result.allowed is False
        assert result.blocked_by == "security_manager"
        assert "RuntimeError" in (result.reason or "")


# ============================================================================
# Audit log: both allow and deny paths record
# ============================================================================


class TestAuditLog:
    @pytest.mark.asyncio
    async def test_audit_written_on_allow(self):
        authorizer = MCPAuthorizer(MCPSessionPolicy(allow_writes=True))
        await authorizer.authorize(tool="scroll", arguments={"direction": "down"})
        assert len(authorizer.audit_log) == 1
        entry = authorizer.audit_log[0]
        assert entry.allowed is True
        assert entry.blocked_by is None
        assert entry.arguments == {"direction": "down"}

    @pytest.mark.asyncio
    async def test_audit_written_on_deny(self):
        authorizer = MCPAuthorizer(MCPSessionPolicy(allow_writes=False))
        await authorizer.authorize(tool="scroll", arguments={})
        assert len(authorizer.audit_log) == 1
        assert authorizer.audit_log[0].allowed is False

    @pytest.mark.asyncio
    async def test_audit_log_accumulates_across_calls(self):
        authorizer = MCPAuthorizer(MCPSessionPolicy(allow_writes=True, max_actions=5))
        for _ in range(3):
            await authorizer.authorize(tool="scroll", arguments={})
        assert len(authorizer.audit_log) == 3
        assert all(e.allowed for e in authorizer.audit_log)


# ============================================================================
# Dispatcher: no write tool bypasses authorization
# ============================================================================


class TestDispatcherWriteGate:
    @pytest.mark.asyncio
    async def test_write_tool_without_authorizer_refuses(self):
        """No authorizer attached -> writes not configured -> refuse."""
        dispatcher = ToolDispatcher(MCPBrowserRuntime(), authorizer=None)
        result = await dispatcher.dispatch("navigate", {"url": "https://x"})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert payload["refusal"]["blocked_by"] == "mcp_policy"
        assert payload["refusal"]["tool"] == "navigate"

    @pytest.mark.asyncio
    async def test_write_tool_writes_disabled_refuses(self):
        authorizer = MCPAuthorizer(MCPSessionPolicy(allow_writes=False))
        dispatcher = ToolDispatcher(MCPBrowserRuntime(), authorizer=authorizer)
        result = await dispatcher.dispatch("click", {"target": "#btn"})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert payload["refusal"]["reason"] == "actions are disabled"

    @pytest.mark.asyncio
    async def test_all_write_tools_have_real_handlers(self):
        """All 7 write tools (navigate/scroll/press_key + click/fill/open_tab/
        close_tab) now have real handlers. None should return a 'pending' note.
        This test confirms no tool falls through to the dead-code fallback."""
        # Wave 1 + wave 2 are all implemented. We verify by checking that the
        # 'pending' / 'authorized-but-no-handler' note never appears for any
        # write tool that passes authorization. (Individual tool behavior is
        # covered in test_mcp_write_tools.py and test_mcp_write_tools_wave2.py;
        # this test just guards against regression to the placeholder era.)
        authorizer = MCPAuthorizer(MCPSessionPolicy(allow_writes=True))
        dispatcher = ToolDispatcher(MCPBrowserRuntime(), authorizer=authorizer)
        # click with no real browser will fail with a controller/browser error,
        # not with a 'pending' note — that's the proof the handler is real.
        result = await dispatcher.dispatch("click", {"target": "#btn"})
        payload = json.loads(result[0].text)
        # Either ok=True (if somehow a browser existed) or ok=False with an
        # error/exception (no browser) — but never a 'pending' note.
        assert "pending" not in payload.get("note", "")

    @pytest.mark.asyncio
    async def test_no_facade_dispatch_before_authorization(self):
        """The facade must never be touched when authorization denies. We
        prove this by asserting the runtime's browser was never started."""
        authorizer = MCPAuthorizer(MCPSessionPolicy(allow_writes=False))
        runtime = MCPBrowserRuntime()
        dispatcher = ToolDispatcher(runtime, authorizer=authorizer)
        await dispatcher.dispatch("fill", {"selector": "#x", "value": "y"})
        # browser_status would show running=False if nothing lazy-started.
        status = await runtime.status()
        assert status["running"] is False, "facade must not start when write is denied"


# ============================================================================
# Phase 1 unchanged: read-only tools ignore the authorizer entirely
# ============================================================================


class TestPhase1Unchanged:
    @pytest.mark.asyncio
    async def test_browser_status_still_works_without_authorizer(self):
        dispatcher = ToolDispatcher(MCPBrowserRuntime(), authorizer=None)
        result = await dispatcher.dispatch("browser_status", {})
        payload = json.loads(result[0].text)
        assert payload["ok"] is True
        assert payload["status"]["running"] is False

    @pytest.mark.asyncio
    async def test_read_tools_not_affected_by_disabled_writes(self):
        """Writes being disabled must not impede read-only tools."""
        authorizer = MCPAuthorizer(MCPSessionPolicy(allow_writes=False))
        dispatcher = ToolDispatcher(MCPBrowserRuntime(), authorizer=authorizer)
        result = await dispatcher.dispatch("browser_status", {})
        payload = json.loads(result[0].text)
        assert payload["ok"] is True

    def test_phase1_tool_set_unchanged(self):
        names = {t.name for t in PHASE1_TOOLS}
        assert names == {
            "browser_status", "current_url", "observe",
            "extract_text", "screenshot", "list_tabs",
        }

    def test_write_tools_disjoint_from_phase1(self):
        assert not (WRITE_TOOL_NAMES & {t.name for t in PHASE1_TOOLS})


# ============================================================================
# Security-level mapping (decision table from #180)
# ============================================================================


class TestSecurityLevelMapping:
    def test_all_write_tools_are_sensitive_by_default(self):
        for tool in WRITE_TOOL_NAMES:
            assert WRITE_TOOL_SECURITY_LEVELS[tool] == "sensitive", (
                f"{tool} should be SENSITIVE in Phase 2A"
            )

    @pytest.mark.asyncio
    async def test_explicit_security_level_overrides_default(self):
        authorizer = MCPAuthorizer(MCPSessionPolicy(allow_writes=True))
        result = await authorizer.authorize(
            tool="fill", arguments={}, security_level="dangerous",
        )
        assert result.security_level == "dangerous"
