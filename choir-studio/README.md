# 和声 · 合唱练习室

当前版本 **1.8.0（2026-10-31）**：声部名称统一使用“女中音”。新增歌曲的试导入结果、识别问题和重试命令见 [新歌曲导入记录](../docs/新歌曲导入记录.md)。新歌尚未人工逐音校订，曲库中标为“试导入 · 待校订”。

安卓支持「局域网更新」及「离线传递给别人」。手机可从电脑接收更新，保存后离线使用；也可开启个人热点，将当前内容传给其他手机，接收方还能继续传递。完整步骤见 [手机局域网更新说明](../docs/手机局域网更新说明.md)。

1.5.2（2026-10-29）已修复《敕勒歌》男低第 26、29、67 小节的漏音和错拍；按原 PDF 核对男低全部 69 小节的音高、发声时段及休止。修正保留在当前版本中。

电脑和手机浏览器均可使用的本地合唱学习软件。已有《敕勒歌》和《Let It Go》，新歌按试导入状态单独记录。原始 PDF 集中在上一级的 `data/sources/`。


## 打开软件

Windows 构建后可直接双击根目录的 `releases/和声练习室.exe`。安装包保存在本地，未纳入源码仓库，输出位置见 [安装包说明](../releases/README.md)。单文件包含曲库、谱面和音色，使用系统 WebView2 独立窗口，不需要 Node.js 或电脑启动服务。首次启动将资源释放到当前用户的 `%LOCALAPPDATA%/HeshengChoir`；浏览器资料与练习设置也保存在该目录。支持 Windows 10/11 x64，需要微软 WebView2 Runtime。

双击 **启动练习室.bat**，浏览器会自动打开。也可在此目录运行：

```sh
npm start
```

电脑访问 **http://localhost:5173**。运行只需 Node.js 22 或更新版本，**无需 npm install，无需联网**。

手机和电脑连接同一 Wi-Fi，在手机浏览器中打开启动窗口显示的局域网地址。请保持电脑上的启动窗口开启。如果系统询问防火墙访问权限，允许专用网络访问。手机首次播放需点击播放按钮。

## 练习方法

- 选择曲目，点击播放；蓝色游标按实际音频输出时钟移动，自动滚动到当前谱表。
- 每个声部均可独立开关、调音量；“独听”只保留选中的声部，再次点击恢复全声部。
- 已识别的分声部可分别选择，例如《Let It Go》的男低音 1 / 2。齐唱段落共用，不重复叠加。
- 控制台可选择声部、独听和音量；音色按声部固定，女声用女声音色、男声用男声音色、钢琴用钢琴音色。保留“全部开启”“全部静音”。“力度变化”播放 MusicXML 中已识别的力度记号。
- 总音量支持 0%–400%，手机与电脑都在控制台调节。100% 为原来的单位增益，400% 约增加 12dB；默认仍为 70%。输出端有限幅及软峰值保护。
- 点击谱面小节，或拖动底部进度条定位。左右按钮按小节跳转。
- 速度支持 0.5×—1.25×，改变速度保持音高。
- 输入起止小节并开启“重复练习此段”，循环练习选段。
- 手机左上角打开曲库，右上方打开声部与设置。谱面严格保留原 PDF 整页排版，不切分小节、不重新换行。双指缩放或 + / − 调整到 25%–400%，放大后可上下左右拖动；“适合宽度”恢复整页宽度。缩放以手势中心为锚点，保留查看位置。电脑也支持 Ctrl+滚轮。
- “下载乐谱”可下载原文件；安卓内置相同的原谱资源。
- 电脑空格播放/暂停，方向键切换小节。声部音量和练习速度会记在当前设备的浏览器中。

## 曲库与录入状态

| 曲目 | 原谱 | 练习声部 | 时间轴 |
|---|---|---|---|
| 敕勒歌 | 10 页，新修订版，完整 | 女高音、女中音、男高音、男低音、陶笛、钢琴 | 69 个谱面小节，无弱起，约 4:07 |
| Let It Go | 19 页，完整 | 女高音、女中音、男高音、男低音、人声打击乐、钢琴 | 119 小节，约 3:21 |

