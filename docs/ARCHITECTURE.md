# 架构

```text
SwiftBar (every 1 minute)
  → managed shell plugin
  → stable codexbar-lite launcher
  → Python standard-library JSON-RPC client
  → local Codex app-server → account service
  → AppKit PNG renderer → SwiftBar menu
```

Python 仅使用标准库。Swift/AppKit 渲染器在安装时编译，刷新时无需启动编译器。每次查询最多等待 15 秒，渲染最多 5 秒；子进程会被回收，不保留持久连接或本地额度缓存。

JSON-RPC 使用 initialize → initialized → account/rateLimits/read。读取端按字节缓存和换行解析，避免 `readline()` 在半行上无限等待；既支持分包，也支持一次写入多行。多额度桶优先选择 codex；不会拿其他产品的桶作为后备。

插件名称固定为 `codexbar-lite.1m.sh`。setup 通过临时文件原子替换自己的脚本，并拒绝覆盖无标记文件或符号链接。安装过程不扫描或上传其他插件。Homebrew wrapper 的 opt 路径保持稳定，Cellar 内的 Python 模块随版本更新。

额度中的缺失值保持未知；窗口名称根据返回时长生成。`5h`/`7d` 只在没有窗口时作为布局占位。文字错误状态与“额度为零”分开。

菜单栏 PNG 为透明 240 × 66 像素，以 80 × 22 pt 显示。SF 字体约 10pt；100% 为避免裁切略缩小。未点亮短柱随浅色/深色外观调整透明度。
