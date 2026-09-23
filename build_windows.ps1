param([switch]$Clean)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$dist = Join-Path $projectRoot "dist"
$work = Join-Path $projectRoot "build"
$settingsExample = Join-Path $projectRoot "settings.example.ini"

if (-not (Test-Path -LiteralPath $python)) {
    throw "The virtual environment is missing. Create .venv and install requirements first."
}

& $python -m PyInstaller --version
if ($LASTEXITCODE -ne 0) { throw "PyInstaller is not installed. Run: .\\.venv\\Scripts\\python.exe -m pip install pyinstaller" }

if ($Clean) {
    Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $dist -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $projectRoot "CorporateScraper.spec") -Force -ErrorAction SilentlyContinue
}

& $python -m PyInstaller --noconfirm --clean --windowed --onefile `
    --name CorporateScraper `
    --workpath $work `
    --specpath $work `
    --add-data "$settingsExample;." `
    (Join-Path $projectRoot "run_desktop.py")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

# A one-file build only needs the executable in dist. PyInstaller's analysis
# cache and generated spec are build-time artifacts, so remove them on success.
Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
Write-Output "Created $dist\CorporateScraper.exe"
