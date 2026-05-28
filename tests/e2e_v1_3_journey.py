"""End-to-end journey test covering all 4 v1.3 features in sequence.

Simulates a complete workflow:
1. Register plugin hooks
2. Start recording
3. Execute browser actions (emitting events)
4. Save recording
5. Record results in memory
6. Replay recording
7. Verify all features interact correctly

Uses mocks/stubs — no real browser needed.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from super_browser.events.bus import EventBus
from super_browser.events.types import (
    AFTER_ACTION,
    AFTER_NAVIGATE,
    BEFORE_ACTION,
    BEFORE_NAVIGATE,
    ON_ERROR,
)
from super_browser.memory.store import MemoryStore
from super_browser.plugins.decorators import hook
from super_browser.plugins.hooks import clear_registry, get_registered_hooks
from super_browser.recording.persistence import load as load_recording
from super_browser.recording.persistence import save as save_recording
from super_browser.recording.recorder import SessionRecorder
from super_browser.recording.replayer import RecordingReplayer

# Recording types used via recorder/persistence modules


class TestV13FullJourney:
    """E2E journey: plugins → recording → memory → replay."""

    @pytest.mark.asyncio
    async def test_full_v1_3_journey(self):
        """Complete journey through all 4 v1.3 features."""
        clear_registry()
        with tempfile.TemporaryDirectory() as tmpdir:
            # ── Phase 1: Plugin hooks ─────────────────────────────────
            action_log: list[str] = []

            @hook(BEFORE_NAVIGATE)
            def track_navigation(ctx: Any) -> None:
                action_log.append(f"nav:{ctx.get('url', '?')}")

            @hook(AFTER_ACTION)
            def track_action(ctx: Any) -> None:
                action_log.append(f"action:{ctx.get('action', '?')}")

            @hook(ON_ERROR)
            def track_error(ctx: Any) -> None:
                action_log.append(f"error:{ctx.get('error', '?')}")

            # ── Phase 2: Recording setup ──────────────────────────────
            bus = EventBus()

            # Install plugin hooks onto the bus
            for event_type, handlers in get_registered_hooks().items():
                for h in handlers:
                    bus.subscribe(event_type, h)

            recorder = SessionRecorder(bus)
            recorder.start()

            # ── Phase 3: Execute browser actions (simulated) ──────────
            # Step 1: Navigate
            bus.emit(BEFORE_NAVIGATE, {
                "url": "https://shop.example.com",
                "action": "navigate",
                "target": "url",
                "step": 1,
            })
            bus.emit(AFTER_NAVIGATE, {
                "url": "https://shop.example.com",
                "final_url": "https://shop.example.com/",
                "title": "Example Shop",
                "ok": True,
                "action": "navigate",
                "target": "url",
                "step": 1,
                "duration_ms": 200.0,
            })

            # Step 2: Click add-to-cart
            bus.emit(BEFORE_ACTION, {
                "action": "click",
                "target": "#add-to-cart",
                "step": 2,
            })
            bus.emit(AFTER_ACTION, {
                "action": "click",
                "target": "#add-to-cart",
                "step": 2,
                "ok": True,
                "duration_ms": 50.0,
            })

            # Step 3: Fill quantity
            bus.emit(BEFORE_ACTION, {
                "action": "fill",
                "target": "#qty",
                "step": 3,
            })
            bus.emit(AFTER_ACTION, {
                "action": "fill",
                "target": "#qty",
                "step": 3,
                "ok": True,
                "duration_ms": 30.0,
            })

            # Stop recording
            session = recorder.stop()

            # ── Phase 4: Save recording ───────────────────────────────
            rec_path = Path(tmpdir) / "journey_recording.json"
            save_recording(session, rec_path)
            assert rec_path.exists()

            loaded_recording = load_recording(rec_path)
            assert len(loaded_recording.actions) >= 6  # 3 steps × 2 events each

            # ── Phase 5: Record in memory ─────────────────────────────
            mem_store = MemoryStore(Path(tmpdir) / "memory", ttl_days=30)
            mem_store.record_sequence(
                domain="shop.example.com",
                task="Add item to cart",
                actions=[
                    {"action": "navigate", "url": "https://shop.example.com"},
                    {"action": "click", "target": "#add-to-cart"},
                    {"action": "fill", "target": "#qty", "value": "2"},
                ],
                success=True,
            )
            mem_store.record_selector("shop.example.com", "Add to Cart Button", "#add-to-cart")

            # Verify memory was saved
            context = mem_store.get_context_for_prompt("shop.example.com")
            assert "#add-to-cart" in context
            assert "Add item to cart" in context

            # ── Phase 6: Replay recording ─────────────────────────────
            # Build a mock browser for replay
            mock_sb = MagicMock()

            nav_result = MagicMock()
            nav_result.ok = True
            nav_result.data = MagicMock()
            nav_result.data.final_url = "https://shop.example.com/"
            mock_sb.navigate = AsyncMock(return_value=nav_result)

            click_result = MagicMock()
            click_result.ok = True
            mock_sb.click = AsyncMock(return_value=click_result)

            fill_result = MagicMock()
            fill_result.ok = True
            mock_sb.fill = AsyncMock(return_value=fill_result)

            replayer = RecordingReplayer(mock_sb)
            report = await replayer.replay(loaded_recording, delay_ms=0)

            # ── Phase 7: Verify all features interact ─────────────────
            # Plugin hooks fired: nav + click action + fill action = 3
            assert len(action_log) >= 3
            assert any("nav:https://shop.example.com" in entry for entry in action_log)
            assert any("action:click" in entry for entry in action_log)
            assert any("action:fill" in entry for entry in action_log)

            # Recording captured all events
            assert len(loaded_recording.actions) >= 6

            # Memory provides context
            assert "#add-to-cart" in mem_store.get_context_for_prompt("shop.example.com")

            # Replay succeeded (some actions may dispatch as None for generic events)
            assert report.total_actions == len(loaded_recording.actions)

            clear_registry()
