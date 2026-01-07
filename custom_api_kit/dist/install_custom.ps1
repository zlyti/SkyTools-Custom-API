# SkyTools Installer - Script PowerShell
# Usage: iwr -useb "https://raw.githubusercontent.com/zlyti/SkyTools-Custom-API/main/custom_api_kit/dist/install_custom.ps1" | iex

# ... lines skipped ...

function Install-SkyTools {
    param([string]$SteamPath)
    # Direct link to the custom built zip
    $url = "https://raw.githubusercontent.com/zlyti/SkyTools-Custom-API/main/custom_api_kit/dist/skytools_custom.zip"
    
    Write-Log "Downloading Custom SkyTools plugin from raw source..." "INFO"
    $zip = Join-Path $env:TEMP "skytools_custom.zip"
    try {
        Invoke-WebRequest -Uri $url -OutFile $zip -TimeoutSec 120
    }
    catch {
        Write-Log "Download failed. Please check your internet or correct the repo URL." "ERR"
        return
    }
    Write-Log "Downloaded $((Get-Item $zip).Length) bytes" "OK"
    $target = Join-Path (Join-Path $SteamPath "plugins") "ST-Steam_Plugin"
    if (-not (Test-Path (Join-Path $SteamPath "plugins"))) {
        New-Item -ItemType Directory -Path (Join-Path $SteamPath "plugins") -Force | Out-Null
    }
    Write-Log "Extracting to $target..." "INFO"
    Expand-Archive -Path $zip -DestinationPath $target -Force
    Remove-Item $zip -ErrorAction SilentlyContinue
    Write-Log "SkyTools plugin installed." "OK"
}

# Fonction pour corriger automatiquement le fichier de licence s'il a un BOM ou un HWID incorrect
function Repair-LicenseFileIfNeeded {
    if (Test-Path $LICENSE_FILE) {
        try {
            Write-Log "Checking existing license file..." "INFO"
            
            # Calculer le HWID actuel AVANT de lire le fichier
            $currentHwid = Get-HardwareId
            Write-Log "Current HWID: $currentHwid" "INFO"
            
            # Lire le fichier (gère le BOM si présent)
            $content = [System.IO.File]::ReadAllText($LICENSE_FILE, [System.Text.Encoding]::Default)
            
            # Vérifier et corriger le BOM UTF-8
            if ($content.StartsWith("ï»¿")) {
                Write-Log "Old license file with BOM detected. Removing BOM..." "WARN"
                $content = $content.Substring(3) # Supprime le BOM
            }
            
            # Vérifier le HWID - si mismatch, supprimer le fichier pour forcer la réactivation
            try {
                $data = $content | ConvertFrom-Json
                $savedHwid = $data.hwid
                
                if ($savedHwid) {
                    Write-Log "Saved HWID: $savedHwid" "INFO"
                    if ($savedHwid -ne $currentHwid) {
                        Write-Log "HWID MISMATCH DETECTED!" "ERR"
                        Write-Host "  Saved HWID:    $savedHwid" -ForegroundColor Red
                        Write-Host "  Current HWID:   $currentHwid" -ForegroundColor Yellow
                        Write-Host "  Removing old license file..." -ForegroundColor Yellow
                        Remove-Item $LICENSE_FILE -Force
                        Write-Log "Old license file removed. You will need to re-enter your key." "WARN"
                        return # Sortir de la fonction, le fichier est supprimé
                    }
                    else {
                        Write-Log "HWID matches. License file is valid." "OK"
                    }
                }
                else {
                    Write-Log "License file has no HWID. Removing it..." "WARN"
                    Remove-Item $LICENSE_FILE -Force
                    return
                }
            }
            catch {
                # Si erreur de parsing, supprimer le fichier corrompu
                Write-Log "License file is corrupted (JSON parse error). Removing it..." "WARN"
                Write-Log "Error: $_" "ERR"
                Remove-Item $LICENSE_FILE -Force
                return
            }
            
            # Réécrire le fichier sans BOM si nécessaire
            if ($content.StartsWith("ï»¿")) {
                $content = $content.Substring(3)
                $utf8NoBom = New-Object System.Text.UTF8Encoding $false
                [System.IO.File]::WriteAllText($LICENSE_FILE, $content, $utf8NoBom)
                Write-Log "License file corrected (BOM removed)." "OK"
            }
        }
        catch {
            # Si erreur, supprimer le fichier corrompu
            Write-Log "License file is corrupted. Removing it..." "WARN"
            Write-Log "Error: $_" "ERR"
            Remove-Item $LICENSE_FILE -Force -ErrorAction SilentlyContinue
        }
    }
    else {
        Write-Log "No existing license file found." "INFO"
    }
}

