# 安装包

构建产物保存在本地，不加入 Git 历史。仓库已包含运行和构建所需的歌曲、谱面及音色资源。

在仓库根目录安装开发依赖：

```sh
npm --prefix choir-studio ci
```

准备好平台工具后，在 Windows 上执行：

| 命令 | 应用目录产物 | 本目录分发副本 |
| --- | --- | --- |
| `npm --prefix choir-studio run build:windows` | `choir-studio/releases/ChoirStudio.exe` | `releases/和声练习室.exe` |
| `npm --prefix choir-studio run build:android` | `choir-studio/releases/choir-studio.apk` | `releases/和声练习室.apk` |

构建要求见 [应用说明](../choir-studio/README.md)。现有电脑上的安装包和 `archive/releases/` 中的历史版本均保留原位。

后续分发时，可将安装包及对应的 SHA-256 校验文件作为 GitHub Release 附件上传。安卓当前构建脚本生成调试签名 APK；更新现有安装时，还需保留对应的 Android 签名材料和电脑端 `.update-keys/` 更新密钥。
