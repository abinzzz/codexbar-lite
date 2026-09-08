# v0.1.0 本地验证记录

- `make check`：构建、测试、版本命令和无账户演示通过。
- 11 项测试：额度解析、Codex bucket 选择、未知窗口、路径、安装升级卸载、文件保护、JSON-RPC 分包/EOF/超时/错误、PNG 输出及无效输入。
- AppKit 渲染器：浅色/深色、52%/42%、100%/0%、未知额度均生成正确尺寸 PNG；已目视检查文字及边界。
- `doctor --live`：使用现有 Codex 登录读取成功，未记录或打包账户响应。
- Homebrew：Formula Ruby 语法通过，Homebrew Formulary 成功加载 v0.1.0。
- 发布包：仅含明确列出的源码、文档和演示图，不含构建缓存、个人路径或认证文件。

仍需发布后验证：GitHub Actions 的 Apple Silicon 运行记录、公开 Release 下载，以及通过公开 Tap 的完整 `brew install` / `brew test`。本地通过不等于这些远端步骤已经执行。
