"""
Tests for video lightbox pinch-zoom / drag-pan / double-tap-zoom (message videos).

Companion to the image lightbox zoom (#6444). Verifies via static JS analysis
that the video zoom behavior contract lives in ui.js:
  1. Video media rows render a .msg-media-zoom button carrying the src/name.
  2. The click dispatcher routes .msg-media-zoom -> _openVideoLightbox.
  3. _openVideoLightbox builds an .img-lightbox--video with a <video controls>.
  4. _attachVideoZoom implements the control-band passthrough at 1x so native
     playback controls keep working (the key differentiator from image zoom).
  5. Two-finger pinch, wheel, and double-tap zoom paths exist.

Each assertion is written so that reverting the feature code makes it FAIL
(mutation-checkable), not merely asserting a generic substring.
"""
from __future__ import annotations

import pathlib
import re
import unittest

REPO_ROOT = pathlib.Path(__file__).parent.parent
UI_JS = (REPO_ROOT / "static" / "ui.js").read_text(encoding="utf-8")
CSS = (REPO_ROOT / "static" / "style.css").read_text(encoding="utf-8")


class TestVideoZoomButtonRender(unittest.TestCase):
    def test_video_media_row_renders_zoom_button(self):
        # The zoom affordance must be emitted ONLY for video (not audio).
        self.assertIn("msg-media-zoom", UI_JS)
        self.assertRegex(
            UI_JS,
            r"kind===?'video'\s*\n?\s*\?\s*`<button[^`]*msg-media-zoom",
            "zoom button must be gated on kind==='video'",
        )

    def test_zoom_button_carries_src_and_name(self):
        m = re.search(r"msg-media-zoom[^`]*?data-media-src=\"\$\{safeSrc\}\"", UI_JS)
        self.assertIsNotNone(m, "zoom button must carry data-media-src")
        self.assertIn('data-media-name="${safeName}"', UI_JS)


class TestVideoLightboxDispatch(unittest.TestCase):
    def test_click_dispatcher_routes_zoom_button(self):
        # The global click handler must map .msg-media-zoom to _openVideoLightbox.
        self.assertRegex(
            UI_JS,
            r"closest\('\.msg-media-zoom'\)",
            "click handler must detect the zoom button",
        )
        self.assertRegex(
            UI_JS,
            r"_openVideoLightbox\(\s*src\s*,\s*name\s*\)",
            "zoom button click must call _openVideoLightbox(src, name)",
        )

    def test_open_video_lightbox_builds_video_element(self):
        self.assertIn("function _openVideoLightbox(", UI_JS)
        block = UI_JS.split("function _openVideoLightbox(", 1)[1].split("\nfunction ", 1)[0]
        self.assertIn("img-lightbox--video", block)
        self.assertIn("createElement('video')", block)
        self.assertIn("video.controls = true", block)
        self.assertIn("_attachVideoZoom(lb, video)", block)


class TestVideoZoomControlBandPassthrough(unittest.TestCase):
    """The core differentiator: native controls must keep working at 1x."""

    def _fn(self) -> str:
        self.assertIn("function _attachVideoZoom(", UI_JS)
        return UI_JS.split("function _attachVideoZoom(", 1)[1].split("\nfunction ", 1)[0]

    def test_control_band_passthrough_at_1x(self):
        fn = self._fn()
        # A control band constant and an inControlBand() check must exist, and a
        # single-finger touch at scale<=1.01 inside the band must early-return
        # (leaving the event to native controls). Reverting this passthrough
        # (removing the early return) fails this assertion.
        self.assertIn("CONTROL_BAND", fn)
        self.assertRegex(fn, r"inControlBand\s*=\s*\(")
        self.assertRegex(
            fn,
            r"st\.scale\s*<=\s*1\.01\s*&&\s*inControlBand\([^)]*\)\)\s*return",
            "at 1x inside the control band, touchstart must return so native "
            "controls receive the gesture",
        )

    def test_pan_only_when_zoomed(self):
        fn = self._fn()
        # Single-finger pan must be gated on already-zoomed state.
        self.assertRegex(fn, r"if\(st\.scale\s*>\s*1\.01\)\{\s*\n?\s*e\.stopPropagation")

    def test_mousedown_yields_to_controls_at_1x(self):
        fn = self._fn()
        # Desktop: at 1x mousedown returns early (native controls own clicks).
        self.assertRegex(fn, r"mousedown[^;]*\n?\s*if\(st\.scale\s*<=\s*1\.01\)\s*return")


class TestVideoZoomGestures(unittest.TestCase):
    def _fn(self) -> str:
        return UI_JS.split("function _attachVideoZoom(", 1)[1].split("\nfunction ", 1)[0]

    def test_pinch_zoom_path(self):
        fn = self._fn()
        self.assertRegex(fn, r"e\.touches\.length\s*===?\s*2")
        self.assertIn("pinchStartDist", fn)

    def test_wheel_zoom_path(self):
        fn = self._fn()
        self.assertRegex(fn, r"addEventListener\('wheel'")
        self.assertIn("zoomAt(e.clientX, e.clientY", fn)

    def test_double_tap_toggles_zoom(self):
        fn = self._fn()
        self.assertRegex(fn, r"st\.scale\s*>\s*1\.01\s*\?\s*1\s*:\s*2\.5")


class TestVideoLightboxCss(unittest.TestCase):
    def test_video_lightbox_css_present(self):
        self.assertIn(".img-lightbox-video", CSS)
        self.assertIn(".msg-media-zoom", CSS)
        # zoomed video must drop the transition for responsive panning.
        self.assertRegex(CSS, r"\.img-lightbox--zoomed\s+\.img-lightbox-video\{transition:none")


if __name__ == "__main__":
    unittest.main()
