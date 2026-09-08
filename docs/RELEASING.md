# Publishing to GitHub and Homebrew

The project uses two public repositories:

- [abinzzz/codexbar-lite](https://github.com/abinzzz/codexbar-lite): source, documentation, issues, releases, and GitHub Actions.
- [abinzzz/homebrew-codexbar-lite](https://github.com/abinzzz/homebrew-codexbar-lite): the Homebrew formula and tap documentation.

The full installation command is `brew install abinzzz/codexbar-lite/codexbar-lite`. Once the tap is installed, users can run `brew install codexbar-lite`. This project is not part of homebrew/core.

## Prepare a release

Both repositories already exist. In the source repository:

1. Update `VERSION` in `src/codexbar.py` and add a changelog entry.
2. Run `make check`, commit the changes, and push `main`.
3. Wait for the Apple Silicon CI run to succeed.
4. Create and push a new tag matching `VERSION`.

For example, to publish version 0.1.1:

```sh
git tag v0.1.1
git push origin v0.1.1
```

Never reuse a published tag or replace an existing release archive. Doing so would invalidate the checksum in an already published Homebrew formula.

## Automated release artifacts

The Release workflow rebuilds the project, runs tests, checks that the tag matches the version, and uploads:

- `codexbar-lite-VERSION.tar.gz`: a source archive without local build products.
- `SHA256SUMS`: the source archive's SHA-256 checksum.
- `codexbar-lite.rb`: a formula containing the repository URL, version, and actual archive checksum.

A failed build or test prevents publication. Keep `.build`, live quota responses, and authentication files out of the repository.

## Update the Homebrew tap

From your local `homebrew-codexbar-lite` checkout, download the formula for the new release:

```sh
gh release download v0.1.1 --repo abinzzz/codexbar-lite \
  --pattern codexbar-lite.rb --dir Formula --clobber
git add Formula/codexbar-lite.rb
git commit -m "Update codexbar-lite to 0.1.1"
git push origin main
```

The default `GITHUB_TOKEN` in the source repository cannot write to the separate tap repository. Updating the tap is an explicit maintainer step.

The formula supports only Apple Silicon (M-series) Macs. It builds from source and requires Apple development tools; no prebuilt bottle is provided. Installation does not automatically modify SwiftBar preferences. Users enable the plugin with `codexbar-lite setup`.

## Verify public installation

After updating the tap, run the dedicated workflow:

```sh
gh workflow run homebrew.yml --repo abinzzz/codexbar-lite
```

It installs from the public tap and release on a clean M1 runner, runs `brew test`, verifies the ARM64 executable, and checks setup/uninstall in an isolated SwiftBar directory.

For a local check:

```sh
brew upgrade codexbar-lite
brew test abinzzz/codexbar-lite/codexbar-lite
codexbar-lite doctor
```

A live account check is optional and requires an existing Codex login:

```sh
codexbar-lite doctor --live
```

## Generate artifacts manually

```sh
make check
python3 tools/release.py --repository abinzzz/codexbar-lite
```

Upload the three files in `dist/` to the release tag matching `VERSION`, then copy the generated formula into the tap. The generator does not upload files or modify repositories. It archives an explicit set of source and documentation files and excludes user configuration.
