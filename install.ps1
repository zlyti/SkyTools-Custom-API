# SkyTools Installer - Script PowerShell
# Usage: iwr -useb "https://votre-url.com/install.ps1" | iex

$LICENSE_API_URL = "https://skytools-license.skytoolskey.workers.dev"
$LICENSE_FILE = "$env:USERPROFILE\.skytools_license"
$GITHUB_API = "https://api.github.com"
$SKYTOOLS_REPO = "zlyti/skytools-download"
$SKYTOOLS_ASSET = "skytools-steam-plugin.zip"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $ts = Get-Date -Format "HH:mm:ss"
    $badge = switch ($Level) { "OK" { " OK " } "WARN" { "WARN" } "ERR" { "ERR " } default { "INFO" } }
    $color = switch ($Level) { "OK" { "Green" } "WARN" { "Yellow" } "ERR" { "Red" } default { "Cyan" } }
    Write-Host "[$ts] [$badge] $Message" -ForegroundColor $color
}

function Get-SteamPath {
    try {
        $path = (Get-ItemProperty "HKCU:\Software\Valve\Steam" -Name "SteamPath" -ErrorAction SilentlyContinue).SteamPath
        if (-not $path) { $path = (Get-ItemProperty "HKLM:\Software\WOW6432Node\Valve\Steam" -Name "InstallPath" -ErrorAction SilentlyContinue).InstallPath }
        if ($path) { return (Resolve-Path $path).Path }
    }
    catch {}
    return $null
}

function Get-HardwareId {
    try {
        # Utiliser Python pour calculer le HWID exactement comme le plugin
        # Créer un script Python temporaire pour garantir le même calcul
        $tempScript = Join-Path $env:TEMP "get_hwid_$(Get-Random).py"
        $pythonCode = @"
import uuid
import hashlib
import os

machine_id = ""
try:
    machine_id += str(uuid.getnode())
except:
    pass
try:
    machine_id += os.environ.get('COMPUTERNAME', '')
except:
    pass
try:
    machine_id += os.environ.get('USERNAME', '')
except:
    pass

hwid = hashlib.sha256(machine_id.encode()).hexdigest()[:16].upper()
print(hwid)
"@
        $pythonCode | Set-Content -Path $tempScript -Encoding UTF8
        
        try {
            # PRIORITÉ 1: Essayer d'utiliser le Python de Millennium (si Steam est installé)
            $steamPath = Get-SteamPath
            if ($steamPath) {
                $millenniumPythons = Get-ChildItem -Path $steamPath -Recurse -Filter "python.exe" -ErrorAction SilentlyContinue -Depth 10 | Select-Object -First 5 -ExpandProperty FullName
                foreach ($pyPath in $millenniumPythons) {
                    try {
                        $test = & $pyPath --version 2>&1
                        if ($LASTEXITCODE -eq 0) {
                            $result = & $pyPath $tempScript 2>&1
                            if ($LASTEXITCODE -eq 0 -and $result -and $result.Trim()) {
                                $hwid = $result.Trim()
                                Remove-Item $tempScript -ErrorAction SilentlyContinue
                                Write-Log "HWID calculated using Millennium Python: $hwid" "INFO"
                                return $hwid
                            }
                        }
                    }
                    catch {
                        # Continuer avec le prochain Python
                    }
                }
            }
            
            # PRIORITÉ 2: Essayer python, python3, ou py (Python système)
            $pythonCmds = @("python", "python3", "py")
            foreach ($cmd in $pythonCmds) {
                try {
                    # Vérifier si la commande existe
                    $null = Get-Command $cmd -ErrorAction Stop
                    $result = & $cmd $tempScript 2>&1
                    if ($LASTEXITCODE -eq 0 -and $result -and $result.Trim()) {
                        $hwid = $result.Trim()
                        Remove-Item $tempScript -ErrorAction SilentlyContinue
                        Write-Log "HWID calculated using system Python: $hwid" "INFO"
                        return $hwid
                    }
                }
                catch {
                    # Continuer avec la prochaine commande
                }
            }
            
            # Nettoyer
            Remove-Item $tempScript -ErrorAction SilentlyContinue
        }
        catch {
            Remove-Item $tempScript -ErrorAction SilentlyContinue
        }
        
        # Fallback si Python n'est pas disponible - utiliser la même logique
        # ATTENTION: Ce fallback peut ne pas correspondre exactement à uuid.getnode()
        # Il est préférable d'avoir Python installé
        Write-Log "Python not found. Using PowerShell fallback (may not match exactly)..." "WARN"
        $id = ""
        try {
            # Obtenir uuid.getnode() équivalent - prendre le premier adaptateur réseau physique
            $adapters = Get-WmiObject Win32_NetworkAdapterConfiguration | Where-Object { 
                $_.MACAddress -ne $null -and $_.MACAddress.Length -eq 17 -and $_.MACAddress -ne "00:00:00:00:00:00"
            }
            if ($adapters) {
                $mac = ($adapters | Select-Object -First 1).MACAddress
                $macClean = $mac -replace ":", "" -replace "-", ""
                $macInt = [Convert]::ToInt64($macClean, 16)
                $id += $macInt.ToString()
            }
        }
        catch {}
        try { $id += $env:COMPUTERNAME } catch {}
        try { $id += $env:USERNAME } catch {}
        if (-not $id) { 
            Write-Log "Failed to generate HWID. Returning UNKNOWN." "ERR"
            return "UNKNOWN" 
        }
        $sha = [System.Security.Cryptography.SHA256]::Create()
        $hash = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($id))
        $hwid = (($hash | ForEach-Object { $_.ToString("X2") }) -join "").Substring(0, 16).ToUpper()
        Write-Log "HWID calculated using PowerShell fallback: $hwid" "WARN"
        Write-Log "WARNING: This HWID may not match the plugin's HWID!" "WARN"
        return $hwid
    }
    catch { 
        Write-Log "Error calculating HWID: $_" "ERR"
        return "UNKNOWN" 
    }
}

