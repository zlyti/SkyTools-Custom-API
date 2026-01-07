"""Central configuration constants for the SkyTools backend."""

WEBKIT_DIR_NAME = "SkyTools"
WEB_UI_JS_FILE = "skytools.js"
WEB_UI_ICON_FILE = "skytools-icon.png"

DEFAULT_HEADERS = {
    "Accept": "application/json",
    "X-Requested-With": "SteamDB",
    "User-Agent": "https://github.com/BossSloth/Steam-SteamDB-extension",
    "Origin": "https://github.com/BossSloth/Steam-SteamDB-extension",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
}

API_MANIFEST_URL = "https://raw.githubusercontent.com/zlyti/SkyTools-Custom-API/main/api.json"
API_MANIFEST_PROXY_URL = "https://skytools.vercel.app/load_free_manifest_apis"
API_JSON_FILE = "api.json"

UPDATE_CONFIG_FILE = "update.json"
UPDATE_PENDING_ZIP = "update_pending.zip"
UPDATE_PENDING_INFO = "update_pending.json"

HTTP_TIMEOUT_SECONDS = 15
HTTP_PROXY_TIMEOUT_SECONDS = 15
UPDATE_DOWNLOAD_TIMEOUT_SECONDS = 120  # 2 minutes pour les téléchargements de mises à jour

UPDATE_CHECK_INTERVAL_SECONDS = 2 * 60 * 60  # 2 hours

USER_AGENT = "skytools-v61-stplugin-hoe"

LOADED_APPS_FILE = "loadedappids.txt"
APPID_LOG_FILE = "appidlogs.txt"

