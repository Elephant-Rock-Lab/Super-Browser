# P7: Vision Bridge — Design Note

> **Status:** Proposed. Solution A (screenshot output controls) is the first
> implementation PR in this workstream.

## Problem

Super-Browser's inspect tier reads the DOM/AX tree — correct and complete for
text-bearing pages, but blind to content encoded in images (flyer sites,
PDF-style catalogs, image-only dashboards, captchas). Three concrete gaps:

### Gap 1 — Screenshots are write-only when oversized

The `screenshot` tool returned raw lossless PNG with no output controls. A
viewport shot is typically ~700 KiB; most MCP hosts inline images only up to
~200 KiB, so the image is "successfully" returned to a path the model never
sees.

**Status:** Addressed by P7.A (screenshot output controls — `format`/`quality`).

### Gap 2 — Inspect tools cannot read image content

- `observe` / `SnapshotProvider` filter to interactive ARIA roles (excludes
  `img`); `extract_text` uses `textContent` or the AX tree. Neither pulls
  `alt`, neither does OCR.

### Gap 3 — Existing vision code is unreachable from MCP

A complete OCR/vision subsystem exists in `src/super_browser/vision/`:

- `ocr.py` — `OCRGrounding` (pytesseract + PIL, word boxes with confidence).
- `providers.py` — `AnthropicCUAProvider`, `OpenAIResponseProvider`,
  `UITARSProvider`.
- `controller.py` — `VisionController` (cascade, cache, OCR fallback,
  `solve_captcha`, `infer_state`).

But it is gated behind `enable_vision=False` (`config.py:157`), used only for
interaction-time element location (`controller.py:770-771`), and unreachable
from any MCP read tool. Dependencies (`pytesseract`, `opencv`,
`transformers`) are not declared in `pyproject.toml`.

## Solutions (priority order)

### P7.A — Screenshot output controls (format + quality) ✓ implemented

Add `format` (`"png" | "jpeg"`) and `quality` (1-100, jpeg-only) to the
`screenshot` tool. Default unchanged (lossless PNG). Requesting
`format="jpeg"` with `quality=70` drops a ~700 KiB PNG to ~80 KiB, under
typical inline limits.

Resize (`max_width`/`max_height`) deferred — needs Pillow, which is currently
`[patchright]`-optional; first PR avoids dependency churn.

**Backend coverage:**
- Patchright/Playwright: native `type="jpeg"`, `quality=N` — passthrough.
- CDP: `Page.captureScreenshot` supports `format`/`quality`; backend was
  hardcoding `format="png"` — now forwards kwargs.
- Selenium: PNG-only; re-encodes via Pillow if available (lazy import), else
  returns PNG with honest `image/png` mime in the sidecar.

**Validation:**
- `quality` rejected when `format="png"`.
- `quality` validated 1-100.
- `format` validated to png/jpeg enum.
- Invalid args fail before any browser call.

### P7.D — Image/alt visibility in observe/extract_text (next)

Surface image `alt` text and `aria-label` without promoting non-interactive
images to actionable targets. Images appear in a separate `images` array on
the `observe` result, not in `targets` — `targets` means action-ready.

Non-interactive images must NOT become action targets.

Potential shape:

```json
{
  "images": [
    {
      "ref": "@e4",
      "role": "image",
      "name": "Milk offer",
      "alt": "Milk offer",
      "bounds": {"x": 10, "y": 20, "width": 300, "height": 200}
    }
  ],
  "images_truncated": false
}
```

### P7.B — `extract_image_text` OCR inspect tool (after D)

Wrap the existing `OCRGrounding.extract_words()` as an inspect-tier MCP tool.
Input: optional selector or bounding box (defaults to viewport). Output:
aggregated `text` + structured `words` (`{text, x, y, w, h, confidence}`).

Declare `pytesseract` + `Pillow` under a `[vision]` extra; load `ara` language
pack for Arabic flyer support. Graceful degradation when tesseract binary /
language pack absent (structured "OCR unavailable" error, not a crash).

Tool name: `extract_image_text` (describes agent intent better than `ocr`).

Suggested output:

```json
{
  "text": "Milk 2 for 10 ...",
  "words": [
    {"text": "Milk", "x": 120, "y": 340, "w": 48, "h": 18, "confidence": 0.91}
  ],
  "language": "eng+ara"
}
```

### P7.C — `analyze_image` vision-LLM tool (deferred)

Wrap `VisionController` as an inspect-tier tool for layout-level reasoning.
Deferred until a concrete task proves OCR insufficient. Once P7.A works, a
multimodal host can inspect resized screenshots directly, making C largely
redundant.
