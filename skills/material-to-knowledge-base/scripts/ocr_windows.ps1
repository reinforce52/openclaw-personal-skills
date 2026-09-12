# OCR single PNG using Windows built-in OCR (zh-Hans-CN), print text to stdout.
#
# Usage:
#     powershell -ExecutionPolicy Bypass -File ocr_windows.ps1 -ImagePath <png> [-Lang zh-Hans-CN]
#
# Notes:
#   - Uses Windows 10/11 built-in Windows.Media.Ocr, no extra install needed.
#   - Pair with render_pdf.py: render PDF page to PNG first, then OCR per page.
#   - Low-quality lines should be marked "OCR 待校对" by the caller.
param(
    [Parameter(Mandatory=$true)][string]$ImagePath,
    [string]$Lang = "zh-Hans-CN"
)

$ErrorActionPreference = "Stop"

# ---- WinRT async helper ----
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
} | Select-Object -First 1

function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    return $netTask.Result
}

[Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime] | Out-Null

# ---- Open and decode image ----
$absPath = (Resolve-Path $ImagePath).Path
$file   = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($absPath)) ([Windows.Storage.StorageFile])
$stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

# ---- OCR engine (prefer requested lang, fallback to user profile langs) ----
$engine = $null
try {
    $langObj = New-Object Windows.Globalization.Language $Lang
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($langObj)
} catch {
    $engine = $null
}
if (-not $engine) {
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
}
if (-not $engine) {
    Write-Error "No OCR engine available (missing language pack?)"
    exit 1
}

$result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
$result.Lines | ForEach-Object { $_.Text }
