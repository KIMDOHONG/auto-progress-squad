param(
    [ValidateRange(1, 65535)]
    [int]$ApiPort = 8000,
    [ValidateRange(1, 65535)]
    [int]$WebPort = 5173,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$projectDirectory = Resolve-Path (Join-Path $PSScriptRoot "..")
$apiDirectory = Join-Path $projectDirectory "src\api"
$webDirectory = Join-Path $projectDirectory "src\web"
$uvicornExecutable = Join-Path $apiDirectory ".venv\Scripts\uvicorn.exe"
$viteEntrypoint = Join-Path $webDirectory "node_modules\vite\bin\vite.js"
$viteRelativeEntrypoint = "node_modules\vite\bin\vite.js"
$nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
$nodeCandidates = @()
if ($nodeCommand) { $nodeCandidates += $nodeCommand.Source }
if ($env:ProgramFiles) { $nodeCandidates += (Join-Path $env:ProgramFiles "nodejs\node.exe") }
if (${env:ProgramFiles(x86)}) { $nodeCandidates += (Join-Path ${env:ProgramFiles(x86)} "nodejs\node.exe") }
if ($env:LOCALAPPDATA) { $nodeCandidates += (Join-Path $env:LOCALAPPDATA "Programs\nodejs\node.exe") }
if ($env:USERPROFILE) {
    $nodeCandidates += (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe")
}
$nodeExecutable = $nodeCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

if (-not (Test-Path -LiteralPath $uvicornExecutable)) {
    throw "백엔드 실행 파일이 없습니다. 먼저 README의 백엔드 설치 단계를 실행해 주세요: $uvicornExecutable"
}
if (-not $nodeExecutable) {
    throw "Node.js를 찾지 못했습니다. Node.js를 설치하거나 Codex 데스크톱 앱에서 이 저장소를 다시 연 뒤 실행해 주세요."
}
if (-not (Test-Path -LiteralPath $viteEntrypoint)) {
    throw "프런트엔드 의존성이 없습니다. src/web에서 pnpm install을 먼저 실행해 주세요."
}

function Assert-PortAvailable([int]$Port, [string]$ServiceName) {
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($listener) {
        throw "$ServiceName 포트 $Port가 이미 사용 중입니다(PID $($listener.OwningProcess)). 기존 개발 서버를 종료한 뒤 다시 실행해 주세요."
    }
}

function Wait-HttpEndpoint([string]$Url, [System.Diagnostics.Process]$Process, [string]$ServiceName) {
    $deadline = [DateTime]::UtcNow.AddSeconds(20)
    while ([DateTime]::UtcNow -lt $deadline) {
        $Process.Refresh()
        if ($Process.HasExited) {
            throw "$ServiceName 프로세스가 시작 중 종료되었습니다."
        }
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return
            }
        }
        catch {
            Start-Sleep -Milliseconds 350
        }
    }
    throw "$ServiceName 시작을 20초 안에 확인하지 못했습니다: $Url"
}

if ($ApiPort -eq $WebPort) {
    throw "API 포트와 웹 포트는 서로 달라야 합니다."
}

Assert-PortAvailable -Port $ApiPort -ServiceName "FastAPI"
Assert-PortAvailable -Port $WebPort -ServiceName "Vite"