**所有声部从标准 MIDI 的音符事件与速度信息确定时间。** 导入链为 Audiveris → MusicXML → music21 → `performance.mid`，运行时用 @tonejs/midi 解析。四分、八分等时值、休止、附点与连音先组成节拍，再生成 MIDI ticks；谱面横坐标不参与音符时刻计算。Let It Go 的声乐有 19 处小节识别节奏修复；口技补识原 PDF 的符头、符杠、符尾与休止，并按有理数累计时值，69 个口技小节均满足每小节拍数。361 个口技事件保留同拍不同声层，末尾三个全音符风声连成一个长音。发声口技单独提高音量和中频清晰度。

声音采用男女人声元音、钢琴采样与合成口技，并非整首真人演唱录音。相邻人声短音连续使用同一元音，内部以 22.05 kHz 单声道播放以降低手机负担。音色许可集中在控制台折叠的“关于”；识谱与开发说明只保留在文档。

1.5 使用新版 PDF 重新识谱，未沿用旧版小节修正规则。对照新版修正了装饰音误算时值、拍号误识为音符、钢琴跨谱表及密集连音等问题；音符超拍审计为 0。第 42 小节按两组九连音加八个普通三十二分音符处理，第 43、44 小节恢复跨谱表连音，第 61–64 小节核对六/五连音及倚音。倚音从相邻主音借时，小节拍数保持不变。游标仍采用 MIDI 音乐偏移与符头对应的定位点及单调三次插值，插值只用于显示。

**识别结果尚未全部人工逐音校订。** 当前仍记录《Let It Go》11 个钢琴音符的跨小节识别异常，未通过压缩时值掩盖。原始 MusicXML、审计 JSON 和生成的 MIDI 均保留，供 MuseScore 等软件继续校订。其他未确认的装饰音、音高、自由延长和渐慢也可能有差异。当前使用谱首速度，游标与练习音轨同步，不代表与外部演唱录音同步。

## 社区方案与技术取舍

