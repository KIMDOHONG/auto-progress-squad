param(
    [int]$Port = 8001
)

$ErrorActionPreference = "Stop"

$apiDirectory = Join-Path $PSScriptRoot "..\src\api"
$fastApiExecutable = Join-Path $apiDirectory ".venv\Scripts\fastapi.exe"

if (-not (Test-Path -LiteralPath $fastApiExecutable)) {
    throw "FastAPI 실행 파일을 찾지 못했습니다: $fastApiExecutable"
}

Write-Host "NAVER Maps 인증값은 이 실행 프로세스에만 적용되며 파일에 저장되지 않습니다."
$clientIdSecure = Read-Host "NAVER Client ID를 붙여 넣고 Enter" -AsSecureString
$clientSecretSecure = Read-Host "NAVER Client Secret을 붙여 넣고 Enter" -AsSecureString

$clientIdPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($clientIdSecure)
$clientSecretPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($clientSecretSecure)

try {
    $env:APS_NAVER_MAPS_CLIENT_ID = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($clientIdPointer)
    $env:APS_NAVER_MAPS_CLIENT_SECRET = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($clientSecretPointer)

    Write-Host "NAVER Maps가 연결된 로컬 백엔드를 http://127.0.0.1:$Port 에서 시작합니다."
    Push-Location $apiDirectory
    try {
        & $fastApiExecutable dev --host 127.0.0.1 --port $Port
    }
    finally {
        Pop-Location
    }
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($clientIdPointer)
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($clientSecretPointer)
    Remove-Item Env:APS_NAVER_MAPS_CLIENT_ID -ErrorAction SilentlyContinue
    Remove-Item Env:APS_NAVER_MAPS_CLIENT_SECRET -ErrorAction SilentlyContinue
}
