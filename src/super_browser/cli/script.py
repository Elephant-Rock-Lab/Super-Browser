"""Script execution, recording replay, and one-shot agent commands.

Provides:
  - ``run_script(path)`` — execute a YAML batch script
  - ``run_replay(path)`` — replay a recording JSON file
  - ``run_act(instruction)`` — one-shot agent execution

HB-24-02: Script mode reports progress per step.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from super_browser import SuperBrowser
from super_browser.results import ActionResult

# ---------------------------------------------------------------------------
# YAML script execution
# ---------------------------------------------------------------------------


def _load_yaml_steps(path: str) -> dict[str, Any]:
    """Load a YAML script file and return the parsed dict.

    Tries ``yaml`` (PyYAML) first, then falls back to a simple JSON-based
    parser for YAML files that are also valid JSON.
    """
    raw = Path(path).read_text(encoding="utf-8")

    try:
        import yaml
        data = yaml.safe_load(raw)
    except ImportError:
        # Fallback: try JSON parse (works for simple YAML that is valid JSON)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            raise ImportError(
                "PyYAML is required for YAML script execution. "
                "Install with: pip install pyyaml"
            )

    if not isinstance(data, dict) or "steps" not in data:
        raise ValueError(f"Invalid script file (missing 'steps'): {path}")

    return data


async def _execute_step(sb: SuperBrowser, step: dict[str, Any]) -> ActionResult:
    """Execute a single script step against the browser."""
    action = step.get("action", "")
    result: ActionResult

    if action == "navigate":
        url = step.get("url", "")
        result = await sb.navigate(url)
    elif action == "click":
        selector = step.get("selector", "")
        result = await sb.click(selector)
    elif action == "fill":
        selector = step.get("selector", "")
        value = step.get("value", "")
        result = await sb.fill(selector, value)
    elif action == "extract":
        query = step.get("selector", step.get("query", "page content"))
        selector = step.get("selector")
        result = await sb.extract(query, selector=selector)
    elif action == "observe":
        result = await sb.observe()
    elif action == "screenshot":
        path = step.get("path")
        if sb._page:
            try:
                result_bytes = await sb._page.screenshot(full_page=False)
                if path:
                    Path(path).write_bytes(result_bytes)
                result = ActionResult(ok=True, data={"bytes": len(result_bytes), "path": path})
            except Exception as exc:
                result = ActionResult(ok=False, error=exc)
        else:
            result = ActionResult(ok=False, error=RuntimeError("Browser not started"))
    elif action == "scroll":
        direction = step.get("direction", "down")
        amounts = {"up": "(0, -500)", "down": "(0, 500)", "left": "(-500, 0)", "right": "(500, 0)"}
        amount = amounts.get(direction, "(0, 500)")
        if sb._page:
            await sb._page.evaluate(f"window.scrollBy{amount}")
            result = ActionResult(ok=True, data={"scrolled": direction})
        else:
            result = ActionResult(ok=False, error=RuntimeError("Browser not started"))
    else:
        result = ActionResult(ok=False, error=ValueError(f"Unknown action: {action}"))

    return result


async def run_script(path: str, *, output_path: str | None = None) -> list[dict[str, Any]]:
    """Execute a YAML script file step by step.

    HB-24-02: Reports progress per step.

    :param path: Path to the YAML script file.
    :param output_path: Optional path to write results JSON.
    :returns: List of step result dicts.
    """
    from super_browser.testing import MockLLMClient

    data = _load_yaml_steps(path)
    steps = data["steps"]
    stop_on_error = data.get("stop_on_error", True)
    results: list[dict[str, Any]] = []

    sb = SuperBrowser(llm_client=MockLLMClient())
    await sb.start()

    try:
        for i, step in enumerate(steps, 1):
            total = len(steps)
            action = step.get("action", "?")
            print(f"Step {i}/{total}: {action} ... ", end="", flush=True)

            try:
                result = await _execute_step(sb, step)
                status = "OK" if result.ok else "FAIL"
                print(status)

                step_result: dict[str, Any] = {
                    "step": i,
                    "action": action,
                    "ok": result.ok,
                }
                if result.data is not None:
                    if hasattr(result.data, "to_dict"):
                        step_result["data"] = result.data.to_dict()
                    elif isinstance(result.data, dict):
                        step_result["data"] = result.data
                    else:
                        step_result["data"] = str(result.data)
                if result.error is not None:
                    step_result["error"] = str(result.error)

                results.append(step_result)

                if not result.ok and stop_on_error:
                    print(f"  Error: {result.error}")
                    print("  Stopping (stop_on_error=true)")
                    break
            except Exception as exc:
                print(f"ERROR: {exc}")
                results.append({"step": i, "action": action, "ok": False, "error": str(exc)})
                if stop_on_error:
                    break
    finally:
        await sb.stop()

    if output_path:
        Path(output_path).write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
        print(f"\nResults written to {output_path}")

    return results


# ---------------------------------------------------------------------------
# Recording replay
# ---------------------------------------------------------------------------


async def run_replay(path: str, *, delay_ms: float = 100) -> dict[str, Any]:
    """Replay a recording JSON file.

    :param path: Path to the recording JSON file.
    :param delay_ms: Delay between actions in milliseconds.
    :returns: Replay report dict.
    """
    from super_browser.testing import MockLLMClient

    sb = SuperBrowser(llm_client=MockLLMClient())
    await sb.start()

    try:
        result = await sb.replay(path, delay_ms=delay_ms)

        if result.ok and result.data is not None:
            report = result.data
            if hasattr(report, "to_dict"):
                report_dict = report.to_dict()
            elif isinstance(report, dict):
                report_dict = report
            else:
                report_dict = {"raw": str(report)}

            print(f"Replay complete: {report_dict.get('total_actions', '?')} actions")
            print(f"  Matched: {report_dict.get('matched', '?')}")
            print(f"  Mismatches: {len(report_dict.get('mismatches', []))}")
            print(f"  Duration: {report_dict.get('duration_ms', 0):.0f}ms")
            return report_dict
        else:
            error = getattr(result, "error", None) or "Unknown error"
            print(f"Replay failed: {error}")
            return {"ok": False, "error": str(error)}
    finally:
        await sb.stop()


# ---------------------------------------------------------------------------
# One-shot agent
# ---------------------------------------------------------------------------


async def run_act(
    instruction: str,
    *,
    url: str | None = None,
    max_steps: int = 50,
) -> ActionResult:
    """Run a one-shot agent instruction.

    Requires a valid LLM provider to be configured via environment variables.

    :param instruction: Natural language instruction.
    :param url: Optional URL to navigate to before executing.
    :param max_steps: Maximum agent steps.
    :returns: ActionResult from the agent.
    """
    from super_browser import create_llm

    try:
        llm_client = create_llm()
    except Exception as exc:
        print(f"Error: Could not create LLM client: {exc}")
        print("Set LLM credentials via environment variables (e.g., OPENAI_API_KEY, ANTHROPIC_API_KEY)")
        return ActionResult(ok=False, error=exc)

    sb = SuperBrowser(llm_client=llm_client)
    await sb.start()

    try:
        if url:
            print(f"Navigating to {url}...")
            nav = await sb.navigate(url)
            if not nav.ok:
                print(f"Navigation failed: {nav.error}")
                return nav

        print(f"Executing: {instruction}")
        result = await sb.act(instruction, max_steps=max_steps)

        if result.ok:
            print("✓ Task completed successfully")
            if result.data is not None:
                data = result.data
                if hasattr(data, "to_dict"):
                    print(json.dumps(data.to_dict(), indent=2, default=str))
                elif isinstance(data, dict):
                    print(json.dumps(data, indent=2, default=str))
        else:
            print("✗ Task failed")
            if result.error:
                print(f"  Error: {result.error}")

        return result
    finally:
        await sb.stop()
