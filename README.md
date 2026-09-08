# Codexbar Lite

在 macOS 菜单栏里，看一眼 Codex 还剩多少额度。

双行显示短周期和周额度，使用平滑系统字体、圆角进度条和百分比。仅显示 **Codex** 额度，不含余额网关、其他模型或付费 API 账单。通过 SwiftBar 运行，无独立后台守护进程。

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/preview-dark.png">
  <img src="docs/preview-light.png" width="240" alt="Demo: Codex 5h 52%, 7d 42% remaining">
</picture>

*上图为放大 3 倍的合成演示，实际菜单栏显示为 80 × 22 pt；不含个人账户数据。*

## 安装

要求：macOS 13 或更新版本、SwiftBar、已使用 ChatGPT 账户登录的 Codex CLI。源码构建需要 Apple Command Line Tools（`xcode-select --install`）或 Xcode，以及 Python 3.10+。Homebrew 负责安装 Python 依赖。

### Homebrew

源码仓库：[abinzzz/codexbar-lite](https://github.com/abinzzz/codexbar-lite)。Homebrew Tap：[abinzzz/homebrew-codexbar-lite](https://github.com/abinzzz/homebrew-codexbar-lite)。以下命令在首个 Release 和 Tap 发布后可用：

```sh
brew install --cask swiftbar codex
brew install abinzzz/codexbar-lite/codexbar-lite
codex login
open -a SwiftBar
# 首次打开 SwiftBar 时，选择一个插件目录
codexbar-lite setup
```

已安装且已登录的 Codex 可以直接使用。`setup` 会读取 SwiftBar 已配置的插件目录，只写入自己的 `codexbar-lite.1m.sh`，不会更改其他插件或 SwiftBar 偏好。也可显式指定：

```sh
codexbar-lite setup --plugin-dir "$HOME/SwiftBar Plugins"
```

指定目录后，请在 SwiftBar 中选择同一目录。菜单栏每分钟刷新一次。

### 从源码安装（现在即可使用）

在本项目根目录运行：

```sh
python3 tools/install.py --prefix "$HOME/.local"
"$HOME/.local/bin/codexbar-lite" setup
```

如需直接使用命令名，将 `$HOME/.local/bin` 加入 shell 的 `PATH`。构建出的插件启动脚本使用绝对路径，不依赖 SwiftBar 的 shell 初始化文件。

## 使用

```sh
codexbar-lite status        # 请求当前额度，输出 JSON
codexbar-lite doctor        # 检查本地 Codex 与图片渲染器，不请求账户额度
codexbar-lite doctor --live # 额外验证真实额度读取
codexbar-lite menu --demo   # 使用合成数据预览，无需登录
codexbar-lite --version
```

- 文字显示**剩余**比例：`100 − usedPercent`；按整数四舍五入。
- 绿色：剩余超过 60%；橙色：20%–60%；红色：低于 20%。
- 五个短柱是近似值，按最近的 20% 档位显示；非零额度至少亮一格，具体数值以百分比为准。
- 额度窗口名称使用服务返回的时长，不强制把所有账户标成 5h / 7d。缺失窗口显示 `--%`。
- 菜单显示重置时间及本地时区。额度属于账户，并非当前会话单独的额度。
- 自动适配 SwiftBar 提供的浅色/深色外观；图片渲染失败时退回文字显示。

### 自定义 Codex 路径

支持 Apple Silicon、Intel Homebrew 及 PATH 中的 Codex。自定义安装位置可用：

```sh
codexbar-lite setup --codex /absolute/path/to/codex
codexbar-lite status --codex /absolute/path/to/codex
```

`setup` 将当时找到的 Codex 路径保存到自己的插件脚本。之后如果移动 Codex 安装位置，重新运行 `setup`。终端命令也可用 `CODEXBAR_CODEX` 环境变量。

## 升级与卸载

```sh
brew upgrade codexbar-lite
# 无需重新 setup：插件指向 Homebrew 的稳定 opt 路径

codexbar-lite uninstall
brew uninstall codexbar-lite
```

源码安装：再次执行相同的安装命令即可升级。移除菜单栏插件使用 `codexbar-lite uninstall`；若安装到专用前缀，还可自行移除该专用目录。`uninstall` 只删除带本项目标记的插件，不移除 Codex、SwiftBar 或账户数据。

## 隐私和兼容性

Codexbar Lite 通过本机 `codex app-server --stdio` 的 `account/rateLimits/read` 读取额度，复用 Codex 登录状态，不读取或复制认证文件，不要求 API key，不自建服务器，不发送分析数据。Codex CLI 自身会连接其账户服务；这不是离线额度查询。

这是独立的社区工具，与 OpenAI、SwiftBar 及其他同名/近似名称项目没有隶属关系。依赖 Codex app-server 接口，后续 CLI 升级可能改变兼容性。API-key-only 登录不保证提供 ChatGPT/Codex 订阅窗口。缺失或失败不会显示成“额度已用尽”。

接口依据：[Codex App Server 文档](https://developers.openai.com/codex/app-server)。安装格式依据：[Homebrew Formula Cookbook](https://docs.brew.sh/Formula-Cookbook)。

## 常见问题

**没有看到组件**：确认 SwiftBar 正在运行，插件目录一致，且 macOS 允许 SwiftBar 出现在菜单栏。等待下一分钟刷新，或在 SwiftBar 中手动刷新。

**Usage unavailable**：先运行 `codexbar-lite doctor --live`。确认 `codex login` 使用了支持额度查询的账户，并更新 Codex CLI。不要在 GitHub Issue 中粘贴认证文件或 access token。

**出现两个组件**：从旧的手工版本迁移时，先在 SwiftBar 禁用旧的 `chatgpt-usage.1m.py`。本工具不会自动删除旧插件。

**构建报错**：运行 `xcode-select --install` 安装 Apple 开发工具，安装完成后重新构建。

## 开发与发布

```sh
make check
```

测试使用伪 app-server，无需登录；涵盖协议分包、超时、EOF、账户错误、额度解析及插件安装保护。GitHub CI 配置覆盖 Apple Silicon 与 Intel macOS；CI 结果以实际仓库运行记录为准。

详见 [发布指南](docs/RELEASING.md)、[架构说明](docs/ARCHITECTURE.md) 和 [变更日志](CHANGELOG.md)。MIT License。

---

**English:** A lightweight Codex quota indicator for the macOS menu bar, powered by SwiftBar. Shows remaining quota with native system typography and compact progress bars. Uses your existing Codex CLI login; no API key or separate backend. Build with `make check`, install with `python3 tools/install.py --prefix "$HOME/.local"`, then run `~/.local/bin/codexbar-lite setup`. Homebrew installation becomes available after the maintainer publishes the tap described in the release guide.
