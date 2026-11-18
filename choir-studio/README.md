# 合唱练习室应用

版本 1.9.0，运行方式、曲库状态及下载入口见 [仓库首页](../README.md)。
本版新增《回声》双合唱队八声部，并删除局域网更新和手机转发。

## 验证

在本目录执行 `npm ci`、`npm test`。启动 `node server.mjs` 后，
执行 `npm run test:browser`、`node tests/hui-sheng-browser.mjs`。
macOS 安装依赖后可运行 `node tests/macos-smoke.mjs` 验证原生宿主；
`ELECTRON_PATH` 可指定构建后应用的 `Contents/MacOS/和声练习室`。

## macOS

```sh
cd macos
npm ci
npm run build
```

产物在 `choir-studio/releases/macos/`。构建未使用开发者证书，不包含 Apple 公证。

## Windows

Windows 上安装 Python 3.12 和 Pillow，执行：

```powershell
npm run build:windows
```

使用系统 .NET Framework 编译器和 WebView2 SDK，输出 `releases/ChoirStudio.exe`。
使用时电脑需要 WebView2 Runtime。

## Android

使用 JDK 21、Android SDK 35，先 `npm ci`，然后执行：

```powershell
npm run build:android
```

也可在本目录运行 `npx cap sync android`，然后在 `android` 目录执行 `./gradlew assembleDebug`。
本版使用新的调试签名。用户已确认可以重新安装；不同签名无法覆盖旧版。
再次发布如需覆盖安装，应保留同一签名密钥或另行配置正式发布签名。

## 发布

`.github/workflows/release.yml` 构建 macOS arm64/x64 DMG、Windows EXE 和 Android APK。
先通过 Node 测试和原 PDF 符头审计，再构建；所有目标成功后，带 `[release]` 的提交发布 v1.9.0。
安装包包含当前完整曲库与音色，不从其他电脑或手机接收资源更新。

历史验证记录保留在 `VALIDATION.md`，其中 1.6/1.7 的局域网功能仅代表历史版本。
《回声》核验依据见 [核验记录](../docs/回声核验记录.md)。
