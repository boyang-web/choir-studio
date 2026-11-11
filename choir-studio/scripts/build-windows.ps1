$ErrorActionPreference = 'Stop'
$projectDir = Split-Path $PSScriptRoot -Parent
$workspaceDir = Split-Path $projectDir -Parent
$buildDir = Join-Path $projectDir 'desktop/build'
& python (Join-Path $PSScriptRoot 'prepare-desktop.py')
if ($LASTEXITCODE -ne 0) { throw 'Desktop assets preparation failed.' }
$compiler = Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
$sdkDir = Join-Path $workspaceDir 'tools/webview2/lib/net462'
$exe = Join-Path $buildDir 'ChoirStudio.exe'
& $compiler /nologo /target:winexe /platform:x64 /optimize+ "/out:$exe" "/win32manifest:$projectDir/desktop/app.manifest" "/win32icon:$buildDir/choir.ico" "/resource:$buildDir/payload.zip,ChoirPayload" "/resource:$buildDir/choir.ico,ChoirIcon" /reference:System.dll /reference:System.Core.dll /reference:System.Drawing.dll /reference:System.Windows.Forms.dll /reference:System.IO.Compression.dll "/reference:$sdkDir/Microsoft.Web.WebView2.Core.dll" "/reference:$sdkDir/Microsoft.Web.WebView2.WinForms.dll" (Join-Path $projectDir 'desktop/Program.cs')
if ($LASTEXITCODE -ne 0) { throw 'Windows compilation failed.' }
New-Item -ItemType Directory -Force (Join-Path $projectDir 'releases') | Out-Null
Copy-Item -LiteralPath $exe -Destination (Join-Path $projectDir 'releases/ChoirStudio.exe') -Force
# Keep this script ASCII; construct the Chinese release filename without encoding assumptions.
$fileName = -join ([char[]]@(0x548c,0x58f0,0x7ec3,0x4e60,0x5ba4))
$releaseDir = Join-Path $workspaceDir 'releases'
New-Item -ItemType Directory -Force $releaseDir | Out-Null
Copy-Item -LiteralPath $exe -Destination (Join-Path $releaseDir ($fileName + '.exe')) -Force
Write-Output 'Windows EXE ready in workspace releases/ and project releases/ChoirStudio.exe'
