# Validation record

## Version 0.1.0

- Local build and 11 tests passed: quota parsing, Codex bucket selection, unknown windows, paths, setup/upgrade/uninstall, file protection, JSON-RPC fragmentation/EOF/timeouts/errors, PNG output, and invalid renderer input.
- Renderer previews covered light/dark appearances, 52%/42%, 100%/0%, and unknown quotas. Image dimensions, text, and clipping were checked.
- `doctor --live` succeeded using an existing Codex login. No account response was recorded or packaged.
- [Apple Silicon CI](https://github.com/abinzzz/codexbar-lite/actions/runs/34215050456) passed source builds, tests, and formula syntax validation.
- The [release workflow](https://github.com/abinzzz/codexbar-lite/actions/runs/34215133596) successfully built, tested, and published v0.1.0.
- [Public Homebrew installation](https://github.com/abinzzz/codexbar-lite/actions/runs/34242162970) passed on a clean M1 runner: installation from the public tap/release, `brew test`, ARM64 verification, and setup/uninstall in an isolated SwiftBar directory.
- The downloaded source archive matched both `SHA256SUMS` and the tap formula.
- The release archive excluded build caches, personal paths, and authentication files.

## Environment scope

Only Apple Silicon (M-series) Macs are supported. GitHub installation testing used macos-14 ARM64. The live account request was tested separately on a local machine with an existing Codex login.

Local Homebrew installation was blocked by an outdated Xcode 15.2 installation. Selecting Command Line Tools did not satisfy Homebrew's check. That Xcode installation was neither modified nor removed; the public installation path was verified on the clean M1 runner instead.

## Version 0.1.1

This release standardizes all current project documentation in English. Runtime messages, source comments, workflows, the license, tap documentation, and release notes were already in English. The source tree is checked for remaining CJK text before publication. Historical release archives are retained unchanged.

## Version 0.2.0

- 20 local tests passed, including startup interpolation, one-second scheduling, delayed data recovery, no replay on refresh, disabled animation, fallback rendering, complete stream frames, stdin actions, native batch equivalence, and process shutdown.
- A real native-renderer playback emitted 31 frames over approximately 1.003 seconds. The first, middle, and final images were inspected at 0/0%, 50/42%, and 100/85%.
- The Homebrew formula now exercises a complete streaming response in addition to the static demo.
