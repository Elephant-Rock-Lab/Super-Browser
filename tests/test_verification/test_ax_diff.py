"""Tests for AX tree structural diff."""

from super_browser.interaction.types import AXNode, AXSnapshot
from super_browser.verification.ax_diff import diff_ax_trees


def _snap(nodes: dict[str, AXNode]) -> AXSnapshot:
    return AXSnapshot(url="https://example.com", title="Test", nodes=nodes)


class TestDiffAxTrees:
    def test_identical_snapshots(self):
        nodes = {"e0": AXNode(ref="e0", role="button", name="OK")}
        result = diff_ax_trees(_snap(nodes), _snap(nodes))
        assert result.total_interactive_changes == 0
        assert result.nodes_added == 0
        assert result.nodes_removed == 0
        assert result.nodes_changed == 0

    def test_added_interactive_node(self):
        before = _snap({"e0": AXNode(ref="e0", role="button", name="OK")})
        after = _snap({
            "e0": AXNode(ref="e0", role="button", name="OK"),
            "e1": AXNode(ref="e1", role="link", name="Next"),
        })
        result = diff_ax_trees(before, after)
        assert result.nodes_added == 1
        assert "e1" in result.added_refs
        assert result.total_interactive_changes == 1

    def test_removed_interactive_node(self):
        before = _snap({
            "e0": AXNode(ref="e0", role="button", name="OK"),
            "e1": AXNode(ref="e1", role="link", name="Next"),
        })
        after = _snap({"e0": AXNode(ref="e0", role="button", name="OK")})
        result = diff_ax_trees(before, after)
        assert result.nodes_removed == 1
        assert "e1" in result.removed_refs

    def test_changed_node_property(self):
        before = _snap({"e0": AXNode(ref="e0", role="button", name="Submit")})
        after = _snap({"e0": AXNode(ref="e0", role="button", name="Submitted")})
        result = diff_ax_trees(before, after)
        assert result.nodes_changed == 1
        assert "e0" in result.changed_refs

    def test_disabled_change_detected(self):
        before = _snap({"e0": AXNode(ref="e0", role="button", name="OK", disabled=False)})
        after = _snap({"e0": AXNode(ref="e0", role="button", name="OK", disabled=True)})
        result = diff_ax_trees(before, after)
        assert result.nodes_changed == 1

    def test_non_interactive_ignored(self):
        before = _snap({"e0": AXNode(ref="e0", role="heading", name="Title")})
        after = _snap({"e0": AXNode(ref="e0", role="heading", name="New Title")})
        result = diff_ax_trees(before, after)
        assert result.total_interactive_changes == 0

    def test_empty_snapshots(self):
        empty = _snap({})
        result = diff_ax_trees(empty, empty)
        assert result.total_interactive_changes == 0

    def test_change_descriptions_populated(self):
        before = _snap({"e0": AXNode(ref="e0", role="button", name="Go")})
        after = _snap({
            "e0": AXNode(ref="e0", role="button", name="Go", disabled=True),
            "e1": AXNode(ref="e1", role="link", name="New"),
        })
        result = diff_ax_trees(before, after)
        assert len(result.change_descriptions) == 2
        assert any("Added" in d for d in result.change_descriptions)
        assert any("Changed" in d for d in result.change_descriptions)

    def test_focused_change(self):
        before = _snap({"e0": AXNode(ref="e0", role="textbox", name="Email", focused=False)})
        after = _snap({"e0": AXNode(ref="e0", role="textbox", name="Email", focused=True)})
        result = diff_ax_trees(before, after)
        assert result.nodes_changed == 1