function Get-SavedLicense {
    if (Test-Path $LICENSE_FILE) {
        try {
            # Lire le fichier (gère automatiquement le BOM si présent)
            $content = Get-Content $LICENSE_FILE -Raw -Encoding UTF8
            $data = $content | ConvertFrom-Json
            
            # Vérifier si le HWID correspond au HWID actuel
            $currentHwid = Get-HardwareId
            if ($data.hwid -and $data.hwid -ne $currentHwid) {
                # HWID mismatch - supprimer le fichier pour forcer la réactivation
                Write-Log "HWID mismatch detected. Removing old license file..." "WARN"
                Remove-Item $LICENSE_FILE -Force
                return $null
            }
            
            # Corriger le fichier en le réécrivant sans BOM
            $json = $data | ConvertTo-Json
            $utf8NoBom = New-Object System.Text.UTF8Encoding $false
            [System.IO.File]::WriteAllText($LICENSE_FILE, $json, $utf8NoBom)
            return $data
        }
        catch {
            # Si erreur, supprimer le fichier corrompu
            Write-Log "License file is corrupted. Removing it..." "WARN"
            Remove-Item $LICENSE_FILE -Force -ErrorAction SilentlyContinue
            return $null
        }
    }
    return $null
}

function Save-License {
    param([string]$Key, [string]$Hwid)
    try {
        $data = @{key = $Key; hwid = $Hwid; activated_at = (Get-Date -Format "yyyy-MM-dd HH:mm:ss") } | ConvertTo-Json
        # Sauvegarder sans BOM UTF-8 (compatible avec Python)
        $utf8NoBom = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText($LICENSE_FILE, $data, $utf8NoBom)
    }
    catch {}
}

function Test-LicenseOnline {
    param([string]$Key, [string]$Hwid)
    try {
        $body = @{key = $Key; hwid = $Hwid } | ConvertTo-Json
        return Invoke-RestMethod -Uri "$LICENSE_API_URL/validate" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 15
    }
    catch {
        return @{valid = $false; error = "NO_CONNECTION"; message = "Impossible de contacter le serveur" }
    }
}

