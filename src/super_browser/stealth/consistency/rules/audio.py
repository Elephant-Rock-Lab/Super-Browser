"""Audio + behavior + extras rules — R-015..R-023."""

from __future__ import annotations

from super_browser.stealth.consistency.rule import Rule, define_rule

__all__ = ["AUDIO_RULES"]

# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

R015: Rule[int] = define_rule(
    id="R-015",
    description="AudioContext.sampleRate — passthrough",
    inputs=("audio.context_sample_rate",),
    output="audio_context_sample_rate",
    derive=lambda ins, _prng: ins[0],
)

R016: Rule[float] = define_rule(
    id="R-016",
    description="AudioContext audioWorklet latency — passthrough",
    inputs=("audio.audio_worklet_latency",),
    output="audio_worklet_latency",
    derive=lambda ins, _prng: float(ins[0]),
)

R016b: Rule[int] = define_rule(
    id="R-016b",
    description="AudioContext destination maxChannelCount — passthrough",
    inputs=("audio.destination_max_channel_count",),
    output="audio_destination_max_channel_count",
    derive=lambda ins, _prng: ins[0],
)

AUDIO_RULES: list[Rule] = [R015, R016, R016b]
