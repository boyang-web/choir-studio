$ErrorActionPreference = 'Stop'
$projectDir = Split-Path $PSScriptRoot -Parent
$workspaceDir = Split-Path $projectDir -Parent
$toolDir = Join-Path $workspaceDir 'tools'
if (-not $env:JAVA_HOME) {
    $localJdk = Get-ChildItem (Join-Path $toolDir 'java21') -Directory -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($localJdk) { $env:JAVA_HOME = $localJdk.FullName }
}
if (-not $env:JAVA_HOME) { throw 'JAVA_HOME must point to JDK 21.' }
if (-not $env:ANDROID_HOME -and (Test-Path (Join-Path $toolDir 'android-sdk'))) {
    $env:ANDROID_HOME = Join-Path $toolDir 'android-sdk'
}
if (-not $env:ANDROID_HOME) { throw 'Set ANDROID_HOME to an Android SDK with platform 35 and build-tools 35.0.0.' }
$env:GRADLE_USER_HOME = Join-Path $toolDir 'gradle-home'
$env:ANDROID_USER_HOME = Join-Path $toolDir 'android-state'
$taskUserHome = Join-Path $toolDir 'java-home'
$sdkDir = $env:ANDROID_HOME.Replace('\','/')
$sdkDir = [regex]::Replace($sdkDir, '[^\x00-\x7F]', { param($m) '\u' + ([int][char]$m.Value).ToString('x4') })
[IO.File]::WriteAllText((Join-Path $projectDir 'android/local.properties'), "sdk.dir=$sdkDir`n", [Text.Encoding]::ASCII)
Push-Location $projectDir
try {
    & node 'scripts/prepare-local-updates.mjs'
    if ($LASTEXITCODE -ne 0) { throw 'Local update key preparation failed.' }
    & node 'node_modules/@capacitor/cli/bin/capacitor' sync android
    if ($LASTEXITCODE -ne 0) { throw 'Capacitor sync failed.' }
    $localGradle = Join-Path $toolDir 'gradle-8.11.1/bin/gradle.bat'
    if (-not (Test-Path $localGradle)) { $localGradle = Join-Path $projectDir 'android/gradlew.bat' }
    & $localGradle -p (Join-Path $projectDir 'android') assembleDebug --no-daemon "-Duser.home=$taskUserHome" --console=plain
    if ($LASTEXITCODE -ne 0) { throw 'Android build failed.' }
    New-Item -ItemType Directory -Force (Join-Path $projectDir 'releases') | Out-Null
    Copy-Item -LiteralPath (Join-Path $projectDir 'android/app/build/outputs/apk/debug/app-debug.apk') -Destination (Join-Path $projectDir 'releases/choir-studio.apk') -Force
    $releaseDir = Join-Path $workspaceDir 'releases'
    New-Item -ItemType Directory -Force $releaseDir | Out-Null
    $fileName = -join ([char[]]@(0x548c,0x58f0,0x7ec3,0x4e60,0x5ba4))
    Copy-Item -LiteralPath (Join-Path $projectDir 'releases/choir-studio.apk') -Destination (Join-Path $releaseDir ($fileName + '.apk')) -Force
    Write-Output 'APK ready: releases/choir-studio.apk'
} finally { Pop-Location }