function Test-License {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "        VERIFICATION DE LA LICENCE" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan
    
    $hwid = Get-HardwareId
    $saved = Get-SavedLicense
    
    if ($saved -and $saved.key) {
        Write-Host "Licence trouvée, vérification en ligne...`n" -ForegroundColor Yellow
        $result = Test-LicenseOnline -Key $saved.key -Hwid $hwid
        if ($result.valid) {
            Write-Log "Licence valide !" "OK"
            Write-Host "     ID Machine: $hwid`n" -ForegroundColor Green
            return $true
        }
        else {
            # Si la licence est invalide (HWID mismatch ou autre), supprimer le fichier
            Write-Log "License validation failed: $($result.message)" "WARN"
            Write-Host "Removing invalid license file..." -ForegroundColor Yellow
            Remove-Item $LICENSE_FILE -Force -ErrorAction SilentlyContinue
        }
    }
    
    Write-Host "Entrez votre clé de licence SkyTools:" -ForegroundColor Yellow
    Write-Host "(Format: SKY-XXXX-XXXX-XXXX-XXXXXXXX)" -ForegroundColor Gray
    Write-Host "Achetez sur: https://skytools.store`n" -ForegroundColor Gray
    Write-Host "!! ATTENTION: La clé sera liée à CET ordinateur DEFINITIVEMENT !!`n" -ForegroundColor Red
    
    for ($i = 0; $i -lt 3; $i++) {
        $key = (Read-Host "Clé").Trim().ToUpper()
        if (-not $key) { Write-Log "Aucune clé entrée." "ERR"; continue }
        if (-not $key.StartsWith("SKY-") -or ($key -split "-").Count -ne 5) {
            Write-Log "Format invalide. $(3-$i-1) tentative(s) restante(s)." "ERR"
            continue
        }
        Write-Host "Vérification en ligne..." -ForegroundColor Yellow
        $result = Test-LicenseOnline -Key $key -Hwid $hwid
        if ($result.valid) {
            Save-License -Key $key -Hwid $hwid
            Write-Host "`n[OK] Licence activée avec succès !`n" -ForegroundColor Green
            return $true
        }
        else {
            Write-Log $result.message "ERR"
        }
    }
    return $false
}

function Test-MillenniumInstalled {
    param([string]$SteamPath)
    if (-not $SteamPath) { return $false }
    $dll = Join-Path $SteamPath "millennium.dll"
    return ((Test-Path $dll) -and ((Get-Item $dll).Length -gt 0))
}

function Test-SteamToolsInstalled {
    param([string]$SteamPath)
    if (-not $SteamPath) { return $false }
    $dll = Join-Path $SteamPath "xinput1_4.dll"
    return (Test-Path $dll)
}

function Install-SteamTools {
    param([string]$SteamPath)
    $alreadyInstalled = Test-SteamToolsInstalled -SteamPath $SteamPath
    if ($alreadyInstalled) {
        Write-Log "SteamTools already installed, reinstalling..." "INFO"
    }
    else {
        Write-Log "SteamTools not found. Installing SteamTools..." "INFO"
    }
    Write-Log "This will fix Steam compatibility issues with the latest updates." "INFO"
    Write-Log "Please wait, this may take a few minutes..." "INFO"
    $ProgressPreference = 'SilentlyContinue'
    try {
        Write-Log "Executing SteamTools installation..." "INFO"
        # Lancer SteamTools dans un processus séparé pour éviter qu'il ferme PowerShell
        $steamtoolsScript = Invoke-RestMethod -Uri "steam.run" -ErrorAction Stop
        # Créer un script temporaire et l'exécuter dans un nouveau processus
        $tempScript = Join-Path $env:TEMP "steamtools_install.ps1"
        $steamtoolsScript | Set-Content -Path $tempScript -Encoding UTF8
        # Exécuter dans un nouveau processus PowerShell qui ne fermera pas le script principal
        $process = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $tempScript -Wait -PassThru -NoNewWindow
        Start-Sleep -Seconds 3
        # Nettoyer le script temporaire
        Remove-Item $tempScript -ErrorAction SilentlyContinue
        if (Test-SteamToolsInstalled -SteamPath $SteamPath) {
            if ($alreadyInstalled) {
                Write-Log "SteamTools reinstalled successfully." "OK"
            }
            else {
                Write-Log "SteamTools installed successfully." "OK"
            }
        }
        else {
            Write-Log "SteamTools installation may have failed (non-fatal)" "WARN"
            Write-Log "You can install SteamTools manually: irm steam.run | iex" "INFO"
        }
    }
    catch {
        Write-Log "SteamTools installation failed (non-fatal): $_" "WARN"
        Write-Log "You can install SteamTools manually: irm steam.run | iex" "INFO"
    }
}

