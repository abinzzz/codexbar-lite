# v0.1.0 验证记录

## 已通过

- 本地构建与 11 项测试：额度解析、Codex bucket 选择、未知窗口、路径、安装升级卸载、文件保护、JSON-RPC 分包/EOF/超时/错误、PNG 输出及无效输入。
- AppKit 渲染器：浅色/深色、52%/42%、100%/0%、未知额度均生成正确尺寸 PNG；已目视检查文字及边界。
- `doctor --live`：使用现有 Codex 登录读取成功，未记录或打包账户响应。
- [Apple Silicon CI](https://github.com/abinzzz/codexbar-lite/actions/runs/34215050456)：源码构建、测试和 Formula 语法验证成功。
- [v0.1.0 Release](https://github.com/abinzzz/codexbar-lite/actions/runs/34215133596)：构建测试及自动发布成功。
- [公开 Homebrew 安装验证](https://github.com/abinzzz/codexbar-lite/actions/runs/34242162970)：干净 M1 runner 从公开 Tap/Release 执行 `brew install`，随后 `brew test`、ARM64 二进制检查、隔离 SwiftBar 目录的 setup/uninstall 全部通过。
- 下载的正式源码包 SHA-256 与 Release 的 SHA256SUMS 及 Tap Formula 一致。
- 发布包不含构建缓存、个人路径或认证文件。

## 环境范围

只支持 Apple Silicon（M 系列）Mac。GitHub 安装验证运行于 macos-14 ARM64；API 实际调用在已有 Codex 登录的本机完成。

本机直接执行 Homebrew 源码安装时，Homebrew 检测到旧版 Xcode 15.2 并拒绝构建，指定 Command Line Tools 仍无法绕过该检查。未修改或删除该 Xcode；公开安装链路已由上述干净 M1 环境验证。这是本机开发工具兼容性限制。
