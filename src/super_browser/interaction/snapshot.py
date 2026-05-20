"""Snapshot provider — AX tree capture via CDP Accessibility.getFullAXTree."""

from __future__ import annotations

import json
import logging
from typing import Any

from super_browser.interaction.types import AXNode, AXSnapshot

logger = logging.getLogger(__name__)

_INTERACTIVE_ROLES = frozenset({
    "button", "link", "textbox", "combobox", "checkbox",
    "radio", "menuitem", "tab", "slider", "searchbox",
    "spinbutton", "switch", "option", "treeitem",
})


class SnapshotProvider:

    def __init__(self, cdp: Any, stealth_bridge: Any = None) -> None:
        self._cdp = cdp
        self._stealth_bridge = stealth_bridge

    async def capture_ax_only(self, url: str, title: str) -> AXSnapshot:
        if self._stealth_bridge is not None:
            raw_data = await self._stealth_bridge.get_ax_tree()
            class _FakeResult:
                ok = True
                data = raw_data
            result = _FakeResult()
        else:
            result = await self._cdp.send("Accessibility.getFullAXTree", {})
        nodes: dict[str, AXNode] = {}

        if result.ok and result.data:
            raw_nodes = result.data.get("nodes", [])
            idx = 0
            for raw in raw_nodes:
                role = (raw.get("role", {}) or {}).get("value", "").lower()
                if role not in _INTERACTIVE_ROLES:
                    continue

                name = _extract_name(raw)
                node_url = _extract_property(raw, "url")
                value = (raw.get("value", {}) or {}).get("value")
                description = _extract_property(raw, "description")
                bounds = _extract_bounds(raw)
                focused = _extract_property(raw, "focused") == "true"
                disabled = _extract_property(raw, "disabled") == "true"

                ref = f"e{idx}"
                nodes[ref] = AXNode(
                    ref=f"@{ref}",
                    role=role,
                    name=name,
                    url=node_url,
                    value=value,
                    description=description,
                    bounds=bounds,
                    focused=focused,
                    disabled=disabled,
                )
                idx += 1

        token_count = len(nodes) * 10
        return AXSnapshot(url=url, title=title, nodes=nodes, token_count=token_count)

    async def capture_hybrid(self, url: str, title: str) -> AXSnapshot:
        ax_snap = await self.capture_ax_only(url, title)

        expr = (
            '(function(){ var els = document.querySelectorAll("input, button, a, select, textarea, [role]"); '
            'var result = []; for (var i = 0; i < els.length; i++) { '
            'var el = els[i]; var rect = el.getBoundingClientRect(); '
            'result.push({name: el.getAttribute("aria-label") || el.textContent.trim().substring(0, 50) || "", '
            'role: el.getAttribute("role") || el.tagName.toLowerCase(), '
            'x: rect.x, y: rect.y, w: rect.width, h: rect.height}); } '
            'return JSON.stringify(result); })()'
        )
        dom_result = await (self._stealth_bridge.cdp_send("Runtime.evaluate", {"expression": expr}) if self._stealth_bridge else self._cdp.send("Runtime.evaluate", {"expression": expr}))

        if dom_result.ok and dom_result.data:
            val = dom_result.data.get("result", {}).get("value")
            if val:
                try:
                    dom_elements = json.loads(val)
                    idx = len(ax_snap.nodes)
                    for elem in dom_elements:
                        name = elem.get("name", "")
                        role = elem.get("role", "")
                        ref = f"e{idx}"
                        if not any(
                            n.name == name and n.role == role
                            for n in ax_snap.nodes.values()
                        ):
                            ax_snap.nodes[ref] = AXNode(
                                ref=f"@{ref}",
                                role=role,
                                name=name,
                                bounds=(elem["x"], elem["y"], elem["w"], elem["h"]),
                            )
                            idx += 1
                except (json.JSONDecodeError, KeyError):
                    pass

        return ax_snap


def _extract_name(raw: dict) -> str:
    name_obj = raw.get("name", {})
    if isinstance(name_obj, dict):
        return name_obj.get("value", "")
    return str(name_obj) if name_obj else ""


def _extract_property(raw: dict, prop_name: str) -> Any:
    for p in raw.get("properties", []):
        if p.get("name") == prop_name:
            val = p.get("value", {})
            if isinstance(val, dict):
                return val.get("value")
            return val
    return None


def _extract_bounds(raw: dict) -> tuple[float, float, float, float] | None:
    for p in raw.get("properties", []):
        if p.get("name") == "bounds":
            val = p.get("value", {})
            if isinstance(val, dict):
                entries = val.get("value", [])
                bounds_map = {}
                for entry in entries:
                    if isinstance(entry, dict):
                        v = entry.get("value", {})
                        if isinstance(v, dict):
                            bounds_map[entry.get("name")] = v.get("value", 0)
                if bounds_map:
                    return (
                        float(bounds_map.get("x", 0)),
                        float(bounds_map.get("y", 0)),
                        float(bounds_map.get("width", 0)),
                        float(bounds_map.get("height", 0)),
                    )
    return None
