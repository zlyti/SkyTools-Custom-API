import json
import os
import re
import shutil
import sys
import tempfile
import time
import zipfile
import subprocess
import hashlib
import uuid
from io import BytesIO

import requests


GITHUB_API = "https://api.github.com"
DEFAULT_UPDATE_JSON_RELATIVE = os.path.join("backend", "update.json")

# ============== LICENSE CONFIGURATION ==============
# IMPORTANT: Remplace cette URL par ton URL Cloudflare Worker après déploiement !
LICENSE_API_URL = "https://skytools-license.skytoolskey.workers.dev"
LICENSE_FILE = os.path.join(os.path.expanduser("~"), ".skytools_license")

# --------------- Logging ---------------


def log_to_widget(widget, message: str, level: str = 'info') -> None:
    ts = time.strftime("%H:%M:%S")
    badge = {
        'info': 'INFO',
        'ok': ' OK ',
        'warn': 'WARN',
        'err': 'ERR ',
    }.get(level, 'INFO')
    line = f"[{ts}] [{badge}] {message}\n"
    try:
        print(line, end="")
    except Exception:
        print(line, end="")


def print_banner():
    print("")
    print("=" * 50)
    print("        SKYTOOLS - Steam Plugin Installer")
    print("                   v1.0")
    print("=" * 50)
    print("")


def get_hardware_id() -> str:
    """Génère un ID unique basé sur le matériel de l'ordinateur."""
    try:
        # Utiliser plusieurs sources pour créer un ID unique
        machine_id = ""
        
        # UUID de la machine
        try:
            machine_id += str(uuid.getnode())
        except:
            pass
        
        # Nom de l'ordinateur
        try:
            machine_id += os.environ.get('COMPUTERNAME', '')
        except:
            pass
        
        # Nom d'utilisateur
        try:
            machine_id += os.environ.get('USERNAME', '')
        except:
            pass
        
        # Créer un hash unique
        hwid = hashlib.sha256(machine_id.encode()).hexdigest()[:16].upper()
        return hwid
    except Exception:
        return "UNKNOWN"


