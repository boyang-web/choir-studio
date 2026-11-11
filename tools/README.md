# 曲库与构建工具

这些脚本用于识谱、校订和重新生成曲库。当前可播放资源已经保存在 `choir-studio/public/`，日常运行无需执行它们。

## Python 环境

在仓库根目录创建 Python 3.12 虚拟环境：

```sh
python -m venv .venv
```

Windows PowerShell 激活环境后安装依赖：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r tools/requirements.txt
```

Linux/macOS 使用 `source .venv/bin/activate` 激活。`requirements.txt` 记录当前使用的 music21、PyMuPDF 和 Pillow 版本。旧工作区的 `tools/python-libs/` 仍受脚本支持，但不纳入 Git；新环境可以直接使用虚拟环境。

## 常用入口

从仓库根目录执行。生成脚本会覆盖对应的曲库资源，修改后运行 `npm --prefix choir-studio test`。

| 脚本 | 用途 |
| --- | --- |
| `import_scores.py` | 从已有 OMR、MusicXML、PDF 生成原有两首曲目的数据 |
| `update_chile_score.py --generate-only` | 复用修订后的 MusicXML，重建十页版《敕勒歌》 |
| `build_performance.py` | 从 MusicXML 和修订规则生成原有曲目的 MIDI 与音符数据 |
| `transcribe_new_scores.py --id <id>` | 使用本地 Audiveris 识别指定的新谱 |
| `import_new_scores.py --id <id> --reuse-export` | 复用新歌的 MusicXML，生成谱面和播放数据 |
| `export_reading_scores.py` | 导出用于阅读的原谱 SVG |
| `fetch_audio_samples.py` | 按来源下载音色，现有音色已随仓库提交 |
| `create_design_previews.py` | 生成本地界面参考，输出到被 Git 忽略的 `public/designs/` |

例如：

```sh
python tools/update_chile_score.py --generate-only
python tools/import_new_scores.py --id ye-lai-xiang --reuse-export
npm --prefix choir-studio test
```

新歌标识和来源文件名定义在 `new-scores.json`，导入状态见 [新歌曲导入记录](../docs/新歌曲导入记录.md)。

## 识谱与本地工具链

需要重新识别 PDF 或重新导出 OMR 时，现有脚本使用 Audiveris 5.11.0 的 Windows 安装目录：

```text
tools/audiveris/Audiveris/
  runtime/bin/java.exe
  app/
```

将 Audiveris 安装或解包到这个位置后再执行识谱命令。复用已提交的 MusicXML 时，`--generate-only` 和 `--reuse-export` 无需调用 Audiveris。

Android 构建可通过 `JAVA_HOME`、`ANDROID_HOME` 指定本机安装；也支持本地 `tools/java21/`、`tools/android-sdk/` 和 `tools/gradle-8.11.1/`。Windows 构建会按需下载 WebView2 SDK 到 `tools/webview2/`。

下载的 SDK、Python 库、浏览器测试资料、日志和临时文件只保留在本机。Git 只跟踪本目录的 Python 源码、歌曲定义和依赖说明。