$originalClientId = [Environment]::GetEnvironmentVariable("APS_NAVER_MAPS_CLIENT_ID", "Process")
$originalClientSecret = [Environment]::GetEnvironmentVariable("APS_NAVER_MAPS_CLIENT_SECRET", "Process")
$originalEvChargerServiceKey = [Environment]::GetEnvironmentVariable("APS_EV_CHARGER_SERVICE_KEY", "Process")
$originalHydrogenStationServiceKey = [Environment]::GetEnvironmentVariable("APS_HYDROGEN_STATION_SERVICE_KEY", "Process")
$originalOpinetServiceKey = [Environment]::GetEnvironmentVariable("APS_OPINET_SERVICE_KEY", "Process")
$originalApiBaseUrl = [Environment]::GetEnvironmentVariable("VITE_API_BASE_URL", "Process")
$originalCorsOrigins = [Environment]::GetEnvironmentVariable("APS_CORS_ORIGINS", "Process")
$clientIdValue = $originalClientId
$clientSecretValue = $originalClientSecret
$evChargerServiceKeyValue = $originalEvChargerServiceKey
$hydrogenStationServiceKeyValue = $originalHydrogenStationServiceKey
$opinetServiceKeyValue = $originalOpinetServiceKey
$clientIdPointer = [IntPtr]::Zero
$clientSecretPointer = [IntPtr]::Zero
$evChargerServiceKeyPointer = [IntPtr]::Zero
$hydrogenStationServiceKeyPointer = [IntPtr]::Zero
$opinetServiceKeyPointer = [IntPtr]::Zero
$apiProcess = $null
$webProcess = $null

