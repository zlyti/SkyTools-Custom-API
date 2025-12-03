import json
import os
import re
import sys
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
SECRET_KEY = "SKYTOOLS_2025_ZLYTI_SECRET"
LICENSE_FILE = os.path.join(os.path.expanduser("~"), ".skytools_license")

# --------------- Pretty logging ---------------
ENABLE_COLOR = sys.stdout.isatty()
CLR = {
    'reset': "\033[0m" if ENABLE_COLOR else "",
    'dim': "\033[2m" if ENABLE_COLOR else "",
    'cyan': "\033[36m" if ENABLE_COLOR else "",
    'green': "\033[32m" if ENABLE_COLOR else "",
    'yellow': "\033[33m" if ENABLE_COLOR else "",
    'red': "\033[31m" if ENABLE_COLOR else "",
    'magenta': "\033[35m" if ENABLE_COLOR else "",
}


def log_to_widget(widget, message: str, level: str = 'info') -> None:
    ts = time.strftime("%H:%M:%S")
    badge = {
        'info': f"{CLR['cyan']}INFO{CLR['reset']}",
        'ok': f"{CLR['green']} OK {CLR['reset']}",
        'warn': f"{CLR['yellow']}WARN{CLR['reset']}",
        'err': f"{CLR['red']}ERR {CLR['reset']}",
    }.get(level, f"{CLR['cyan']}INFO{CLR['reset']}")
    line = f"[{ts}] {badge} {message}\n"
    try:
        print(line, end="")
    except Exception:
        print(line, end="")


def print_banner():
    banner = f"""
{CLR['cyan']}╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   {CLR['magenta']}███████╗██╗  ██╗██╗   ██╗████████╗ ██████╗  ██████╗ ██╗     ███████╗{CLR['cyan']}
║   {CLR['magenta']}██╔════╝██║ ██╔╝╚██╗ ██╔╝╚══██╔══╝██╔═══██╗██╔═══██╗██║     ██╔════╝{CLR['cyan']}
║   {CLR['magenta']}███████╗█████╔╝  ╚████╔╝    ██║   ██║   ██║██║   ██║██║     ███████╗{CLR['cyan']}
║   {CLR['magenta']}╚════██║██╔═██╗   ╚██╔╝     ██║   ██║   ██║██║   ██║██║     ╚════██║{CLR['cyan']}
║   {CLR['magenta']}███████║██║  ██╗   ██║      ██║   ╚██████╔╝╚██████╔╝███████╗███████║{CLR['cyan']}
║   {CLR['magenta']}╚══════╝╚═╝  ╚═╝   ╚═╝      ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝╚══════╝{CLR['cyan']}
║                                                           ║
║              {CLR['green']}Steam Plugin Installer v1.0{CLR['cyan']}                  ║
╚═══════════════════════════════════════════════════════════╝{CLR['reset']}
"""
    print(banner)


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


def verify_license_key(license_key: str) -> bool:
    """Vérifie si une clé de licence est valide (format)."""
    try:
        key = license_key.strip().upper()
        
        if not key.startswith("SKY-"):
            return False
        
        parts = key.split("-")
        if len(parts) != 5:
            return False
        
        random_part = parts[1] + parts[2] + parts[3]
        provided_hash = parts[4]
        
        data = f"{random_part}{SECRET_KEY}"
        expected_hash = hashlib.sha256(data.encode()).hexdigest()[:8].upper()
        
        return provided_hash == expected_hash
    except Exception:
        return False


