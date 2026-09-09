# Changelog

## 0.2.0

- Add a one-second startup count-up with synchronized quota bars.
- Stream complete frames through SwiftBar, with one-minute polling and manual refresh without replaying the animation.
- Preserve unknown values and respect macOS Reduce Motion; add `setup --no-animation`.
- Render animation frames in a single native batch and retain the static menu fallback.
- Add tests for animation timing, recovery, refresh, renderer batches, and stream shutdown.
- Users upgrading from 0.1.x must run `codexbar-lite setup` once to enable streaming.

## 0.1.1

- Redesign the README with a compact overview, appearance-aware preview, and quick installation.
- Move detailed setup and troubleshooting into a dedicated user guide.
- Standardize the README, architecture, release guide, and validation record in English.
- Publish an English-only source archive and update the Homebrew release.

## 0.1.0

- Codex-only quota monitoring through the local app-server.
- Native dual-row menu bar display and appearance adaptation.
- Missing-window and error states, local reset times, JSON status output.
- Explicit SwiftBar setup/uninstall and local diagnostics.
- Apple Silicon (M-series) Macs only.
- Source installation, Homebrew Formula generation, CI and release workflow.
