# 和声 · 合唱练习室

电脑和手机都能使用的本地合唱练习工具。保留原谱排版，支持跟谱播放、分声部独听、音量调整、变速和分段循环；安卓安装版还支持局域网更新和手机间离线传递。

当前版本为 **1.8.0**。仓库包含现有六首可播放歌曲的谱面、PDF、MusicXML、MIDI、音符数据及离线音色，克隆后即可运行，无需重新识谱或下载音色。

## 快速开始

安装 Node.js 22 或更新版本，然后执行：

```sh
git clone https://github.com/boyang-web/choir-studio.git
cd choir-studio
node choir-studio/server.mjs
```

浏览器打开 <http://localhost:5173>。日常运行无需安装 npm 依赖，也无需联网。Windows 也可以双击根目录的 `启动合唱练习室.bat`。

手机连接同一 Wi-Fi 后，打开终端显示的局域网地址。浏览器使用时需保持服务运行；安卓安装版可在接收内容后离线使用。详细步骤见 [手机局域网更新说明](docs/手机局域网更新说明.md)。

## 当前曲库

| 曲目 | 页数 | 状态 |
| --- | --- | --- |
| 敕勒歌 | 10 | 已有曲目，保留逐小节修订和核对记录 |
| Let It Go | 19 | 已有曲目，仍有已记录的识谱问题 |
| 没有共产党就没有新中国 | 6 | 试导入 · 待校订 |
| 夜来香 | 6 | 试导入 · 待校订 |
| 我歌唱的理由有很多 | 12 | 试导入 · 待校订 |
| 告别时刻 | 9 | 试导入 · 待校订 |

《为要寻一个明星》的原谱和识谱材料也已保留；因声部分配未通过检查，暂未加入可播放曲库。识谱结果不等同于人工逐音校订，详情见 [新歌曲导入记录](docs/新歌曲导入记录.md) 和 [验证记录](choir-studio/VALIDATION.md)。

## 开发与验证

在仓库根目录执行：

```sh
npm --prefix choir-studio ci
npm --prefix choir-studio test
```

`package-lock.json` 固定 JavaScript 依赖。GitHub Actions 在 Linux 和 Windows 上使用 Node.js 22、24 运行现有测试，并检查 Python 脚本语法。本次干净副本的检查结果见 [仓库验证记录](docs/仓库验证记录.md)。真实浏览器验证、平台构建和手机实机验收另行执行，步骤见 [应用说明](choir-studio/README.md)。

修改乐谱、生成 MIDI 或构建 Windows 安装包时需要 Python 3.12，以及 `tools/requirements.txt` 中的依赖；仅运行网页不需要 Python。工具安装和曲库重建步骤见 [工具说明](tools/README.md)。

## 安装包与构建

源码仓库不保存 EXE、APK 和历史 ZIP。当前电脑已有的安装包仍保存在本地 `releases/`；构建脚本也会更新该目录。

在 Windows 上安装对应工具后执行：

```sh
npm --prefix choir-studio run build:windows
npm --prefix choir-studio run build:android
```

Windows 构建使用系统 .NET Framework 编译器、WebView2 SDK 和 Python/Pillow；安卓构建使用 JDK 21、Android SDK 35、Gradle 和 Capacitor。输出位置见 [安装包说明](releases/README.md)。

## 目录

| 位置 | 内容 |
| --- | --- |
| `choir-studio/` | 网页、服务端、安卓和 Windows 工程、测试、构建脚本 |
| `choir-studio/public/songs/` | 六首可播放歌曲及目录，随源码一并提交 |
| `choir-studio/public/samples/` | 离线音色及来源说明 |
| `data/sources/` | 原始 PDF 和 MIDI |
| `data/omr/`、`data/revisions/` | 识谱工程、MusicXML 和修订材料 |
| `inspection/` | 核对脚本、审计数据及谱面截图 |
| `tools/` | 识谱与曲库生成脚本、Python 依赖清单 |
| `docs/` | 使用说明、导入记录和界面参考 |
| `releases/`、`archive/` | 本地安装包和历史分发包，不纳入 Git |

`.gitignore` 排除下载的工具链、依赖、浏览器资料、缓存、构建产物及签名密钥，保留这些文件的本地副本。`choir-studio/.update-keys/` 是现有手机信任的更新签名密钥目录，换电脑时需单独备份迁移；新克隆会在首次启动时生成自己的密钥。

第三方库和音色的署名及许可位置见 [第三方材料说明](THIRD_PARTY_NOTICES.md)。此前目录移动的清单见 [structure-moves.json](docs/structure-moves.json)。
