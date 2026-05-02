"""AX tree structural diff — compare two AX snapshots for interactive node changes."""

from __future__ import annotations

from super_browser.interaction.types import AXNode, AXSnapshot, _INTERACTIVE_ROLES
from super_browser.verification.types import AXDiffResult


def diff_ax_trees(before: AXSnapshot, after: AXSnapshot) -> AXDiffResult:
    before_keys = set(before.nodes.keys())
    after_keys = set(after.nodes.keys())

    added_refs: list[str] = []
    removed_refs: list[str] = []
    changed_refs: list[str] = []
    descriptions: list[str] = []

    for ref in sorted(after_keys - before_keys):
        node = after.nodes[ref]
        if node.role in _INTERACTIVE_ROLES:
            added_refs.append(ref)
            descriptions.append(f"Added {node.role} '{node.name}' [{ref}]")

    for ref in sorted(before_keys - after_keys):
        node = before.nodes[ref]
        if node.role in _INTERACTIVE_ROLES:
            removed_refs.append(ref)
            descriptions.append(f"Removed {node.role} '{node.name}' [{ref}]")

    for ref in sorted(before_keys & after_keys):
        b = before.nodes[ref]
        a = after.nodes[ref]
        if a.role not in _INTERACTIVE_ROLES:
            continue
        changes = _compare_node_props(b, a)
        if changes:
            changed_refs.append(ref)
            descriptions.append(f"Changed {a.role} '{a.name}' [{ref}]: {', '.join(changes)}")

    return AXDiffResult(
        nodes_added=len(added_refs),
        nodes_removed=len(removed_refs),
        nodes_changed=len(changed_refs),
        added_refs=tuple(added_refs),
        removed_refs=tuple(removed_refs),
        changed_refs=tuple(changed_refs),
        change_descriptions=tuple(descriptions),
    )


def _compare_node_props(before: AXNode, after: AXNode) -> list[str]:
    changes: list[str] = []
    if before.role != after.role:
        changes.append(f"role: {before.role} -> {after.role}")
    if before.name != after.name:
        changes.append(f"name: '{before.name}' -> '{after.name}'")
    if before.value != after.value:
        changes.append(f"value: '{before.value}' -> '{after.value}'")
    if before.url != after.url:
        changes.append("url changed")
    if before.focused != after.focused:
        changes.append(f"focused: {before.focused} -> {after.focused}")
    if before.disabled != after.disabled:
        changes.append(f"disabled: {before.disabled} -> {after.disabled}")
    return changes
