"""Device profile schema — frozen dataclasses for browser fingerprint profiles."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrowserInfo:
    """Browser identity and version range."""

    name: str
    channel: str
    min_version: str
    max_version: str
    user_agent: str


@dataclass(frozen=True)
class OSInfo:
    """Operating system details."""

    name: str
    version: str
    arch: str
    platform_version: str = ""


@dataclass(frozen=True)
class DeviceInfo:
    """Physical device / hardware characteristics."""

    vendor: str
    model: str
    cpu_family: str
    cores: int
    memory_gb: int


@dataclass(frozen=True)
class DisplayInfo:
    """Screen / viewport properties."""

    width: int
    height: int
    dpr: int
    color_depth: int
    pixel_depth: int


@dataclass(frozen=True)
class GPUInfo:
    """GPU / WebGL fingerprint data."""

    vendor: str
    renderer: str
    webgl_unmasked_vendor: str
    webgl_unmasked_renderer: str
    webgl_max_texture_size: int
    webgl_max_color_attachments: int
    webgl_extensions: tuple[str, ...] = ()


@dataclass(frozen=True)
class AudioInfo:
    """AudioContext fingerprint parameters."""

    context_sample_rate: int
    audio_worklet_latency: float
    destination_max_channel_count: int


@dataclass(frozen=True)
class FontInfo:
    """Installed font fingerprint."""

    family: str
    list: tuple[str, ...] = ()


@dataclass(frozen=True)
class BehaviorInfo:
    """Humanised interaction parameters."""

    hand: str
    tremor: float
    wpm: int
    scroll_style: str


@dataclass(frozen=True)
class EntropyBudget:
    """Allowed entropy variance per profile."""

    fixed: tuple[str, ...] = ()
    per_seed: tuple[str, ...] = ()


@dataclass(frozen=True)
class DeviceProfile:
    """Complete device fingerprint profile."""

    id: str
    version: str
    engine: str
    browser: BrowserInfo
    os: OSInfo
    device: DeviceInfo
    display: DisplayInfo
    gpu: GPUInfo
    audio: AudioInfo
    fonts: FontInfo
    behavior: BehaviorInfo
    entropy_budget: EntropyBudget
    timezone: str
    locale: str
    languages: tuple[str, ...] = ()

    def validate(self) -> None:
        """Check that all required fields are non-empty / non-zero.

        Raises ValueError on the first invalid field found.
        """
        if not self.id:
            raise ValueError("DeviceProfile.id must be non-empty")
        if not self.version:
            raise ValueError("DeviceProfile.version must be non-empty")
        if not self.engine:
            raise ValueError("DeviceProfile.engine must be non-empty")
        if not self.browser.name:
            raise ValueError("BrowserInfo.name must be non-empty")
        if not self.browser.user_agent:
            raise ValueError("BrowserInfo.user_agent must be non-empty")
        if not self.os.name:
            raise ValueError("OSInfo.name must be non-empty")
        if not self.os.version:
            raise ValueError("OSInfo.version must be non-empty")
        if not self.os.arch:
            raise ValueError("OSInfo.arch must be non-empty")
        if not self.device.vendor:
            raise ValueError("DeviceInfo.vendor must be non-empty")
        if self.device.cores <= 0:
            raise ValueError("DeviceInfo.cores must be positive")
        if self.device.memory_gb <= 0:
            raise ValueError("DeviceInfo.memory_gb must be positive")
        if self.display.width <= 0:
            raise ValueError("DisplayInfo.width must be positive")
        if self.display.height <= 0:
            raise ValueError("DisplayInfo.height must be positive")
        if not self.gpu.vendor:
            raise ValueError("GPUInfo.vendor must be non-empty")
        if not self.gpu.renderer:
            raise ValueError("GPUInfo.renderer must be non-empty")
        if self.audio.context_sample_rate <= 0:
            raise ValueError("AudioInfo.context_sample_rate must be positive")
        if not self.fonts.family:
            raise ValueError("FontInfo.family must be non-empty")
        if not self.behavior.hand:
            raise ValueError("BehaviorInfo.hand must be non-empty")
        if self.behavior.wpm <= 0:
            raise ValueError("BehaviorInfo.wpm must be positive")
        if not self.timezone:
            raise ValueError("DeviceProfile.timezone must be non-empty")
        if not self.locale:
            raise ValueError("DeviceProfile.locale must be non-empty")
