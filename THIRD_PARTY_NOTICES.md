# 第三方材料

仓库保留随材料提供的许可和署名文件，位置如下：

| 材料 | 说明或许可文件 |
| --- | --- |
| Tone.js | `choir-studio/public/vendor/TONE-LICENSE.md` |
| @tonejs/midi | `choir-studio/public/vendor/MIDI-LICENSE.md` |
| midi-file | `choir-studio/public/vendor/MIDI-FILE-LICENSE.md` |
| array-flatten | `choir-studio/public/vendor/ARRAY-FLATTEN-LICENSE.txt` |
| 合唱与钢琴音色 | `choir-studio/public/samples/SOURCES.md` |
| Salamander Grand Piano 原始说明 | `choir-studio/public/samples/SALAMANDER-README.txt` |

JavaScript 开发依赖由 `choir-studio/package-lock.json` 记录；Capacitor、jsdom、Playwright 等依赖的许可证随各自软件包提供。

Python 和识谱工具包括 music21、PyMuPDF、Pillow、Audiveris；工具链不随 Git 仓库提交。Windows 构建按需下载微软 WebView2 SDK，其许可文件会随桌面资源打包。

原始乐谱、MIDI、识谱和修订材料保存在 `data/`，应用使用的谱面位于 `choir-studio/public/songs/`。这些音乐材料及音色各有其权利归属，仓库未为它们另行授予许可；原创代码的许可证由维护者另行确定。
