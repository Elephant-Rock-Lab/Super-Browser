"""CheckpointManager — browser-state persistence for recovery.

Persists page URL, scroll position, form values, and cookies to JSON files
under ``~/.config/super-browser/checkpoints/{session_id}/``.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from super_browser.recovery.types import Checkpoint

logger = logging.getLogger(__name__)

# Default base directory for all checkpoint storage
_DEFAULT_BASE_DIR = Path.home() / ".config" / "super-browser" / "checkpoints"


class CheckpointManager:
    """Save and restore browser page state (URL, scroll, forms, cookies).

    Each checkpoint is a JSON file containing enough information to
    restore a page to its previous state after a failure.
    """

    def __init__(
        self,
        workspace: Path,
        checkpoint_dir: Optional[Path] = None,
        *,
        session_id: str = "default",
        cdp: Optional[Any] = None,
        page: Optional[Any] = None,
    ) -> None:
        self._workspace = workspace
        self._session_id = session_id
        self._cdp = cdp
        self._page = page
        if checkpoint_dir is not None:
            self._checkpoint_dir = checkpoint_dir
        else:
            self._checkpoint_dir = _DEFAULT_BASE_DIR / session_id

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Ensure checkpoint directory exists."""
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("CheckpointManager initialized at %s", self._checkpoint_dir)

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    async def save(self, label: str = "") -> Checkpoint:
        """Capture current page state and persist to JSON.

        Serializes: page URL, scroll position, form input values, cookies.
        """
        state: dict[str, Any] = {
            "checkpoint_id": uuid.uuid4().hex[:12],
            "label": label,
            "timestamp": time.time(),
        }

        # --- URL ---
        if self._page is not None:
            try:
                state["url"] = getattr(self._page, "url", "")
            except Exception:
                state["url"] = ""

        # --- Scroll position ---
        state["scroll_x"] = 0
        state["scroll_y"] = 0
        if self._cdp is not None:
            try:
                scroll_result = await self._cdp.evaluate(
                    'JSON.stringify({x: window.scrollX, y: window.scrollY})'
                )
                if scroll_result.ok and scroll_result.data:
                    val = scroll_result.data.get("result", {}).get("value")
                    if val:
                        scroll_data = json.loads(val)
                        state["scroll_x"] = scroll_data.get("x", 0)
                        state["scroll_y"] = scroll_data.get("y", 0)
            except Exception:
                pass

        # --- Form values ---
        state["form_values"] = {}
        if self._cdp is not None:
            try:
                form_result = await self._cdp.evaluate(
                    '(function() {'
                    '  var inputs = document.querySelectorAll("input, textarea, select");'
                    '  var values = {};'
                    '  for (var i = 0; i < inputs.length; i++) {'
                    '    var el = inputs[i];'
                    '    var key = el.id || el.name || ("__idx_" + i);'
                    '    if (el.type === "checkbox" || el.type === "radio") {'
                    '      values[key] = el.checked;'
                    '    } else {'
                    '      values[key] = el.value;'
                    '    }'
                    '  }'
                    '  return JSON.stringify(values);'
                    '})()'
                )
                if form_result.ok and form_result.data:
                    val = form_result.data.get("result", {}).get("value")
                    if val:
                        state["form_values"] = json.loads(val)
            except Exception:
                pass

        # --- Cookies ---
        state["cookies"] = []
        if self._cdp is not None:
            try:
                cookie_result = await self._cdp.send("Network.getAllCookies", {})
                if cookie_result.ok and cookie_result.data:
                    state["cookies"] = cookie_result.data.get("cookies", [])
            except Exception:
                pass

        # --- Persist ---
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_id = state["checkpoint_id"]
        file_path = self._checkpoint_dir / f"{checkpoint_id}.json"
        file_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            message=label,
            created_at=state["timestamp"],
            file_count=1,
            commit_hash="",
        )
        logger.info("Checkpoint saved: %s (%s)", checkpoint_id, label)
        return checkpoint

    # ------------------------------------------------------------------
    # Restore
    # ------------------------------------------------------------------

    async def restore(self, checkpoint_id: str) -> bool:
        """Restore page to a previously saved checkpoint state.

        Navigates to URL, restores scroll position, and refills form values.
        """
        file_path = self._checkpoint_dir / f"{checkpoint_id}.json"
        if not file_path.exists():
            logger.warning("Checkpoint not found: %s", checkpoint_id)
            return False

        state = json.loads(file_path.read_text(encoding="utf-8"))

        # --- Navigate to URL ---
        url = state.get("url", "")
        if url and self._page is not None:
            try:
                await self._page.goto(url)
            except Exception as exc:
                logger.error("Failed to navigate to %s: %s", url, exc)
                return False

        # --- Restore cookies ---
        cookies = state.get("cookies", [])
        if cookies and self._cdp is not None:
            try:
                await self._cdp.send("Network.setCookies", {"cookies": cookies})
            except Exception:
                pass

        # --- Restore form values ---
        form_values = state.get("form_values", {})
        if form_values and self._cdp is not None:
            try:
                # HB-17-04: Use Runtime.callFunctionOn with argument passing
                # to avoid JS injection from form values via string concatenation.
                import json as _json
                # CDP Runtime.evaluate with the values as a proper JS argument
                result = await self._cdp.send("Runtime.evaluate", {
                    "expression": "(function(values) {"
                        "var inputs = document.querySelectorAll('input, textarea, select');"
                        "for (var i = 0; i < inputs.length; i++) {"
                        "  var el = inputs[i];"
                        "  var key = el.id || el.name || ('__idx_' + i);"
                        "  if (key in values) {"
                        "    if (el.type === 'checkbox' || el.type === 'radio') {"
                        "      el.checked = values[key];"
                        "    } else {"
                        "      el.value = values[key];"
                        "    }"
                        "  }"
                        "}})(JSON.parse(arguments[0]))",
                    "args": [_json.dumps(form_values)],
                    "returnByValue": True,
                })
            except Exception:
                # Fallback: if Runtime.evaluate with args doesn't work,
                # use CDP Runtime.callFunctionOn on the page context
                try:
                    # Get page execution context
                    ctx_result = await self._cdp.send("Runtime.evaluate", {
                        "expression": "this",
                        "returnByValue": False,
                    })
                    obj_id = ctx_result.get("result", {}).get("objectId")
                    if obj_id:
                        await self._cdp.send("Runtime.callFunctionOn", {
                            "functionDeclaration": "function(valuesJson) {"
                                "var values = JSON.parse(valuesJson);"
                                "var inputs = document.querySelectorAll('input, textarea, select');"
                                "for (var i = 0; i < inputs.length; i++) {"
                                "  var el = inputs[i];"
                                "  var key = el.id || el.name || ('__idx_' + i);"
                                "  if (key in values) {"
                                "    if (el.type === 'checkbox' || el.type === 'radio') {"
                                "      el.checked = values[key];"
                                "    } else {"
                                "      el.value = values[key];"
                                "    }"
                                "  }"
                                "}}",
                            "objectId": obj_id,
                            "arguments": [{"value": _json.dumps(form_values) }],
                            "returnByValue": True,
                        })
                except Exception:
                    pass

        # --- Restore scroll position ---
        scroll_x = state.get("scroll_x", 0)
        scroll_y = state.get("scroll_y", 0)
        if (scroll_x or scroll_y) and self._cdp is not None:
            try:
                await self._cdp.evaluate(
                    f'window.scrollTo({scroll_x}, {scroll_y})'
                )
            except Exception:
                pass

        logger.info("Checkpoint restored: %s", checkpoint_id)
        return True

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    def list_checkpoints(self, limit: int = 20) -> list[Checkpoint]:
        """Return metadata for saved checkpoints, newest first."""
        if not self._checkpoint_dir.exists():
            return []

        checkpoints: list[Checkpoint] = []
        files = sorted(
            self._checkpoint_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        for fp in files[:limit]:
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
                checkpoints.append(Checkpoint(
                    checkpoint_id=data.get("checkpoint_id", fp.stem),
                    message=data.get("label", ""),
                    created_at=data.get("timestamp", 0),
                    file_count=1,
                    commit_hash="",
                ))
            except Exception:
                logger.warning("Corrupt checkpoint file: %s", fp)

        return checkpoints

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete(self, checkpoint_id: str) -> bool:
        """Remove a checkpoint file by ID."""
        file_path = self._checkpoint_dir / f"{checkpoint_id}.json"
        if not file_path.exists():
            return False
        file_path.unlink()
        logger.info("Checkpoint deleted: %s", checkpoint_id)
        return True

    # ------------------------------------------------------------------
    # Backward-compatible aliases (legacy API)
    # ------------------------------------------------------------------

    async def create_checkpoint(self, message: str) -> Checkpoint:
        """Alias for save() — backward compatibility."""
        return await self.save(label=message)

    async def rollback(self, checkpoint_id: str) -> bool:
        """Alias for restore() — backward compatibility."""
        return await self.restore(checkpoint_id)