function Install-Millennium {
    param([string]$SteamPath)
    if (Test-MillenniumInstalled -SteamPath $SteamPath) {
        Write-Log "Millennium is already installed." "OK"
        return
    }
    
    $steam = Get-Process -Name "steam" -ErrorAction SilentlyContinue
    if ($steam) {
        Write-Log "Steam is running. Closing Steam..." "INFO"
        Stop-Process -Name "steam" -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 3
        Write-Log "Steam closed." "OK"
    }

    Write-Log "Installing Millennium (Manual Method)..." "INFO"
    try {
        # 1. Get Latest Release
        Write-Log "Querying GitHub for latest Millennium release..." "INFO"
        try {
            $release = Invoke-RestMethod -Uri "https://api.github.com/repos/SteamClientHomebrew/Millennium/releases/latest" -Headers @{"Accept" = "application/vnd.github+json"; "User-Agent" = "SkyTools-Installer" } -TimeoutSec 15
        }
        catch {
            Write-Log "Failed to query GitHub API. Trying fallback URL..." "WARN"
            # Fallback hardcoded if API fails
            $release = @{ tag_name = "v2.32.0" } 
        }

        # 2. Determine Download URL
        $asset = $null
        if ($release.assets) {
            $asset = $release.assets | Where-Object { $_.name -like "*windows-x86_64.zip" } | Select-Object -First 1
        }
        
        $url = ""
        if ($asset) { 
            $url = $asset.browser_download_url 
        }
        else {
            # Fallback construction
            $tag = $release.tag_name
            if (-not $tag) { $tag = "v2.32.0" }
            $url = "https://github.com/SteamClientHomebrew/Millennium/releases/download/$tag/millennium-$tag-windows-x86_64.zip"
            # Note: The zip name format might vary, but this is a best guess fallback
        }

        Write-Log "Downloading Millennium from: $url" "INFO"
        $zipPath = Join-Path $env:TEMP "millennium_install.zip"
        Invoke-WebRequest -Uri $url -OutFile $zipPath -UserAgent "SkyTools-Installer"
        
        # 3. Extract to Steam Folder
        Write-Log "Extracting to Steam folder: $SteamPath" "INFO"
        Expand-Archive -Path $zipPath -DestinationPath $SteamPath -Force
        
        Remove-Item $zipPath -ErrorAction SilentlyContinue
        
        Start-Sleep -Seconds 2
        
        if (Test-MillenniumInstalled -SteamPath $SteamPath) {
            Write-Log "Millennium installed successfully!" "OK"
        }
        else {
            Write-Log "Millennium installation check failed, but files were copied." "WARN"
        }
    }
    catch {
        Write-Log "Millennium installation failed (Manual): $_" "ERR"
    }
}

function Install-PythonDependencies {
    param([string]$SteamPath)
    if (-not (Test-MillenniumInstalled -SteamPath $SteamPath)) {
        Write-Log "Millennium not found! Cannot install Python dependencies." "ERR"
        return
    }
    Write-Log "Installing Python dependencies (httpx, requests)..." "INFO"
    $pythons = Get-ChildItem -Path $SteamPath -Recurse -Filter "python.exe" -ErrorAction SilentlyContinue -Depth 10 | Select-Object -Unique -ExpandProperty FullName
    if (-not $pythons) {
        Write-Log "No Python executables found in Steam!" "ERR"
        return
    }
    $success = 0
    $count = 0
    foreach ($py in $pythons) {
        try {
            $test = & $py --version 2>&1
            if ($LASTEXITCODE -eq 0) {
                $count++
                & $py -m pip install --quiet --upgrade httpx==0.27.2 requests 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) { $success++ }
            }
        }
        catch {}
    }
    if ($success -gt 0) {
        Write-Log "Installed dependencies in $success Python environment(s)." "OK"
    }
    else {
        Write-Log "Failed to install dependencies." "WARN"
    }
}

function Install-SkyTools {
    param([string]$SteamPath)
    # CUSTOM URL FOR HOTFIX
    $url = "https://raw.githubusercontent.com/zlyti/SkyTools-Custom-API/main/custom_api_kit/dist/skytools_custom.zip"
    Write-Log "Downloading SkyTools Custom Plugin..." "INFO"
    $zip = Join-Path $env:TEMP "skytools.zip"
    Invoke-WebRequest -Uri $url -OutFile $zip -TimeoutSec 120
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
function Fix-LicenseFileIfNeeded {
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
Fix-LicenseFileIfNeeded

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

