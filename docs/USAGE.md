# User guide

[Back to the README](../README.md)

## Installation

Requires an Apple Silicon Mac, macOS 13 or later, SwiftBar, and the Codex CLI signed in with a supported ChatGPT account. Source builds require Apple Command Line Tools (`xcode-select --install`) or Xcode, plus Python 3.10 or later. Homebrew installs the Python dependency.

### Homebrew

```sh
brew install --cask swiftbar codex
brew install abinzzz/codexbar-lite/codexbar-lite
codex login
open -a SwiftBar
# Choose a plugin directory when SwiftBar first opens.
codexbar-lite setup
```

You can reuse an existing SwiftBar installation and Codex login. `setup` reads your configured SwiftBar plugin directory and installs `codexbar-lite.1m.sh`. Other plugins and SwiftBar preferences are preserved.

To choose a directory explicitly:

```sh
codexbar-lite setup --plugin-dir "$HOME/SwiftBar Plugins"
```

Select the same directory in SwiftBar. The plugin refreshes every minute.

Source: [abinzzz/codexbar-lite](https://github.com/abinzzz/codexbar-lite). Tap: [abinzzz/homebrew-codexbar-lite](https://github.com/abinzzz/homebrew-codexbar-lite).

### From source

Run these commands from the project root:

```sh
python3 tools/install.py --prefix "$HOME/.local"
"$HOME/.local/bin/codexbar-lite" setup
```

Add `$HOME/.local/bin` to your shell's `PATH` to use the command by name. The generated plugin uses absolute paths and does not depend on SwiftBar loading your shell configuration.

## Usage

```sh
codexbar-lite status        # Fetch current limits as JSON.
codexbar-lite doctor        # Check local dependencies without fetching limits.
codexbar-lite doctor --live # Also verify a live quota request.
codexbar-lite menu --demo   # Preview synthetic data without signing in.
codexbar-lite --version
```

- Percentages represent **remaining** quota: `100 − usedPercent`, rounded to an integer.
- Green means more than 60% remaining; orange means 20%–60%; red means below 20%.
- The five segments approximate the nearest 20% increment. Nonzero quota lights at least one segment; the percentage provides the precise displayed value.
- Window labels follow the durations returned by the service. Missing windows show `--%`.
- The dropdown shows reset times in your local time zone. Limits are shared across your Codex account.
- The plugin follows SwiftBar's light or dark appearance and falls back to text if image rendering fails.

### Custom Codex location

The CLI searches your `PATH` and common Homebrew locations. Intel Macs are not supported. For a custom installation:

```sh
codexbar-lite setup --codex /absolute/path/to/codex
codexbar-lite status --codex /absolute/path/to/codex
```

`setup` saves the detected Codex path in its plugin script. Run it again if you move your Codex installation. Terminal commands also accept the `CODEXBAR_CODEX` environment variable.

## Upgrade and uninstall

```sh
brew upgrade codexbar-lite
# No additional setup is needed: the plugin uses Homebrew's stable opt path.

codexbar-lite uninstall
brew uninstall codexbar-lite
```

For source installations, rerun the original installation command to upgrade. Use `codexbar-lite uninstall` to remove the menu bar plugin. If you installed into a dedicated prefix, you may also remove that dedicated directory. Uninstall only removes the plugin managed by this project; Codex, SwiftBar, and account data remain available.

## Privacy and compatibility

Codexbar Lite calls `account/rateLimits/read` through the local `codex app-server --stdio` process and reuses your existing Codex login. It does not directly read or copy authentication files, require an API key, operate a separate backend, or send analytics. The Codex CLI itself connects to its account service, so quota requests require network access.

This is an independent community project, unaffiliated with OpenAI, SwiftBar, or similarly named projects. Compatibility depends on the Codex app-server interface and may change with future CLI versions. API-key-only authentication may not provide subscription quota windows. Unavailable data is shown as unknown rather than exhausted quota.

References: [Codex App Server](https://developers.openai.com/codex/app-server) and [Homebrew Formula Cookbook](https://docs.brew.sh/Formula-Cookbook).

## Troubleshooting

**The plugin is missing:** Check that SwiftBar is running, the plugin directories match, and macOS allows SwiftBar in the menu bar. Wait for the next refresh or refresh manually in SwiftBar.

**Usage unavailable:** Run `codexbar-lite doctor --live`. Check your account with `codex login` and update the Codex CLI. Do not post authentication files or access tokens in GitHub issues.

**Duplicate indicators:** When migrating from the original manual plugin, disable `chatgpt-usage.1m.py` in SwiftBar. Setup does not remove that older plugin automatically.

**Build errors:** Install Apple development tools with `xcode-select --install`, then rebuild. If Homebrew reports an outdated Xcode installation, update that Xcode. Selecting Command Line Tools alone may not satisfy Homebrew's environment checks.

