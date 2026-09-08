# 发布到 GitHub 和 Homebrew

使用两个公开仓库：

- `abinzzz/codexbar-lite`：本目录的源码、Issues、版本及 GitHub Actions。
- `abinzzz/homebrew-codexbar-lite`：只存放 `Formula/codexbar-lite.rb`，供 Homebrew Tap 使用。

项目未进入 homebrew/core，因此第一版的完整安装命令为 `brew install abinzzz/codexbar-lite/codexbar-lite`。用户安装过 Tap 后可用 `brew install codexbar-lite`。

## 1. 创建源码仓库

发布账号为 `abinzzz`。检查 README、LICENSE 和仓库可见性，然后在本目录执行：

```sh
gh auth login
git init -b main
git add .
git commit -m "Initial Codexbar Lite release"
gh repo create abinzzz/codexbar-lite --public --source . --remote origin --push
```

README 已使用 `abinzzz`；首次发布完成后确认安装命令可用。不要把 `.build`、真实限额响应或本机认证文件添加到仓库。

## 2. 发布首个版本

等待 CI 通过，再创建与 `src/codexbar.py` 中 VERSION 一致的 tag：

```sh
git tag v0.1.0
git push origin v0.1.0
```

Release workflow 会重新构建、测试、验证 tag，并发布：

- `codexbar-lite-0.1.0.tar.gz`：源码安装包；不含本机构建产物。
- `SHA256SUMS`：该源码包的 SHA-256。
- `codexbar-lite.rb`：已填入当前仓库、版本和真实校验值的 Formula。

CI 失败不会发布。不要重复使用已发布 tag 或替换同一版本的归档，否则已安装 Formula 的校验值会失效。

## 3. 发布 Homebrew Tap

在另一个空目录执行（使用相同账号）：

```sh
mkdir homebrew-codexbar-lite
cd homebrew-codexbar-lite
mkdir Formula
gh release download v0.1.0 --repo abinzzz/codexbar-lite --pattern codexbar-lite.rb --dir Formula
git init -b main
git add Formula
git commit -m "Add codexbar-lite 0.1.0"
gh repo create abinzzz/homebrew-codexbar-lite --public --source . --remote origin --push
brew install abinzzz/codexbar-lite/codexbar-lite
brew test abinzzz/codexbar-lite/codexbar-lite
codexbar-lite doctor
```

Formula 不在 Homebrew 安装阶段自动修改用户的 SwiftBar 设置。用户通过 `codexbar-lite setup` 完成启用。

仅支持 Apple Silicon（M 系列）Mac。这是从源码构建的 Formula，首次安装需要 Apple 开发工具。没有预编译 bottle，也不需要把未经签名的可执行文件作为下载产物发布。

## 手动生成发布产物

不使用 GitHub Actions 时：

```sh
make check
python3 tools/release.py --repository abinzzz/codexbar-lite
```

将 `dist/` 中的三个文件上传到 **v0.1.0** Release，再将 Formula 复制到 Tap。生成工具本身不会上传或修改仓库，必须使用实际仓库名生成。归档只包含明确列出的源码和文档，不包含用户配置。

## 下一版本

修改 VERSION 和 CHANGELOG，运行 `make check`，提交并推送新的 tag。下载新 Release 的 Formula，替换 Tap 中旧 Formula 并提交。用户即可运行 `brew upgrade codexbar-lite`。主仓库的默认 GITHUB_TOKEN 无法跨仓库自动写入 Tap，因此 Tap 更新是显式维护步骤。