| 功能 | 复用方案 | 用途与取舍 |
|---|---|---|
| PDF 乐谱识别 | [Audiveris 5.11.0](https://github.com/Audiveris/audiveris) | 离线识别、输出标准 MusicXML；不在浏览器重复实现 OMR |
| MusicXML 读取 | [music21 10.5.1](https://www.music21.org/music21docs/) | 导入时解析音符、和弦、声部和时值；运行时无需 Python |
| MIDI 时间轴 | [music21 MIDI](https://music21.org/music21docs/moduleReference/moduleMidiBase.html)、[@tonejs/midi 2.0.28](https://github.com/Tonejs/Midi) | music21 写出 SMF；MIDI 回读验证事件，应用直接读取 MIDI tempo/ticks。解析器及其 midi-file/array-flatten 许可均本地打包 |
| 声音、变速、循环、节拍器 | [Tone.js 15.1.22](https://tonejs.github.io/) | Transport 统一时钟，原生 Web Audio 播放采样，Tone 合成口技与节拍器，Gain 独立混音 |
| 人声与钢琴 | [Virtual Playing Orchestra](https://virtualplaying.com/virtual-playing-orchestra/)、[Salamander Grand Piano](https://github.com/Tonejs/audio/tree/master/salamander) | 男女人声循环采样、Alexander Holm 钢琴；本地内置，署名和许可见 `public/samples/SOURCES.md` |
| 谱面方案调研 | [OpenSheetMusicDisplay](https://github.com/opensheetmusicdisplay/opensheetmusicdisplay)、[PyMuPDF](https://pymupdf.readthedocs.io/) | 已评估 MusicXML 重排；当前显示完整原 PDF 页，保留原始版式，支持双指缩放 |
| 响应式界面 | CSS Grid / Flex 与浏览器原生控件 | 无框架运行依赖，便于离线运行和静态部署 |
| 验证 | Node Test Runner、jsdom、Playwright | 数据一致性、时间轴与界面集成；真实浏览器验收脚本单独提供 |

Tone.js 已打包到 `public/vendor`，许可见同目录的 `TONE-LICENSE.md`。导入工具不与网页运行时耦合。

## 开发与验证

### 安卓安装版

安卓工程采用 [Capacitor 7](https://capacitorjs.com/docs/v7/android)，当前曲库、MIDI、全部采样和谱面资源均内置，安装后可以离线练习。APK 为签名调试构建，仍需在用户手机上复验。

安装文件位于 `releases/choir-studio.apk`。也可以在电脑启动练习室后，用手机访问 `http://电脑局域网IP:5173/download/choir-studio.apk` 下载。安装时，按手机提示允许当前浏览器安装该 APK。

重新构建需要 JDK 21、Android SDK platform 35 / build-tools 35.0.0，以及 Node.js。当前工作区已准备构建工具，运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build-android.ps1
```

若在其他电脑构建，先 `npm ci`，设置 `JAVA_HOME` 和 `ANDROID_HOME`。也可使用 Android Studio 打开 `android` 目录构建。构建脚本会生成本机更新签名及内置更新清单；密钥和这些生成文件不纳入 Git。现有手机信任的更新密钥需要单独迁移，详见 [手机局域网更新说明](../docs/手机局域网更新说明.md)。

### 网页验证

```sh
npm ci
npm test
# 另一个终端先 npm start，再执行：
npm run test:browser
node tests/audio-browser.mjs
node tests/performance-browser.mjs
node tests/zoom-browser.mjs
node tests/tail-audio-browser.mjs
node tests/reported-browser.mjs
node tests/volume-browser.mjs
```

如未安装 Playwright 浏览器，运行 `npx playwright install chromium`，或设置 `CHROME_PATH` 为本机 Chrome 可执行文件路径。也支持 `CDP_URL` 连接专用测试浏览器。

1.5 已通过 22 项数据、音频调度及 DOM 检查，并验证两类安装包所含资源一致。1.4 的真实浏览器和 WebView2 验收结果属于历史记录；当前环境阻止 Chrome 创建所需进程通信通道，本次未能重跑真实浏览器播放与触摸验收。详细结果和限制见 `VALIDATION.md`。这些检查不等于逐音人工校订或安卓设备听感验收。

### Windows 构建

运行 `npm run build:windows`（也可直接执行 `scripts/build-windows.ps1`）。复用微软官方 [WebView2](https://learn.microsoft.com/microsoft-edge/webview2/) SDK，使用 Windows 内置 .NET Framework 编译器；Python/Pillow 负责资源与图标打包，Python 依赖见 [工具说明](../tools/README.md)。构建脚本会按需下载官方 SDK，随后生成仓库根目录的 `releases/和声练习室.exe` 和应用目录的 `releases/ChoirStudio.exe`。SDK 许可内置于 EXE 资源，运行时解压到应用资源目录。

## 文件结构

```text
public/               可直接部署的静态应用
  app.js              界面、声部控制、谱面游标
  audio-engine.js     Tone.js 播放适配层
  score-utils.js      时间轴、小节定位与循环边界
  songs/              当前曲库的 PDF、MusicXML、音符数据、原谱图像
  vendor/             本地 Tone.js 和许可证
server.mjs            无依赖静态服务，支持局域网访问
tests/                自动化验证
```

上一级 `tools/import_scores.py` 是可重复的数据生成入口，依赖 PyMuPDF、Pillow 和 music21；`tools/fix_parts.py` 保存了本次声部映射校正。`data/omr` 保留 Audiveris 识别工程和标准 MusicXML，供后续校订。重新导出后的 MusicXML 可由同一导入入口生成曲库。

最终音频数据入口为 `python tools/build_performance.py`（从工作区根目录执行）。它读取 MusicXML、修复可核对的印刷时值、生成两首歌的 `performance.mid` 并回读成音符元数据。`tools/read_vp_rhythm.py` 只识别符号及其关联，不从横坐标推算时间。重新导入、修改识谱源或力度后，应最后重新运行此 MIDI 构建步骤。

新版《敕勒歌》的数据入口为 `tools/update_chile_score.py`。已保留识谱工程时，运行 `python tools/update_chile_score.py --generate-only` 可重建谱面与播放数据。`tools/new_score_symbols.py` 保存新版的符号核对和节奏修正；`data/revisions/2026-10-26/chi-le-ge-playback.mxl` 与应用内 `score.mxl` 为修正后的可编辑 MusicXML。原始 Audiveris 导出仍保留在该修订目录的 `omr` 子目录。

本版范围为曲库、跟谱与分声部练习。无账号、录音评分、付费或后台管理。
