import json
import os
import re
import sys
import time
import zipfile
import subprocess
from io import BytesIO

import requests


GITHUB_API = "https://api.github.com"
DEFAULT_UPDATE_JSON_RELATIVE = os.path.join("backend", "update.json")

# --------------- Pretty logging ---------------
ENABLE_COLOR = sys.stdout.isatty()
CLR = {
    'reset': "\033[0m" if ENABLE_COLOR else "",
    'dim': "\033[2m" if ENABLE_COLOR else "",
    'cyan': "\033[36m" if ENABLE_COLOR else "",
    'green': "\033[32m" if ENABLE_COLOR else "",
    'yellow': "\033[33m" if ENABLE_COLOR else "",
    'red': "\033[31m" if ENABLE_COLOR else "",
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
        # Always print to stdout for CLI usage
        print(line, end="")
    except Exception:
        print(line, end="")


def detect_steam_path() -> str:
    steam_path = None
    try:
        import winreg  # type: ignore

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
        log("Ensuring Millennium is installed (this is safe to re-run)...")
        cmd = (
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "iwr -useb 'https://steambrew.app/install.ps1' | iex",
        )
        completed = subprocess.run(cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
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
        # Fallback default matching repo layout
        return {
            "github": {
                "owner": "zlyti",
                "repo": "skytools-steam-plugin",
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
    # Fallback: create default target
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
        import msvcrt  # type: ignore
        print(prompt)
        msvcrt.getch()
    except Exception:
        # Fallback
        input(prompt)

if __name__ == "__main__":
    # Pure CLI entrypoint
    steam_path = do_install(None)
    if steam_path:
        print()
        print(f"{CLR['green']}Done!{CLR['reset']} {CLR['dim']}Press any key to restart Steam and apply changes!{CLR['reset']}")
        wait_for_keypress("")
        restart_steam(steam_path, lambda m, level='info': log_to_widget(None, m, level))