try {
    if ([string]::IsNullOrWhiteSpace($clientIdValue) -and [string]::IsNullOrWhiteSpace($clientSecretValue)) {
        Write-Host "NAVER Maps 인증값은 자식 백엔드 프로세스에만 전달되며 파일에 저장되지 않습니다."
        $clientIdSecure = Read-Host "NAVER Client ID를 붙여 넣고 Enter" -AsSecureString
        $clientSecretSecure = Read-Host "NAVER Client Secret을 붙여 넣고 Enter" -AsSecureString
        $clientIdPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($clientIdSecure)
        $clientSecretPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($clientSecretSecure)
        $clientIdValue = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($clientIdPointer)
        $clientSecretValue = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($clientSecretPointer)
    }
    elseif ([string]::IsNullOrWhiteSpace($clientIdValue) -or [string]::IsNullOrWhiteSpace($clientSecretValue)) {
        throw "NAVER Client ID와 Client Secret은 둘 다 설정하거나 둘 다 비워야 합니다."
    }

    if ([string]::IsNullOrWhiteSpace($evChargerServiceKeyValue)) {
        Write-Host "전기차 충전소 공공데이터 서비스키도 파일에 저장하지 않고 자식 백엔드에만 전달합니다."
        $evChargerServiceKeySecure = Read-Host "공공데이터포털 서비스키를 붙여 넣거나 아직 없으면 Enter" -AsSecureString
        $evChargerServiceKeyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($evChargerServiceKeySecure)
        $evChargerServiceKeyValue = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($evChargerServiceKeyPointer)
    }

    if ([string]::IsNullOrWhiteSpace($hydrogenStationServiceKeyValue)) {
        Write-Host "수소충전소 운영정보와 실시간정보 활용신청이 모두 승인된 경우에만 입력해 주세요."
        $hydrogenStationServiceKeySecure = Read-Host "수소충전소 공공데이터 서비스키를 붙여 넣거나 아직 없으면 Enter" -AsSecureString
        $hydrogenStationServiceKeyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($hydrogenStationServiceKeySecure)
        $hydrogenStationServiceKeyValue = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($hydrogenStationServiceKeyPointer)
    }

    if ([string]::IsNullOrWhiteSpace($opinetServiceKeyValue)) {
        Write-Host "오피넷 인증키도 파일에 저장하지 않고 자식 백엔드에만 전달합니다."
        $opinetServiceKeySecure = Read-Host "오피넷 인증키를 붙여 넣거나 아직 없으면 Enter" -AsSecureString
        $opinetServiceKeyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($opinetServiceKeySecure)
        $opinetServiceKeyValue = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($opinetServiceKeyPointer)
    }

    $env:APS_NAVER_MAPS_CLIENT_ID = $clientIdValue
    $env:APS_NAVER_MAPS_CLIENT_SECRET = $clientSecretValue
    if ([string]::IsNullOrWhiteSpace($evChargerServiceKeyValue)) {
        Remove-Item Env:APS_EV_CHARGER_SERVICE_KEY -ErrorAction SilentlyContinue
    }
    else {
        $env:APS_EV_CHARGER_SERVICE_KEY = $evChargerServiceKeyValue
    }
    if ([string]::IsNullOrWhiteSpace($hydrogenStationServiceKeyValue)) {
        Remove-Item Env:APS_HYDROGEN_STATION_SERVICE_KEY -ErrorAction SilentlyContinue
    }
    else {
        $env:APS_HYDROGEN_STATION_SERVICE_KEY = $hydrogenStationServiceKeyValue
    }
    if ([string]::IsNullOrWhiteSpace($opinetServiceKeyValue)) {
        Remove-Item Env:APS_OPINET_SERVICE_KEY -ErrorAction SilentlyContinue
    }
    else {
        $env:APS_OPINET_SERVICE_KEY = $opinetServiceKeyValue
    }
    $env:VITE_API_BASE_URL = "http://127.0.0.1:$ApiPort"
    $configuredCorsOrigins = @(
        if ($originalCorsOrigins) { $originalCorsOrigins.Split(",", [StringSplitOptions]::RemoveEmptyEntries) }
        "http://127.0.0.1:$WebPort"
        "http://localhost:$WebPort"
    ) | ForEach-Object { $_.Trim() } | Where-Object { $_ } | Select-Object -Unique
    $env:APS_CORS_ORIGINS = $configuredCorsOrigins -join ","

    $runId = [Guid]::NewGuid().ToString("N")
    $apiOutputLog = Join-Path ([IO.Path]::GetTempPath()) "auto-progress-api-$runId.log"
    $apiErrorLog = Join-Path ([IO.Path]::GetTempPath()) "auto-progress-api-$runId.error.log"
    $webOutputLog = Join-Path ([IO.Path]::GetTempPath()) "auto-progress-web-$runId.log"
    $webErrorLog = Join-Path ([IO.Path]::GetTempPath()) "auto-progress-web-$runId.error.log"

    $apiProcess = Start-Process -FilePath $uvicornExecutable `
        -ArgumentList @("app.main:app", "--host", "127.0.0.1", "--port", "$ApiPort") `
        -WorkingDirectory $apiDirectory -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $apiOutputLog -RedirectStandardError $apiErrorLog

    $webProcess = Start-Process -FilePath $nodeExecutable `
        -ArgumentList @($viteRelativeEntrypoint, "--host", "127.0.0.1", "--port", "$WebPort", "--strictPort") `
        -WorkingDirectory $webDirectory -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $webOutputLog -RedirectStandardError $webErrorLog

    # Plain-text copies are no longer needed after both child processes inherit their environment.
    $clientIdValue = $null
    $clientSecretValue = $null
    $evChargerServiceKeyValue = $null
    $hydrogenStationServiceKeyValue = $null
    $opinetServiceKeyValue = $null
    if ($originalClientId) { $env:APS_NAVER_MAPS_CLIENT_ID = $originalClientId } else { Remove-Item Env:APS_NAVER_MAPS_CLIENT_ID -ErrorAction SilentlyContinue }
    if ($originalClientSecret) { $env:APS_NAVER_MAPS_CLIENT_SECRET = $originalClientSecret } else { Remove-Item Env:APS_NAVER_MAPS_CLIENT_SECRET -ErrorAction SilentlyContinue }
    if ($originalEvChargerServiceKey) { $env:APS_EV_CHARGER_SERVICE_KEY = $originalEvChargerServiceKey } else { Remove-Item Env:APS_EV_CHARGER_SERVICE_KEY -ErrorAction SilentlyContinue }
    if ($originalHydrogenStationServiceKey) { $env:APS_HYDROGEN_STATION_SERVICE_KEY = $originalHydrogenStationServiceKey } else { Remove-Item Env:APS_HYDROGEN_STATION_SERVICE_KEY -ErrorAction SilentlyContinue }
    if ($originalOpinetServiceKey) { $env:APS_OPINET_SERVICE_KEY = $originalOpinetServiceKey } else { Remove-Item Env:APS_OPINET_SERVICE_KEY -ErrorAction SilentlyContinue }
    if ($originalCorsOrigins) { $env:APS_CORS_ORIGINS = $originalCorsOrigins } else { Remove-Item Env:APS_CORS_ORIGINS -ErrorAction SilentlyContinue }

    $webUrl = "http://127.0.0.1:$WebPort/auto-progress-squad/"
    Wait-HttpEndpoint -Url "http://127.0.0.1:$ApiPort/api/v1/health" -Process $apiProcess -ServiceName "FastAPI"
    Wait-HttpEndpoint -Url $webUrl -Process $webProcess -ServiceName "Vite"

    Write-Host ""
    Write-Host "로컬 앱이 준비되었습니다: $webUrl" -ForegroundColor Green
    Write-Host "상단 배지가 'SQLite 동기화'인지 확인해 주세요."
    Write-Host "종료하려면 이 창에서 Ctrl+C를 누르세요."
    Write-Host "로그: $apiOutputLog / $apiErrorLog / $webOutputLog / $webErrorLog"
    if (-not $NoBrowser) {
        Start-Process $webUrl
    }

    while ($true) {
        Start-Sleep -Milliseconds 750
        $apiProcess.Refresh()
        $webProcess.Refresh()
        if ($apiProcess.HasExited) { throw "FastAPI가 예기치 않게 종료되었습니다. 오류 로그: $apiErrorLog" }
        if ($webProcess.HasExited) { throw "Vite가 예기치 않게 종료되었습니다. 오류 로그: $webErrorLog" }
    }
}
finally {
    if ($webProcess -and -not $webProcess.HasExited) { Stop-Process -Id $webProcess.Id -Force -ErrorAction SilentlyContinue }
    if ($apiProcess -and -not $apiProcess.HasExited) { Stop-Process -Id $apiProcess.Id -Force -ErrorAction SilentlyContinue }
    if ($clientIdPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($clientIdPointer) }
    if ($clientSecretPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($clientSecretPointer) }
    if ($evChargerServiceKeyPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($evChargerServiceKeyPointer) }
    if ($hydrogenStationServiceKeyPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($hydrogenStationServiceKeyPointer) }
    if ($opinetServiceKeyPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($opinetServiceKeyPointer) }
    if ($originalClientId) { $env:APS_NAVER_MAPS_CLIENT_ID = $originalClientId } else { Remove-Item Env:APS_NAVER_MAPS_CLIENT_ID -ErrorAction SilentlyContinue }
    if ($originalClientSecret) { $env:APS_NAVER_MAPS_CLIENT_SECRET = $originalClientSecret } else { Remove-Item Env:APS_NAVER_MAPS_CLIENT_SECRET -ErrorAction SilentlyContinue }
    if ($originalEvChargerServiceKey) { $env:APS_EV_CHARGER_SERVICE_KEY = $originalEvChargerServiceKey } else { Remove-Item Env:APS_EV_CHARGER_SERVICE_KEY -ErrorAction SilentlyContinue }
    if ($originalHydrogenStationServiceKey) { $env:APS_HYDROGEN_STATION_SERVICE_KEY = $originalHydrogenStationServiceKey } else { Remove-Item Env:APS_HYDROGEN_STATION_SERVICE_KEY -ErrorAction SilentlyContinue }
    if ($originalOpinetServiceKey) { $env:APS_OPINET_SERVICE_KEY = $originalOpinetServiceKey } else { Remove-Item Env:APS_OPINET_SERVICE_KEY -ErrorAction SilentlyContinue }
    if ($originalApiBaseUrl) { $env:VITE_API_BASE_URL = $originalApiBaseUrl } else { Remove-Item Env:VITE_API_BASE_URL -ErrorAction SilentlyContinue }
    if ($originalCorsOrigins) { $env:APS_CORS_ORIGINS = $originalCorsOrigins } else { Remove-Item Env:APS_CORS_ORIGINS -ErrorAction SilentlyContinue }
}
