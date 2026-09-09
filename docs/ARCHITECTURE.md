# Architecture

```text
SwiftBar (streaming plugin host)
  → managed shell plugin
  → stable codexbar-lite launcher
  → Python streaming loop (60-second polling / stdin refresh)
  → standard-library JSON-RPC client
  → local Codex app-server → account service
  → AppKit PNG renderer → SwiftBar menu
```

Python uses only the standard library. The Swift/AppKit renderer is compiled during installation, so refreshes do not invoke the compiler. Each quota request has a 15-second timeout; rendering has a 5-second timeout. The Python plugin process stays alive under SwiftBar supervision and sleeps while waiting for the next poll or stdin action. Child processes are reaped, and the client keeps no persistent connection or local quota cache.

The JSON-RPC sequence is `initialize` → `initialized` → `account/rateLimits/read`. The reader buffers bytes and splits complete lines, avoiding an unbounded `readline()` wait on a partial message. It handles both fragmented messages and multiple lines in one read. For multi-bucket responses, it selects the `codex` bucket and does not substitute another product's limits.

The plugin filename is `codexbar-lite.1m.sh`. Setup atomically replaces its own script through a temporary file and refuses to overwrite unmarked files or symbolic links. Installation does not scan or upload other plugins. The Homebrew launcher's `opt` path remains stable while the Python module in the Cellar changes with each version.

Missing quota values remain unknown. Window labels use the returned durations; `5h` and `7d` serve as fallback labels when durations are unavailable. Error output is distinct from zero remaining quota.

The menu bar image is a transparent 240 × 66-pixel PNG displayed at 80 × 22 pt. The system font is approximately 10 pt; `100%` uses a slightly smaller size to prevent clipping. Empty segments adjust their color and opacity for light and dark appearances.

Only Apple Silicon Macs are supported. The installer requires a native ARM64 environment and compiles the renderer for `arm64-apple-macos13.0`.

## README animation

The light and dark GIFs use the production renderer with synthetic inputs. Over 101 frames, the 5-hour window decreases from 100% to 0%, while the weekly window decreases from 100% to 85%. This is an illustrative scenario, not a fixed relationship between quota windows. Each loop pauses at both endpoints.

After `make build`, regenerate the assets with:

```sh
swift tools/generate-demo.swift .build/install/libexec/usage-renderer docs
```

The generator uses AppKit and ImageIO, adds an opaque appearance-matched background for smooth GIF text, and never requests account data.

## Startup and reset animations

The shell wrapper declares `swiftbar.type=streamable` and `swiftbar.useTrailingStreamSeparator=true`. Each complete menu frame is flushed with a trailing `~~~` separator, so SwiftBar can commit the frame even when a PNG spans multiple pipe reads. The native renderer supports batch input, preparing all 31 PNG frames in one process before the one-second monotonic-clock playback starts.

The initial loading state displays unknown quota. Each window's first known value triggers interpolation; missing windows stay unknown. The dropdown always contains authoritative quota values while the menu-bar image animates. Per-window reset deadlines shorten the normal polling wait. Once a deadline passes, that window animates on its next known response; the other row stays unchanged. Consumed deadlines are cleared and only future timestamps are armed, preventing repeated animation from stale responses. Ordinary polls and `stdin=refresh` actions skip animation unless a window is pending. Failed requests retain pending resets and use the normal retry interval. The loop sleeps with a selector, exits on stdin EOF, and handles SIGTERM so an in-flight quota subprocess can be reaped.

Animation is skipped when macOS Reduce Motion is enabled, `--no-animation` is requested, or all known quota values are zero. If batch rendering fails, the plugin shows the final menu directly.
