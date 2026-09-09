# Architecture

```text
SwiftBar (every 1 minute)
  → managed shell plugin
  → stable codexbar-lite launcher
  → Python standard-library JSON-RPC client
  → local Codex app-server → account service
  → AppKit PNG renderer → SwiftBar menu
```

Python uses only the standard library. The Swift/AppKit renderer is compiled during installation, so refreshes do not invoke the compiler. Each quota request has a 15-second timeout; rendering has a 5-second timeout. Child processes are reaped, and the client keeps no persistent connection or local quota cache.

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
