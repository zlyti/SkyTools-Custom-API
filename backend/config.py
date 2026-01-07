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

API_METADATA_URL = "https://raw.githubusercontent.com/zlyti/SkyTools-Custom-API/main/metadata.json"
API_METADATA_FILE = "metadata.json"
CACHE_DB_FILE = "skytools_cache.db"

MORRENUS_API_URL = "https://manifest.morrenus.xyz"
MORRENUS_GAMES_ENDPOINT = f"{MORRENUS_API_URL}/api/games"
MORRENUS_DOWNLOAD_ENDPOINT = f"{MORRENUS_API_URL}/api/download"
MORRENUS_COOKIE = "session=eyJhY2Nlc3NfdG9rZW4iOiAiZXlKaGJHY2lPaUpJVXpJMU5pSXNJblI1Y0NJNklrcFhWQ0o5LmV5SjFjMlZ5WDJsa0lqb2lNVEl6TWpFek5URTBOekUyT0Rjek1URTVNQ0lzSW5WelpYSnVZVzFsSWpvaWVteDVkR2tpTENKa2FYTmpjbWx0YVc1aGRHOXlJam9pTUNJc0ltRjJZWFJoY2lJNkltRmZZVGsyTmpnMk5tVTVPVEEyTkRnM01XUTRNVEE1TWpCbE5UWTRNR0l5WW1ZaUxDSm9hV2RvWlhOMFgzSnZiR1VpT2lKVGIzQm9hV1VnZEdobElFTmhkQ0lzSW5KdmJHVmZiR2x0YVhRaU9qSTFMQ0p5YjJ4bFgyeGxkbVZzSWpveExDSmhiR3hmY205c1pYTWlPbHNpVTI5d2FHbGxJSFJvWlNCRFlYUWlYU3dpWlhod0lqb3hOelkzT0RZeE5EZzVmUS5ILVozMEFZaVB3bTAtY1NSRmp1QTF5RURsM0N5VFpjdTdFdkl2WHNRTVQwIn0=.aV54IQ.1-eT0f63lAyvNzLGg5MHSYa01WQ"
APPID_LOG_FILE = "appid_log.txt"