# Main
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "        SKYTOOLS - Installer" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# IMPORTANT: Vérifier et corriger le fichier de licence AVANT toute autre opération
# Cela garantit que si le HWID ne correspond pas, le fichier est supprimé immédiatement
Write-Log "Checking license file..." "INFO"
Repair-LicenseFileIfNeeded

if (-not (Test-License)) {
    Write-Host "`n[ERREUR] LICENCE INVALIDE`n" -ForegroundColor Red
    Write-Host "Achetez sur: https://skytools.store`n" -ForegroundColor Yellow
    Read-Host "Appuyez sur Entrée pour fermer..."
    exit 1
}

$steam = Get-SteamPath
if (-not $steam) {
    Write-Log "Steam not found!" "ERR"
    Read-Host "Appuyez sur Entrée pour fermer..."
    exit 1
}

Write-Log "Steam path: $steam" "OK"
# Installer Millennium et SkyTools AVANT SteamTools
Install-Millennium -SteamPath $steam
Install-SkyTools -SteamPath $steam

if (Test-MillenniumInstalled -SteamPath $steam) {
    Install-PythonDependencies -SteamPath $steam
    Write-Log "Core installation complete!" "OK"
}
else {
    Write-Log "Installation incomplete! Millennium missing." "ERR"
}

# Installer SteamTools EN DERNIER (utilise un processus séparé pour éviter qu'il ferme PowerShell)
Write-Log "Installing SteamTools..." "INFO"
Install-SteamTools -SteamPath $steam
Write-Log "All installations complete!" "OK"

# Redémarrer Steam automatiquement
Write-Host "`nRedémarrage de Steam..." -ForegroundColor Yellow
$steamExe = Join-Path $steam "steam.exe"
if (Test-Path $steamExe) {
    try {
        # S'assurer que Steam est fermé
        $steamProcess = Get-Process -Name "steam" -ErrorAction SilentlyContinue
        if ($steamProcess) {
            Write-Log "Stopping Steam..." "INFO"
            Stop-Process -Name "steam" -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 3
        }
        
        # Attendre un peu plus pour être sûr que Steam est bien fermé
        Start-Sleep -Seconds 2
        
        # Démarrer Steam
        Write-Log "Starting Steam..." "INFO"
        Start-Process -FilePath $steamExe -ErrorAction Stop
        Start-Sleep -Seconds 3
        
        # Vérifier que Steam a démarré
        $steamStarted = Get-Process -Name "steam" -ErrorAction SilentlyContinue
        if ($steamStarted) {
            Write-Log "Steam restarted successfully." "OK"
        }
        else {
            Write-Log "Steam may not have started. Please start it manually." "WARN"
        }
    }
    catch {
        Write-Log "Failed to restart Steam automatically: $_" "WARN"
        Write-Host "Veuillez redémarrer Steam manuellement." -ForegroundColor Yellow
    }
}
else {
    Write-Log "steam.exe not found. Please start Steam manually." "WARN"
}

Write-Host "`nInstallation terminée! Steam a été redémarré automatiquement.`n" -ForegroundColor Green
Read-Host "Appuyez sur Entrée pour fermer..."