def load_saved_license() -> dict:
    """Charge les données de licence sauvegardées."""
    try:
        if os.path.exists(LICENSE_FILE):
            # Utiliser utf-8-sig pour gérer les fichiers avec ou sans BOM UTF-8
            with open(LICENSE_FILE, "r", encoding="utf-8-sig") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_license(license_key: str, hwid: str) -> None:
    """Sauvegarde la clé de licence localement."""
    try:
        data = {
            "key": license_key,
            "hwid": hwid,
            "activated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(LICENSE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


def validate_license_online(license_key: str, hwid: str) -> dict:
    """Valide la licence auprès du serveur."""
    try:
        response = requests.post(
            f"{LICENSE_API_URL}/validate",
            json={"key": license_key, "hwid": hwid},
            timeout=15
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"valid": False, "error": "SERVER_ERROR", "message": "Erreur serveur"}
    except requests.exceptions.ConnectionError:
        return {"valid": False, "error": "NO_CONNECTION", "message": "Impossible de contacter le serveur de licences"}
    except requests.exceptions.Timeout:
        return {"valid": False, "error": "TIMEOUT", "message": "Le serveur ne répond pas"}
    except Exception as e:
        return {"valid": False, "error": "UNKNOWN", "message": str(e)}


def check_license() -> bool:
    """Vérifie si l'utilisateur a une licence valide (validation en ligne)."""
    print("")
    print("=" * 50)
    print("        VERIFICATION DE LA LICENCE")
    print("=" * 50)
    print("")
    
    current_hwid = get_hardware_id()
    saved_data = load_saved_license()
    
    # Vérifier si une licence est déjà sauvegardée localement
    if saved_data:
        saved_key = saved_data.get("key", "")
        
        print("Licence trouvee, verification en ligne...")
        print("")
        
        # Vérifier auprès du serveur
        result = validate_license_online(saved_key, current_hwid)
        
        if result.get("valid"):
            print("[OK] Licence valide !")
            print(f"     ID Machine: {current_hwid}")
            
            # Mettre à jour le HWID local s'il a changé mais que le serveur l'accepte
            if saved_data.get("hwid") != current_hwid:
                print("     Mise a jour du HWID dans le fichier de licence...")
                save_license(saved_key, current_hwid)
            
            print("")
            return True
        else:
            error = result.get("error", "UNKNOWN")
            message = result.get("message", "Erreur inconnue")
            
            if error == "KEY_ALREADY_USED":
                print("[ERREUR] Cette licence est activee sur un autre ordinateur.")
                print("         Chaque licence ne peut etre utilisee que sur UN seul PC.")
                print("")
                # Supprimer la licence locale invalide
                try:
                    os.remove(LICENSE_FILE)
                except:
                    pass
                return False
            elif error == "KEY_NOT_FOUND":
                print("[ERREUR] Cette cle n'existe pas dans notre systeme.")
                print("")
                try:
                    os.remove(LICENSE_FILE)
                except:
                    pass
            elif error == "KEY_REVOKED":
                print("[ERREUR] Cette cle a ete revoquee.")
                print("")
                try:
                    os.remove(LICENSE_FILE)
                except:
                    pass
                return False
            elif error == "NO_CONNECTION":
                print("[ERREUR] Impossible de contacter le serveur de licences.")
                print("         Verifiez votre connexion internet.")
                print("")
                return False
            else:
                print(f"[ERREUR] {message}")
                print("")
    
    # Demander une nouvelle clé
    print("Entrez votre cle de licence SkyTools:")
    print("(Format: SKY-XXXX-XXXX-XXXX-XXXXXXXX)")
    print("Achetez sur: https://skytools.store")
    print("")
    print("!! ATTENTION: La cle sera liee a CET ordinateur DEFINITIVEMENT !!")
    print("")
    
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            license_key = input("Cle: ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            return False
        
        if not license_key:
            print("[ERREUR] Aucune cle entree.")
            continue
        
        # Vérifier le format basique
        if not license_key.startswith("SKY-") or len(license_key.split("-")) != 5:
            remaining = max_attempts - attempt - 1
            if remaining > 0:
                print(f"[ERREUR] Format invalide. {remaining} tentative(s) restante(s).")
                print("         Format attendu: SKY-XXXX-XXXX-XXXX-XXXXXXXX\n")
            else:
                print("[ERREUR] Format invalide. Plus de tentatives.\n")
            continue
        
        print("Verification en ligne...")
        
        # Valider auprès du serveur
        result = validate_license_online(license_key, current_hwid)
        
        if result.get("valid"):
            # Sauvegarder localement
            save_license(license_key, current_hwid)
            
            print("")
            print("[OK] Licence activee avec succes !")
            print(f"     Cle liee a cet ordinateur (ID: {current_hwid})")
            print("     Cette cle ne fonctionnera plus sur un autre PC.")
            print("")
            return True
        else:
            error = result.get("error", "UNKNOWN")
            message = result.get("message", "Erreur inconnue")
            remaining = max_attempts - attempt - 1
            
            if error == "KEY_ALREADY_USED":
                print("[ERREUR] Cette cle est deja activee sur un autre ordinateur !")
                if remaining > 0:
                    print(f"         {remaining} tentative(s) restante(s).\n")
            elif error == "KEY_NOT_FOUND":
                print("[ERREUR] Cette cle n'existe pas.")
                if remaining > 0:
                    print(f"         {remaining} tentative(s) restante(s).\n")
            elif error == "KEY_REVOKED":
                print("[ERREUR] Cette cle a ete revoquee.")
                if remaining > 0:
                    print(f"         {remaining} tentative(s) restante(s).\n")
            elif error == "NO_CONNECTION":
                print("[ERREUR] Impossible de contacter le serveur.")
                print("         Verifiez votre connexion internet.\n")
                return False
            else:
                print(f"[ERREUR] {message}")
                if remaining > 0:
                    print(f"         {remaining} tentative(s) restante(s).\n")
    
    return False


def detect_steam_path() -> str:
    steam_path = None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
    except Exception:
        steam_path = None
    return os.path.abspath(steam_path) if steam_path else ""


def is_millennium_installed(steam_path: str) -> bool:
    """Vérifie si Millennium est installé - vérifie UNIQUEMENT millennium.dll dans le dossier Steam."""
    if not steam_path:
        return False
    
    # Vérifier UNIQUEMENT millennium.dll dans le dossier Steam directement
    # C'est le fichier principal de Millennium - python311.dll peut exister sans Millennium
    millennium_dll = os.path.join(steam_path, "millennium.dll")
    
    if os.path.exists(millennium_dll) and os.path.isfile(millennium_dll):
        # Vérifier aussi que le fichier n'est pas vide (au cas où il reste un fichier vide)
        try:
            file_size = os.path.getsize(millennium_dll)
            if file_size > 0:
                return True
        except Exception:
            pass
    
    return False


def ensure_millennium_installed(log: callable) -> None:
    """Vérifie et installe Millennium si nécessaire - méthode améliorée."""
    steam_path = detect_steam_path()
    if not steam_path:
        log("Steam path not found in registry; continuing anyway.", level='warn')
        return
    
    # Vérifier si Millennium est déjà installé
    if is_millennium_installed(steam_path):
        log("Millennium is already installed.", level='ok')
        return
    
    # Vérifier et fermer Steam si nécessaire (Millennium nécessite Steam fermé)
    try:
        check_steam_cmd = (
            "powershell.exe",
            "-NoProfile",
            "-Command",
            "Get-Process -Name steam -ErrorAction SilentlyContinue | Select-Object -First 1 | Out-Null; if ($?) { Write-Output 'RUNNING' } else { Write-Output 'NOT_RUNNING' }"
        )
        steam_check = subprocess.run(
            check_steam_cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            shell=False
        )
        if steam_check.returncode == 0:
            output = steam_check.stdout.decode('utf-8', errors='ignore').strip()
            if 'RUNNING' in output:
                log("Steam is currently running. Closing Steam for Millennium installation...", level='info')
                try:
                    # Fermer Steam proprement
                    close_steam_cmd = (
                        "powershell.exe",
                        "-NoProfile",
                        "-Command",
                        "Get-Process -Name steam -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue; Start-Sleep -Seconds 3; if (Get-Process -Name steam -ErrorAction SilentlyContinue) { Write-Output 'STILL_RUNNING' } else { Write-Output 'CLOSED' }"
                    )
                    close_result = subprocess.run(
                        close_steam_cmd,
                        check=False,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=10,
                        shell=False
                    )
                    if close_result.returncode == 0:
                        close_output = close_result.stdout.decode('utf-8', errors='ignore').strip()
                        if 'CLOSED' in close_output:
                            log("Steam closed successfully.", level='ok')
                            import time
                            time.sleep(2)  # Attendre un peu pour que Steam se ferme complètement
                        else:
                            log("WARNING: Could not close Steam completely. Installation may fail.", level='warn')
                except Exception as e:
                    log(f"Could not close Steam: {e}", level='warn')
                    log("Please close Steam manually and try again.", level='info')
    except Exception:
        # Ignorer les erreurs de vérification
        pass
    
    log("Installing Millennium...")
    log("This may take a few minutes, please wait...")
    
    # Utiliser EXACTEMENT la même commande que celle qui fonctionne manuellement
    # Commande manuelle qui marche: iwr -useb 'https://steambrew.app/install.ps1' | iex
    try:
        log("Executing Millennium installation (silent mode)...")
        # Commande PowerShell EXACTE comme celle qui fonctionne manuellement
        # Utiliser Invoke-Expression directement avec le pipe comme en manuel
        ps_command = (
            "$ProgressPreference = 'SilentlyContinue'; "
            "Invoke-Expression (Invoke-WebRequest -UseBasicParsing -Uri 'https://steambrew.app/install.ps1').Content"
        )
        cmd = (
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            ps_command,
        )
        log("Running PowerShell command (this may take 1-2 minutes)...")
        log("Using the same command that works manually: iwr -useb 'https://steambrew.app/install.ps1' | iex", level='info')
        completed = subprocess.run(
            cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=600,  # 10 minutes
            shell=False
        )
        
        # Analyser la sortie (mais ne pas bloquer sur les erreurs - le script peut afficher des erreurs mais réussir)
        output = (completed.stdout or b"").decode('utf-8', errors='ignore')
        errors = (completed.stderr or b"").decode('utf-8', errors='ignore')
        
        # Afficher les erreurs importantes seulement
        if errors:
            error_preview = errors[:300].replace('\n', ' ')
            if error_preview and 'error' in error_preview.lower():
                log(f"PowerShell errors: {error_preview}", level='warn')
        
        # Le script peut retourner un code d'erreur même si l'installation réussit partiellement
        # On vérifie plutôt si Millennium est installé après
        
        # Attendre et vérifier plusieurs fois (l'installation peut prendre du temps)
        import time
        max_attempts = 12  # Augmenté à 12 tentatives (60 secondes au total)
        for attempt in range(max_attempts):
            time.sleep(5)  # Attendre 5 secondes entre chaque vérification
            if is_millennium_installed(steam_path):
                log("Millennium installed successfully.", level='ok')
                return
            if attempt < max_attempts - 1:
                log(f"Waiting for Millennium installation... ({attempt + 1}/{max_attempts})", level='info')
        
        # Si toujours pas installé, vérifier une dernière fois après une attente plus longue
        log("Waiting additional time for Millennium installation to complete...", level='info')
        time.sleep(15)
        if is_millennium_installed(steam_path):
            log("Millennium installed successfully (detected after additional wait).", level='ok')
            return
        
        # Si toujours pas installé après toutes les tentatives
        log("Millennium installation may have failed or is still in progress.", level='warn')
        
    except subprocess.TimeoutExpired:
        log("Millennium installation timed out (but may still be installing in background).", level='warn')
        # Vérifier quand même une dernière fois après le timeout
        import time
        time.sleep(10)
    except Exception as e:
        log(f"Millennium installation error: {e}", level='warn')
    
    # Vérification finale
    if is_millennium_installed(steam_path):
        log("Millennium installation completed successfully.", level='ok')
    else:
        log("WARNING: Millennium installation appears to have failed!", level='err')
        log("SkyTools requires Millennium to function.", level='err')
        log("Please install Millennium manually:", level='info')
        log("  PowerShell: iwr -useb 'https://steambrew.app/install.ps1' | iex", level='info')
        log("  Or visit: https://steambrew.app/", level='info')


def find_millennium_python(steam_path: str) -> str:
    """Trouve l'exécutable Python de Millennium - recherche exhaustive."""
    if not steam_path:
        return None
    
    # Chemins standards à vérifier en premier
    possible_python_paths = [
        os.path.join(steam_path, "steamui", "resources", "millennium", "python", "python.exe"),
        os.path.join(steam_path, "steamui", "resources", "millennium", "python.exe"),
        os.path.join(steam_path, "steamui", "millennium", "python", "python.exe"),
        os.path.join(steam_path, "steamui", "millennium", "python.exe"),
        # Aussi dans le dossier Steam directement (comme millennium.dll)
        os.path.join(steam_path, "python", "python.exe"),
        os.path.join(steam_path, "python.exe"),
    ]
    
    for path in possible_python_paths:
        if os.path.exists(path) and os.path.isfile(path):
            return path
    
    # Recherche récursive dans les dossiers millennium (profondeur augmentée)
    # EXCLURE les dossiers de cache (ext/data/cache, cache, temp, tmp)
    excluded_dirs = {"cache", "temp", "tmp", "ext"}
    millennium_dirs = [
        os.path.join(steam_path, "steamui", "resources", "millennium"),
        os.path.join(steam_path, "steamui", "millennium"),
        os.path.join(steam_path, "millennium"),
    ]
    
    for millennium_dir in millennium_dirs:
        if os.path.exists(millennium_dir) and os.path.isdir(millennium_dir):
            try:
                # Chercher récursivement python.exe (profondeur augmentée à 10)
                for root, dirs, files in os.walk(millennium_dir):
                    # Exclure les dossiers de cache
                    dirs[:] = [d for d in dirs if d.lower() not in excluded_dirs]
                    
                    # Ignorer les chemins contenant "cache", "temp", "tmp" ou "ext/data"
                    if any(excluded in root.lower() for excluded in ["cache", "temp", "tmp", "ext\\data", "ext/data"]):
                        continue
                    
                    if "python.exe" in files:
                        python_path = os.path.join(root, "python.exe")
                        if os.path.exists(python_path) and os.path.isfile(python_path):
                            # Vérifier que c'est bien le Python de Millennium (présence de DLL Python)
                            python_dir = os.path.dirname(python_path)
                            # Chercher python311.dll ou python3*.dll dans le même dossier ou parent
                            for check_dir in [python_dir, os.path.dirname(python_dir)]:
                                if os.path.exists(check_dir):
                                    for dll_file in os.listdir(check_dir):
                                        if dll_file.startswith("python3") and dll_file.endswith(".dll"):
                                            return python_path
                            # Si pas de DLL trouvée, vérifier si on est dans un dossier millennium (mais pas cache)
                            if "millennium" in python_path.lower() and "cache" not in python_path.lower():
                                return python_path
                    # Limiter la profondeur à 10 niveaux
                    if root.count(os.sep) - millennium_dir.count(os.sep) >= 10:
                        dirs[:] = []
            except Exception:
                pass
    
    # Dernière tentative : recherche PowerShell exhaustive dans tout le dossier Steam
    # EXCLURE les dossiers de cache
    try:
        ps_search = f"""
        $steam = '{steam_path}'
        $excluded = @('cache', 'temp', 'tmp', 'ext\\data', 'ext/data')
        $python = Get-ChildItem -Path $steam -Recurse -Filter 'python.exe' -ErrorAction SilentlyContinue -Depth 10 | 
            Where-Object {{ 
                $dir = $_.DirectoryName
                $isExcluded = $excluded | Where-Object {{ $dir -like "*$_*" }}
                if ($isExcluded) {{ return $false }}
                (Test-Path (Join-Path $dir 'python3*.dll')) -or 
                (Test-Path (Join-Path (Split-Path $dir) 'python3*.dll')) -or
                (($dir -like '*millennium*') -and ($dir -notlike '*cache*'))
            }} | 
            Select-Object -First 1 -ExpandProperty FullName
        if ($python) {{ Write-Output $python }}
        """
        ps_cmd = (
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            ps_search,
        )
        search_result = subprocess.run(
            ps_cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            shell=False
        )
        if search_result.returncode == 0:
            found_path = search_result.stdout.decode('utf-8', errors='ignore').strip()
            if found_path and os.path.exists(found_path):
                return found_path
    except Exception:
        pass
    
    return None


def install_python_dependencies(steam_path: str, log: callable) -> None:
    """Installe les dépendances Python nécessaires pour SkyTools dans TOUS les Python trouvés dans Steam."""
    try:
        log("Installing Python dependencies (httpx, requests) in all Python environments...")
        
        # Vérifier d'abord si Millennium est installé (sinon il n'y aura pas de Python dans Steam)
        if not is_millennium_installed(steam_path):
            log("WARNING: Millennium not found! Python dependencies cannot be installed.", level='err')
            log("Please install Millennium first, then run: install_deps_all_pythons.bat", level='info')
            return
        
        if not steam_path:
            log("WARNING: Steam path not found! Python dependencies cannot be installed.", level='err')
            return
        
        # Utiliser PowerShell pour trouver TOUS les python.exe et installer dans chacun
        log("Searching for all Python executables in Steam...")
        
        ps_script = f"""
$steam = '{steam_path}'
$pythons = Get-ChildItem -Path $steam -Recurse -Filter "python.exe" -ErrorAction SilentlyContinue -Depth 10 | Select-Object -Unique -ExpandProperty FullName

if (-not $pythons) {{
    Write-Output "NO_PYTHON_FOUND"
    exit 1
}}

$count = 0
$success = 0

foreach ($py in $pythons) {{
    $count++
    try {{
        $test = & $py --version 2>&1
        if ($LASTEXITCODE -eq 0) {{
            Write-Output "TESTING:$py"
            $result = & $py -m pip install --quiet --upgrade httpx==0.27.2 requests 2>&1 | Out-String
            if ($LASTEXITCODE -eq 0 -or $result -match "already satisfied") {{
                Write-Output "SUCCESS:$py"
                $success++
            }} else {{
                Write-Output "FAILED:$py"
            }}
        }}
    }} catch {{
        Write-Output "ERROR:$py"
    }}
}}

Write-Output "SUMMARY:$success/$count"
"""
        
        ps_cmd = (
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            ps_script,
        )
        
        log("Installing dependencies in all found Python environments...")
        log("This may take a few minutes...")
        
        result = subprocess.run(
            ps_cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300,  # 5 minutes
            shell=False
        )
        
        output = (result.stdout or b"").decode('utf-8', errors='ignore')
        errors = (result.stderr or b"").decode('utf-8', errors='ignore')
        
        # Parser la sortie
        tested_count = 0
        success_count = 0
        failed_pythons = []
        
        for line in output.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            if line == "NO_PYTHON_FOUND":
                log("WARNING: No Python executables found in Steam!", level='err')
                log("Millennium may not be properly installed.", level='warn')
                return
            
            if line.startswith("TESTING:"):
                python_path = line.replace("TESTING:", "").strip()
                tested_count += 1
                log(f"Testing Python #{tested_count}: {os.path.basename(os.path.dirname(python_path))}", level='info')
            
            elif line.startswith("SUCCESS:"):
                python_path = line.replace("SUCCESS:", "").strip()
                success_count += 1
                log(f"  [OK] Dependencies installed in Python #{tested_count}", level='ok')
            
            elif line.startswith("FAILED:"):
                python_path = line.replace("FAILED:", "").strip()
                failed_pythons.append(python_path)
                log(f"  [WARN] Failed to install in Python #{tested_count}", level='warn')
            
            elif line.startswith("SUMMARY:"):
                summary = line.replace("SUMMARY:", "").strip()
                # Le résumé est déjà traité via les lignes SUCCESS/FAILED
        
        # Résumé final
        if success_count > 0:
            log(f"Successfully installed dependencies in {success_count} Python environment(s).", level='ok')
            if tested_count > success_count:
                log(f"Note: {tested_count - success_count} Python(s) failed (non-critical).", level='warn')
        else:
            log("WARNING: Failed to install dependencies in any Python environment!", level='err')
            log("You may need to run install_deps_all_pythons.bat manually.", level='info')
        
        # Vérifier l'installation en testant un Python trouvé
        if success_count > 0:
            log("Verifying installation...")
            python_exe = find_millennium_python(steam_path)
            if python_exe:
                try:
                    verify_cmd = [python_exe, "-c", "import httpx; print(httpx.__version__)"]
                    verify_result = subprocess.run(
                        verify_cmd,
                        check=False,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=10
                    )
                    if verify_result.returncode == 0:
                        version = verify_result.stdout.decode('utf-8', errors='ignore').strip()
                        log(f"Verified: httpx {version} is installed.", level='ok')
                    else:
                        log("Warning: httpx verification failed, but installation may have succeeded in other Python environments.", level='warn')
                except Exception as e:
                    log(f"Verification error: {e}", level='warn')
        
        if result.returncode != 0 and success_count == 0:
            log("PowerShell script encountered errors.", level='warn')
            if errors:
                error_preview = errors[:300].replace('\n', ' ')
                log(f"Error preview: {error_preview}", level='warn')
                
    except subprocess.TimeoutExpired:
        log("Python dependencies installation timed out (continuing)", level='warn')
        log("You can manually install dependencies by running: install_deps_all_pythons.bat", level='info')
    except Exception as e:
        log(f"Failed to install Python dependencies (non-fatal): {e}", level='warn')
        log("You can manually install dependencies by running: install_deps_all_pythons.bat", level='info')


def apply_steamtools_fix(log: callable) -> None:
    """Applique le fix SteamTools pour corriger les problèmes avec les nouvelles mises à jour Steam."""
    try:
        steam_path = detect_steam_path()
        if not steam_path:
            log("Steam path not found, skipping SteamTools fix", level='warn')
            return
        
        # Vérifier si SteamTools est déjà installé
        steamtools_dll = os.path.join(steam_path, "xinput1_4.dll")
        if os.path.exists(steamtools_dll):
            log("SteamTools already installed, skipping installation", level='info')
            return
        
        log("SteamTools not found. Installing SteamTools...")
        log("This will fix Steam compatibility issues with the latest updates.")
        log("Please wait, this may take a few minutes...")
        
        # Télécharger le script depuis steam.run
        log("Downloading SteamTools installation script...")
        try:
            script_response = requests.get("https://steam.run", timeout=30)
            if script_response.status_code != 200:
                log(f"Failed to download SteamTools script (status {script_response.status_code})", level='warn')
                return
            script_content = script_response.text
        except Exception as e:
            log(f"Failed to download SteamTools script: {e}", level='warn')
            return
        
        # Filtrer le script comme le fait LuaTools : enlever les lignes qui lancent Steam, Write-Host, cls, exit, etc.
        filtered_lines = []
        for line in script_content.split("\n"):
            # Garder toutes les lignes sauf celles qui :
            # - Lancent Steam (Start-Process avec steam)
            # - Affichent des messages (Write-Host, mais on garde les erreurs importantes)
            # - Nettoient l'écran (cls)
            # - Sortent du script (exit, sauf dans les blocs catch)
            should_keep = True
            
            # Enlever les lignes qui lancent Steam
            if "Start-Process" in line and "steam" in line.lower():
                should_keep = False
            # Enlever les lignes qui lancent steam.exe
            if "steam.exe" in line.lower() and ("Start-Process" in line or "&" in line):
                should_keep = False
            # Enlever cls
            if line.strip().lower() == "cls" or line.strip().lower().startswith("cls "):
                should_keep = False
            # Enlever exit (sauf dans les blocs catch/error)
            if line.strip().lower() == "exit" and "catch" not in script_content[max(0, script_content.find(line)-100):script_content.find(line)].lower():
                should_keep = False
            # Enlever Stop-Process pour Steam (sauf si c'est pour Get-Process)
            if "Stop-Process" in line and "steam" in line.lower() and "Get-Process" not in line:
                should_keep = False
            
            if should_keep:
                filtered_lines.append(line)
        
        filtered_script = "\n".join(filtered_lines)
        
        # Exécuter le script filtré silencieusement
        log("Installing SteamTools (silent mode)...")
        cmd = (
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "$ProgressPreference = 'SilentlyContinue'; $ErrorActionPreference = 'Continue'; "
            f"Invoke-Expression @'\n{filtered_script}\n'@ "
            "*>&1 | Out-Null",
        )
        completed = subprocess.run(
            cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300  # 5 minutes timeout
        )
        
        # Vérifier si SteamTools a été installé
        if os.path.exists(steamtools_dll):
            log("SteamTools installed successfully.", level='ok')
        elif completed.returncode == 0:
            log("SteamTools installation completed (verification pending)", level='ok')
        else:
            log("SteamTools installation may have failed (continuing)", level='warn')
    except subprocess.TimeoutExpired:
        log("SteamTools installation timed out (continuing)", level='warn')
    except Exception as e:
        log(f"SteamTools installation failed (non-fatal): {e}", level='warn')


def read_update_config(config_path: str) -> dict:
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "github": {
                "owner": "zlyti",
                "repo": "skytools-download",
                "asset_name": "skytools-steam-plugin.zip",
            }
        }


def fetch_latest_release_zip(cfg: dict, log: callable) -> bytes:
    gh = cfg.get("github") or {}
    owner = str(gh.get("owner", "")).strip()
    repo = str(gh.get("repo", "")).strip()
    asset_name = str(gh.get("asset_name", "skytools-steam-plugin.zip")).strip()
    token = str(gh.get("token", "")).strip()
    if not owner or not repo:
        raise RuntimeError("update.json is missing github.owner or github.repo")

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "SkyTools-Installer",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    log(f"Querying GitHub latest release for {owner}/{repo}...")
    data = None
    tag_name = ""
    
    # Primary GitHub API
    try:
        resp = requests.get(f"{GITHUB_API}/repos/{owner}/{repo}/releases/latest", headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        tag_name = str(data.get("tag_name", "")).strip()
        log(f"Latest tag: {tag_name or 'unknown'}")
    except Exception as api_err:
        error_str = str(api_err)
        # Fallback avec proxy en cas de rate limit
        if "403" in error_str or "rate limit" in error_str.lower():
            log("GitHub API rate limit reached (normal), using proxy...")
        else:
            log(f"GitHub API failed ({api_err}), trying proxy...")
        
        try:
            # Utiliser le proxy pour obtenir la dernière release
            proxy_url = f"https://luatools.vercel.app/api/github-latest?owner={owner}&repo={repo}"
            resp = requests.get(proxy_url, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            tag_name = str(data.get("tag_name", "")).strip()
            log(f"Proxy request successful, latest tag: {tag_name or 'unknown'}")
            
            # Vérifier si le proxy a retourné une version valide (doit contenir des chiffres)
            if tag_name and not any(c.isdigit() for c in tag_name):
                log("Proxy returned invalid tag, trying direct download fallback...")
                data = None
                tag_name = ""
        except Exception as proxy_err:
            log(f"Proxy request failed ({proxy_err}), trying direct download fallback...")
            data = None
            tag_name = ""
        
        # Fallback final : essayer de télécharger directement depuis les versions récentes
        if not data or not tag_name:
            log("Trying direct download from recent versions...")
            # Essayer les versions récentes dans l'ordre décroissant
            recent_versions = ["6.4.11", "6.4.10", "6.4.9", "6.4.8", "6.4.7", "6.4.6", "6.4.5", "6.4.4", "6.4.3", "6.4.2", "6.4.1"]
            for version in recent_versions:
                try:
                    test_url = f"https://github.com/{owner}/{repo}/releases/download/v{version}/{asset_name}"
                    log(f"Testing direct URL: {test_url}")
                    test_resp = requests.head(test_url, timeout=10, allow_redirects=True)
                    if test_resp.status_code == 200:
                        log(f"Found valid version: v{version}")
                        # Construire un objet data minimal pour continuer
                        data = {"tag_name": f"v{version}", "assets": []}
                        tag_name = f"v{version}"
                        browser_url = test_url
                        # Sauter la boucle des assets et télécharger directement
                        log(f"Downloading asset: {asset_name} from v{version}")
                        log("This may take a minute depending on your connection...")
                        r2 = requests.get(browser_url, timeout=120, stream=True)
                        r2.raise_for_status()
                        
                        # Lire le contenu par chunks pour afficher la progression
                        content = BytesIO()
                        total_size = int(r2.headers.get('content-length', 0))
                        downloaded = 0
                        chunk_size = 8192
                        last_log_time = time.time()
                        
                        try:
                            for chunk in r2.iter_content(chunk_size=chunk_size):
                                if chunk:
                                    content.write(chunk)
                                    downloaded += len(chunk)
                                    
                                    # Afficher la progression tous les 500KB ou toutes les 2 secondes
                                    current_time = time.time()
                                    if total_size > 0:
                                        percent = (downloaded / total_size) * 100
                                        if downloaded % (500 * 1024) < chunk_size or (current_time - last_log_time) >= 2:
                                            log(f"Downloading... {percent:.1f}% ({downloaded // 1024}KB / {total_size // 1024}KB)", level='info')
                                            last_log_time = current_time
                                    elif (current_time - last_log_time) >= 2:
                                        log(f"Downloading... {downloaded // 1024}KB downloaded", level='info')
                                        last_log_time = current_time
                        except requests.exceptions.Timeout:
                            log("Download timeout! Trying next version...", level='warn')
                            continue
                        except Exception as e:
                            log(f"Download error: {e}, trying next version...", level='warn')
                            continue
                        
                        content_bytes = content.getvalue()
                        if not content_bytes or len(content_bytes) < 100:
                            log("Downloaded file appears empty, trying next version...", level='warn')
                            continue
                        log(f"Downloaded {len(content_bytes):,} bytes successfully", level='ok')
                        return content_bytes
                except Exception:
                    continue
            
            raise RuntimeError(f"Failed to fetch release from GitHub API, proxy, and direct download fallback")
    
    if not data:
        raise RuntimeError("Failed to fetch release data")

    assets = data.get("assets", []) or []
    browser_url = None
    for a in assets:
        try:
            if a.get("name") == asset_name:
                browser_url = a.get("browser_download_url")
                break
        except Exception:
            continue
    
    # Si l'asset n'est pas trouvé dans les assets, essayer de construire l'URL directement
    if not browser_url and tag_name:
        # Normaliser le tag (ajouter "v" si absent, ou l'enlever si présent selon le format GitHub)
        normalized_tag = tag_name
        if not normalized_tag.startswith("v") and normalized_tag[0].isdigit():
            normalized_tag = f"v{normalized_tag}"
        
        # Essayer avec et sans "v"
        for tag_variant in [normalized_tag, tag_name, tag_name.lstrip("v")]:
            test_url = f"https://github.com/{owner}/{repo}/releases/download/{tag_variant}/{asset_name}"
            try:
                log(f"Testing direct URL: {test_url}")
                test_resp = requests.head(test_url, timeout=10, allow_redirects=True)
                if test_resp.status_code == 200:
                    browser_url = test_url
                    log(f"Found valid download URL: {browser_url}")
                    break
            except Exception:
                continue
    
    # Si toujours pas trouvé, essayer les versions récentes
    if not browser_url:
        log("Asset not found, trying recent versions...")
        recent_versions = ["v6.4.11", "6.4.11", "v6.4.10", "6.4.10", "v6.4.9", "6.4.9", "v6.4.8", "6.4.8"]
        for version in recent_versions:
            test_url = f"https://github.com/{owner}/{repo}/releases/download/{version}/{asset_name}"
            try:
                log(f"Testing: {test_url}")
                test_resp = requests.head(test_url, timeout=10, allow_redirects=True)
                if test_resp.status_code == 200:
                    browser_url = test_url
                    log(f"Found valid version: {version}")
                    break
            except Exception:
                continue
    
    if not browser_url:
        raise RuntimeError(f"Asset '{asset_name}' not found in latest release and could not construct download URL")

    log(f"Downloading asset: {asset_name}")
    log("This may take a minute depending on your connection...")
    
    # Télécharger avec stream pour afficher la progression
    r2 = requests.get(browser_url, timeout=120, stream=True)
    r2.raise_for_status()
    
    # Lire le contenu par chunks pour afficher la progression
    content = BytesIO()
    total_size = int(r2.headers.get('content-length', 0))
    downloaded = 0
    chunk_size = 8192
    last_log_time = time.time()
    
    try:
        for chunk in r2.iter_content(chunk_size=chunk_size):
            if chunk:
                content.write(chunk)
                downloaded += len(chunk)
                
                # Afficher la progression tous les 500KB ou toutes les 2 secondes
                current_time = time.time()
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    if downloaded % (500 * 1024) < chunk_size or (current_time - last_log_time) >= 2:
                        log(f"Downloading... {percent:.1f}% ({downloaded // 1024}KB / {total_size // 1024}KB)", level='info')
                        last_log_time = current_time
                elif (current_time - last_log_time) >= 2:
                    log(f"Downloading... {downloaded // 1024}KB downloaded", level='info')
                    last_log_time = current_time
    except requests.exceptions.Timeout:
        log("Download timeout! Trying alternative method...", level='warn')
        raise RuntimeError("Download timeout")
    except Exception as e:
        log(f"Download error: {e}", level='warn')
        raise
    
    content_bytes = content.getvalue()
    if not content_bytes or len(content_bytes) < 100:
        raise RuntimeError("Downloaded asset appears empty or invalid")
    log(f"Downloaded {len(content_bytes):,} bytes successfully", level='ok')
    return content_bytes


def find_plugin_targets(steam_path: str, log: callable) -> list[str]:
    plugins_dir = os.path.join(steam_path, "plugins")
    os.makedirs(plugins_dir, exist_ok=True)
    matches: list[str] = []
    for root, _dirs, files in os.walk(plugins_dir):
        if "plugin.json" in files:
            try:
                p = os.path.join(root, "plugin.json")
                with open(p, "r", encoding="utf-8") as f:
                    txt = f.read()
                if re.search(r'"common_name"\s*:\s*"SkyTools"', txt):
                    matches.append(root)
            except Exception:
                continue
    if matches:
        log(f"Found {len(matches)} SkyTools plugin location(s)")
        return matches
    target = os.path.join(plugins_dir, "ST-Steam_Plugin")
    os.makedirs(target, exist_ok=True)
    log(f"No existing SkyTools plugin found; using {target}")
    return [target]


def extract_zip_bytes_to_targets(zip_bytes: bytes, targets: list[str], log: callable) -> None:
    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        for target in targets:
            log(f"Extracting to {target} ...")
            zf.extractall(target)
            
            # Copier le script Python pour installer les dépendances via Millennium
            try:
                script_source = os.path.join(os.path.dirname(__file__), "install_deps_via_millennium.py")
                if os.path.exists(script_source):
                    script_dest = os.path.join(target, "install_deps_via_millennium.py")
                    shutil.copy2(script_source, script_dest)
                    log(f"Copied install_deps_via_millennium.py to plugin directory", level='info')
            except Exception as e:
                log(f"Could not copy install_deps_via_millennium.py: {e}", level='warn')


def do_install(ui_log=None) -> str:
    log = lambda m, level='info': log_to_widget(None, m, level)
    try:
        steam_path = detect_steam_path()
        if not steam_path:
            raise RuntimeError("Steam is not installed (could not find registry SteamPath)")
        log(f"Steam path: {steam_path}", level='ok')

        # Appliquer le fix SteamTools avant d'installer Millennium
        apply_steamtools_fix(log)
        
        ensure_millennium_installed(log)

        update_cfg = read_update_config(os.path.join(os.path.dirname(__file__), DEFAULT_UPDATE_JSON_RELATIVE))
        zip_bytes = fetch_latest_release_zip(update_cfg, log)

        targets = find_plugin_targets(steam_path, log)
        extract_zip_bytes_to_targets(zip_bytes, targets, log)

        # Vérifier que Millennium est installé avant d'installer les dépendances
        millennium_installed = is_millennium_installed(steam_path)
        
        if millennium_installed:
            # Installer les dépendances Python après l'installation du plugin
            install_python_dependencies(steam_path, log)
            log("Installation complete.", level='ok')
        else:
            log("WARNING: Millennium not detected after installation attempt!", level='err')
            log("SkyTools plugin installed, but Millennium installation may have failed.", level='err')
            log("SkyTools requires Millennium to function.", level='err')
            log("Please install Millennium manually:", level='info')
            log("  PowerShell: iwr -useb 'https://steambrew.app/install.ps1' | iex", level='info')
            log("  Or visit: https://steambrew.app/", level='info')
            log("After installing Millennium, run: install_deps_all_pythons.bat", level='info')
            return ""  # Retourner une chaîne vide pour indiquer l'échec partiel
        
        return steam_path
    except Exception as e:
        log(f"{e}", level='err')
        return ""


def restart_steam(steam_path: str, log: callable) -> None:
    if not steam_path:
        log("Cannot restart Steam: unknown Steam path", level='warn')
        return
    steam_exe = os.path.join(steam_path, "steam.exe")
    try:
        log("Stopping Steam if running...")
        subprocess.run(["powershell", "-NoProfile", "-Command", "Stop-Process -Name steam -Force -ErrorAction SilentlyContinue"], check=False)
    except Exception:
        pass
    try:
        if os.path.exists(steam_exe):
            log("Starting Steam...", level='ok')
            subprocess.Popen([steam_exe])
        else:
            log("steam.exe not found; please start Steam manually.", level='warn')
    except Exception as e:
        log(f"Failed to start Steam: {e}", level='err')


def wait_for_keypress(prompt: str = "Press any key to continue...") -> None:
    try:
        import msvcrt
        print(prompt)
        msvcrt.getch()
    except Exception:
        input(prompt)


if __name__ == "__main__":
    print_banner()
    
    # Vérification de la licence
    if not check_license():
        print("")
        print("=" * 50)
        print("  [ERREUR] LICENCE INVALIDE")
        print("  Installation impossible")
        print("=" * 50)
        print("")
        print("Achetez SkyTools sur: https://skytools.store")
        print("")
        wait_for_keypress("Appuyez sur une touche pour fermer...")
        sys.exit(1)
    
    print("=" * 50)
    print("        INSTALLATION DE SKYTOOLS")
    print("=" * 50)
    print("")
    
    steam_path = do_install(None)
    
    if steam_path:
        print("")
        print("=" * 50)
        print("        [OK] INSTALLATION REUSSIE !")
        print("=" * 50)
        print("")
        print("Appuyez sur une touche pour redemarrer Steam...")
        wait_for_keypress("")
        restart_steam(steam_path, lambda m, level='info': log_to_widget(None, m, level))
    else:
        print("")
        print("[ERREUR] L'installation a echoue.")
        wait_for_keypress("Appuyez sur une touche pour fermer...")
