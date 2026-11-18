# 和声 · 合唱练习室

电脑和手机均可离线使用的合唱练习工具，保留原谱排版，支持跟谱播放、分声部独听、音量调整、变速及分段循环。

当前版本 **1.9.0**。新增《回声》双合唱队八声部，三页、38 小节，练习速度由用户确认设为 120 BPM。
原 PDF、MusicXML、MIDI、逐声部校订账本随仓库保存，详见 [回声核验记录](docs/回声核验记录.md)。

## 下载与更新

在 [GitHub Releases](https://github.com/boyang-web/choir-studio/releases) 下载对应系统的安装包：

| 平台 | 安装包 |
| --- | --- |
| macOS Apple Silicon | arm64 DMG |
| macOS Intel | x64 DMG |
| Windows x64 | 便携 EXE，需要 WebView2 Runtime |
| Android | APK |

歌曲和音色均内置，无需 Node.js、Python 或网络即可练习。更新通过下载安装新版完成。
1.9.0 已删除局域网更新、手机离线转发及 APK 下载服务。
macOS 包未进行 Apple Developer ID 签名／公证，首次打开可能需要在系统隐私与安全设置中确认。
本版 Android 是新签名的调试构建；旧安装签名不兼容时需卸载后重新安装，原有本机设置会清除。

## 源码运行

安装 Node.js 22 或更新版本，在仓库根目录执行：

```sh
node choir-studio/server.mjs
```

浏览器打开 http://127.0.0.1:5173 。开发服务仅监听本机，不提供局域网更新。

## 曲库

《敕勒歌》《Let It Go》保留已有校订记录；《没有共产党就没有新中国》《夜来香》《我歌唱的理由有很多》《告别时刻》仍为试导入待校订。
《回声》使用此份 PDF 的嵌入式音乐字符和矢量符号提取及原谱比对，保留八声部和回声延迟。
自动结构检查和音高比对不等同于音乐人员听感签收，其他曲目不会因本次发布自动变为已校订。

## 开发与验证

```sh
npm --prefix choir-studio ci
npm --prefix choir-studio test
python -m pip install -r tools/requirements.txt
python tools/audit_hui_sheng.py
python tools/build_hui_sheng.py
```

真实浏览器验收：先启动开发服务，然后运行 `npm --prefix choir-studio run test:browser` 和
`node choir-studio/tests/hui-sheng-browser.mjs`。可用 `CHROME_PATH` 指定本机 Chrome。

macOS 构建：在 `choir-studio/macos` 执行 `npm ci`、`npm run build`。
Windows、Android 原有 PowerShell 构建命令见 [应用说明](choir-studio/README.md)。
GitHub Actions 的 `Build and release` 工作流先验证乐谱与应用，再生成三端安装包；
发布提交带 `[release]` 时在所有构建通过后创建 GitHub Release 和 SHA-256 校验文件。

## 目录

- `choir-studio/`：网页、服务、macOS／Windows／Android 工程及测试。
- `choir-studio/public/songs/`、`public/samples/`：内置曲库和离线音色。
- `data/sources/`：原始 PDF 和 MIDI；`data/verified/`：逐声部来源账本。
- `tools/`：识谱、校订、审计和生成工具，依赖见 [工具说明](tools/README.md)。
- `inspection/`、`data/omr/`、`data/revisions/`：审计报告、识谱工程和历史修订。
- `docs/`：使用说明、核验与发布记录。
- `releases/`：本地构建结果，不纳入 Git，分发以 GitHub Releases 为准。

第三方许可见 [第三方材料说明](THIRD_PARTY_NOTICES.md)。签名材料、依赖及下载的工具链不纳入 Git。