def load_saved_license() -> dict:
    """Charge les données de licence sauvegardées."""
    try:
        if os.path.exists(LICENSE_FILE):
            with open(LICENSE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_license(license_key: str, hwid: str) -> None:
    """Sauvegarde la clé de licence avec le HWID."""
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


def check_license() -> bool:
    """Vérifie si l'utilisateur a une licence valide."""
    print(f"\n{CLR['cyan']}═══════════════════════════════════════════════════════════{CLR['reset']}")
    print(f"{CLR['yellow']}           VÉRIFICATION DE LA LICENCE{CLR['reset']}")
    print(f"{CLR['cyan']}═══════════════════════════════════════════════════════════{CLR['reset']}\n")
    
    current_hwid = get_hardware_id()
    saved_data = load_saved_license()
    
    # Vérifier si une licence est déjà activée sur cet ordinateur
    if saved_data:
        saved_key = saved_data.get("key", "")
        saved_hwid = saved_data.get("hwid", "")
        
        print(f"{CLR['dim']}Licence trouvée, vérification...{CLR['reset']}")
        
        # Vérifier que la clé est valide
        if not verify_license_key(saved_key):
            print(f"{CLR['red']}✗ Clé de licence corrompue.{CLR['reset']}\n")
        # Vérifier que le HWID correspond (même ordinateur)
        elif saved_hwid != current_hwid:
            print(f"{CLR['red']}✗ Cette licence est activée sur un autre ordinateur.{CLR['reset']}")
            print(f"{CLR['yellow']}  Chaque licence ne peut être utilisée que sur UN seul PC.{CLR['reset']}\n")
            return False
        else:
            print(f"\n{CLR['green']}✓ Licence valide !{CLR['reset']}")
            print(f"{CLR['dim']}  ID Machine: {current_hwid}{CLR['reset']}\n")
            return True
    
    # Demander une nouvelle clé
    print(f"{CLR['yellow']}Entrez votre clé de licence SkyTools:{CLR['reset']}")
    print(f"{CLR['dim']}(Format: SKY-XXXX-XXXX-XXXX-XXXXXXXX){CLR['reset']}")
    print(f"{CLR['dim']}Achetez sur: https://zlyti.github.io/skytools-updater{CLR['reset']}\n")
    print(f"{CLR['yellow']}⚠ ATTENTION: La clé sera liée à CET ordinateur uniquement !{CLR['reset']}\n")
    
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            license_key = input(f"{CLR['cyan']}Clé: {CLR['reset']}").strip().upper()
        except (EOFError, KeyboardInterrupt):
            return False
        
        if not license_key:
            print(f"{CLR['red']}Aucune clé entrée.{CLR['reset']}")
            continue
        
        if verify_license_key(license_key):
            # Sauvegarder avec le HWID actuel
            save_license(license_key, current_hwid)
            
            print(f"\n{CLR['green']}✓ Licence activée avec succès !{CLR['reset']}")
            print(f"{CLR['dim']}  Clé liée à cet ordinateur (ID: {current_hwid}){CLR['reset']}")
            print(f"{CLR['yellow']}  ⚠ Cette clé ne fonctionnera plus sur un autre PC.{CLR['reset']}\n")
            return True
        else:
            remaining = max_attempts - attempt - 1
            if remaining > 0:
                print(f"{CLR['red']}✗ Clé invalide. {remaining} tentative(s) restante(s).{CLR['reset']}\n")
            else:
                print(f"{CLR['red']}✗ Clé invalide. Plus de tentatives.{CLR['reset']}\n")
    
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


def ensure_millennium_installed(log: callable) -> None:
    steam_path = detect_steam_path()
    if not steam_path:
        log("Steam path not found in registry; continuing anyway.")

    marker_guess = os.path.join(steam_path or "", "steamui")
    already_present = os.path.isdir(marker_guess)
    if already_present:
        log(f"Detected Steam UI directory: {marker_guess}")

    try:
        log("Checking/Installing Millennium...")
        cmd = (
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "iwr -useb 'https://steambrew.app/install.ps1' | iex",
        )
        completed = subprocess.run(cmd, check=False)
        if completed.returncode == 0:
            log("Millennium installation step finished.", level='ok')
        else:
            log("Millennium install step returned a non-zero exit code (continuing)", level='warn')
    except Exception as e:
        log(f"Millennium install step failed (non-fatal): {e}", level='warn')


def read_update_config(config_path: str) -> dict:
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "github": {
                "owner": "zlyti",
                "repo": "skytools-updater",
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
    resp = requests.get(f"{GITHUB_API}/repos/{owner}/{repo}/releases/latest", headers=headers, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    tag_name = str(data.get("tag_name", "")).strip()
    log(f"Latest tag: {tag_name or 'unknown'}")

    assets = data.get("assets", []) or []
    browser_url = None
    for a in assets:
        try:
            if a.get("name") == asset_name:
                browser_url = a.get("browser_download_url")
                break
        except Exception:
            continue
    if not browser_url:
        raise RuntimeError(f"Asset '{asset_name}' not found in latest release")

    log(f"Downloading asset: {asset_name}")
    r2 = requests.get(browser_url, timeout=60, stream=True)
    r2.raise_for_status()
    content = r2.content
    if not content or len(content) < 100:
        raise RuntimeError("Downloaded asset appears empty or invalid")
    log(f"Downloaded {len(content):,} bytes")
    return content


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


def do_install(ui_log=None) -> str:
    log = lambda m, level='info': log_to_widget(None, m, level)
    try:
        steam_path = detect_steam_path()
        if not steam_path:
            raise RuntimeError("Steam is not installed (could not find registry SteamPath)")
        log(f"Steam path: {steam_path}", level='ok')

        ensure_millennium_installed(log)

        update_cfg = read_update_config(os.path.join(os.path.dirname(__file__), DEFAULT_UPDATE_JSON_RELATIVE))
        zip_bytes = fetch_latest_release_zip(update_cfg, log)

        targets = find_plugin_targets(steam_path, log)
        extract_zip_bytes_to_targets(zip_bytes, targets, log)

        log("Installation complete.", level='ok')
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
        print(f"\n{CLR['red']}════════════════════════════════════════════════════════{CLR['reset']}")
        print(f"{CLR['red']}  LICENCE INVALIDE - Installation impossible{CLR['reset']}")
        print(f"{CLR['red']}════════════════════════════════════════════════════════{CLR['reset']}")
        print(f"\n{CLR['yellow']}Achetez SkyTools sur:{CLR['reset']}")
        print(f"{CLR['cyan']}https://zlyti.github.io/skytools-updater{CLR['reset']}\n")
        wait_for_keypress("Appuyez sur une touche pour fermer...")
        sys.exit(1)
    
    print(f"{CLR['cyan']}═══════════════════════════════════════════════════════════{CLR['reset']}")
    print(f"{CLR['yellow']}              INSTALLATION DE SKYTOOLS{CLR['reset']}")
    print(f"{CLR['cyan']}═══════════════════════════════════════════════════════════{CLR['reset']}\n")
    
    steam_path = do_install(None)
    
    if steam_path:
        print()
        print(f"{CLR['green']}═══════════════════════════════════════════════════════════{CLR['reset']}")
        print(f"{CLR['green']}              INSTALLATION RÉUSSIE !{CLR['reset']}")
        print(f"{CLR['green']}═══════════════════════════════════════════════════════════{CLR['reset']}")
        print(f"\n{CLR['dim']}Appuyez sur une touche pour redémarrer Steam...{CLR['reset']}")
        wait_for_keypress("")
        restart_steam(steam_path, lambda m, level='info': log_to_widget(None, m, level))
    else:
        print(f"\n{CLR['red']}L'installation a échoué.{CLR['reset']}")
        wait_for_keypress("Appuyez sur une touche pour fermer...")
