param([switch]$Help)

if ($Help) {
    Write-Host "Reversible Worker Config Toggle`n"
    Write-Host "Usage: .\toggle_worker_config.ps1`n"
    Write-Host "This script toggles between local-only and network worker modes."
    exit
}

$configPath = "config\worker.json"

if (-not (Test-Path $configPath)) {
    Write-Host "Error: worker.json not found at $configPath" -ForegroundColor Red
    exit 1
}

# Read current config
$config = Get-Content $configPath | ConvertFrom-Json
$currentHost = $config.manager_host

Write-Host "=== PulseCheck Worker Config Toggle ===" -ForegroundColor Cyan
Write-Host ""

if ($currentHost -eq "127.0.0.1") {
    Write-Host "Current mode: LOCAL ONLY (localhost)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  [1] Add network worker (enter manager IP)"
    Write-Host "  [2] Keep local-only"
    Write-Host ""
    $choice = Read-Host "Select (1 or 2)"
    
    if ($choice -eq "1") {
        $managerIP = Read-Host "Enter manager's IP address (e.g., 192.168.1.100)"
        
        # Validate IP
        if ($managerIP -match "^(\d{1,3}\.){3}\d{1,3}$") {
            $config.manager_host = $managerIP
            $config | ConvertTo-Json | Set-Content $configPath
            Write-Host ""
            Write-Host "✓ Updated! Manager host changed to: $managerIP" -ForegroundColor Green
            Write-Host "  Run this script again to revert to localhost" -ForegroundColor Gray
        } else {
            Write-Host "Invalid IP address format. Keeping current config." -ForegroundColor Red
        }
    } else {
        Write-Host "Keeping local-only configuration." -ForegroundColor Yellow
    }
} else {
    Write-Host "Current mode: NETWORK WORKER" -ForegroundColor Yellow
    Write-Host "Manager IP: $currentHost" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  [1] Revert to local-only (127.0.0.1)"
    Write-Host "  [2] Update to different IP"
    Write-Host "  [3] Keep current"
    Write-Host ""
    $choice = Read-Host "Select (1, 2, or 3)"
    
    if ($choice -eq "1") {
        $config.manager_host = "127.0.0.1"
        $config | ConvertTo-Json | Set-Content $configPath
        Write-Host ""
        Write-Host "✓ Reverted! Manager host changed to: 127.0.0.1" -ForegroundColor Green
        Write-Host "  Worker will only connect to local machine" -ForegroundColor Gray
    } elseif ($choice -eq "2") {
        $managerIP = Read-Host "Enter new manager IP address"
        if ($managerIP -match "^(\d{1,3}\.){3}\d{1,3}$") {
            $config.manager_host = $managerIP
            $config | ConvertTo-Json | Set-Content $configPath
            Write-Host ""
            Write-Host "✓ Updated! Manager host changed to: $managerIP" -ForegroundColor Green
        } else {
            Write-Host "Invalid IP address format. Keeping current config." -ForegroundColor Red
        }
    } else {
        Write-Host "Keeping current configuration." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Current config:"
$config | ConvertTo-Json | Write-Host -ForegroundColor Gray
Write-Host ""