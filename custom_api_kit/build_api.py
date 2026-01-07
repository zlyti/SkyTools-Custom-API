import json
import urllib.request
import os

# Configuration
OFFICIAL_API_URL = "https://raw.githubusercontent.com/madoiscool/lt_api_links/refs/heads/main/load_free_manifest_apis"
OUTPUT_FILE = "api.json"
# Dynamic URL pattern for your custom games
# SkyTools replaces <appid> with the actual game ID
CUSTOM_REPO_ENTRY = {
    "name": "Alucard Custom Repo",
    "url": "https://raw.githubusercontent.com/zlyti/SkyTools-Custom-API/main/games/<appid>.zip",
    "success_code": 200,
    "unavailable_code": 404,
    "enabled": True
}

# Community ManifestHub Sources (Direct GitHub Access - Bypass 25/day limit)
# These repositories store manifests in branches matching the AppID.
COMMUNITY_SOURCES = [
    {
        "name": "ManifestHub (SteamAutoCracks)",
        "url": "https://github.com/SteamAutoCracks/ManifestHub/archive/refs/heads/<appid>.zip",
        "success_code": 200,
        "unavailable_code": 404,
        "enabled": True
    },
    {
        "name": "ManifestHub Mirror (ikun0014)",
        "url": "https://github.com/ikun0014/ManifestHub/archive/refs/heads/<appid>.zip",
        "success_code": 200,
        "unavailable_code": 404,
        "enabled": True
    },
    {
        "name": "ManifestAutoUpdate (Auiowu)",
        "url": "https://github.com/Auiowu/ManifestAutoUpdate/archive/refs/heads/<appid>.zip",
        "success_code": 200,
        "unavailable_code": 404,
        "enabled": True
    },
    {
        "name": "ManifestHub Fix (tymolu233)",
        "url": "https://github.com/tymolu233/ManifestAutoUpdate-fix/archive/refs/heads/<appid>.zip",
        "success_code": 200,
        "unavailable_code": 404,
        "enabled": True
    }
]

def main():
    print(f"--- SkyTools API Builder ---")
    
    # 1. Load Official API List
    print(f"Fetching official list from: {OFFICIAL_API_URL}")
    official_list = []
    try:
        # Use a User-Agent to avoid being blocked by GitHub
        req = urllib.request.Request(
            OFFICIAL_API_URL, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req) as response:
            content = response.read().decode()
            # Handle potential JSON wrapping (some files are raw lists, some are objects)
            # The file we checked starts with "api_list": [ ... but is it a valid JSON object?
            # The content I saw earlier was just a fragment? Let's assume it's valid JSON.
            # Wait, the read tool showed: "api_list": [ ... ]
            # That implies the root is an object { "api_list": [...] }
            # But the read tool output might have been partial or the file structure is implicit.
            # Let's clean it up just in case.
            
            # Clean up content
            content = content.replace('\r\n', '\n').strip()
            
            # If it's the specific fragment format from madoiscool
            if content.startswith('"api_list"'):
                 # Remove trailing comma if exists (common JSON error in manual files)
                 if content.endswith(','):
                     content = content[:-1]
                 content = "{" + content + "}"
            
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    official_list = data.get("api_list", [])
                elif isinstance(data, list):
                    official_list = data
                print(f"SUCCESS: Loaded {len(official_list)} official APIs.")
            except json.JSONDecodeError as e:
                print(f"JSON PARSE ERROR: {e}")
                print(f"Snippet: {content[:100]}...{content[-50:]}")
                official_list = []
    except Exception as e:
        print(f"ERROR: Could not fetch official list: {e}")
        official_list = []

    # 2. Build Final List
    # Order: Custom Repo -> Community Hubs -> Official APIs
    final_list = [CUSTOM_REPO_ENTRY] + COMMUNITY_SOURCES + official_list
    
    final_structure = {
        "api_list": final_list
    }

    # 3. Save
    print(f"Saving merged list to: {OUTPUT_FILE}")
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(final_structure, f, indent=4)
        print(f"DONE! Total APIs in list: {len(final_list)}")
    except Exception as e:
        print(f"ERROR: Could not write output file: {e}")

if __name__ == "__main__":
    main()
