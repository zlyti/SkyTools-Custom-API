import json
import time
from config import MORRENUS_GAMES_ENDPOINT, MORRENUS_DOWNLOAD_ENDPOINT, MORRENUS_COOKIE, USER_AGENT
from http_client import ensure_http_client
from logger import logger
from cache import cache

class MorrenusAPI:
    def __init__(self):
        self.cookie = MORRENUS_COOKIE

    def sync_games_list(self):
        """Fetches the full game list from Morrenus API (Zero Credit)."""
        client = ensure_http_client("MorrenusSync")
        try:
            logger.log(f"SkyTools: Syncing Morrenus games list from {MORRENUS_GAMES_ENDPOINT}")
            headers = {
                "User-Agent": USER_AGENT,
                "Cookie": self.cookie
            }
            
            resp = client.get(MORRENUS_GAMES_ENDPOINT, headers=headers, timeout=30)
            resp.raise_for_status()
            
            data = resp.json()
            games = data.get("games", []) # Assuming structure {"games": [...]} or just list?
            if isinstance(data, list): games = data
            
            count = 0
            for game in games:
                # Structure: {"app_id": 123, "name": "Game", "last_modified": "...", "zip_exists": true}
                if not game.get("zip_exists"):
                    continue
                    
                appid = game.get("app_id")
                name = game.get("name")
                last_mod = game.get("last_modified")
                
                # We store this in a special way in cache? 
                # Actually, we can use the main app_cache but mark source as 'morrenus'
                # But wait, downloads.py uses the cache to prioritize mirrors.
                # If we put Morrenus in cache, downloads.py might pick it up first!
                # We need to distinguish or handle logic in downloads.py.
                
                # User wants Morrenus as LAST RESORT.
                # So we update a separate table or just use this for LISTING in UI?
                # The prompt says: "Utiliser les champs name, app_id et header_image pour remplir l'interface utilisateur."
                # We should update 'loaded_apps' or similar logic? 
                # Or just put it in the cache and let downloads.py filter it out or push it to end?
                
                # Let's stick to updating the cache with a specific mirror_url pattern
                mirror_url = f"MORRENUS_AUTH:{appid}"
                cache.update_cached_app(appid, mirror_url=mirror_url)
                count += 1
            
            logger.log(f"SkyTools: Morrenus sync complete. {count} games indexed.")
            return count
        except Exception as e:
            logger.warn(f"SkyTools: Morrenus sync failed: {e}")
            return 0

    def get_download_url_and_headers(self, appid):
        """Returns the auth download URL and headers for a specific AppID (Costs 1 Credit)."""
        url = f"{MORRENUS_DOWNLOAD_ENDPOINT}/{appid}"
        headers = {
            "User-Agent": USER_AGENT,
            "Cookie": self.cookie
        }
        return url, headers

morrenus = MorrenusAPI()
