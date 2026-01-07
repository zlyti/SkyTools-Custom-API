
import os
import shutil
import zipfile
import datetime

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR) # "custom_api_kit" -> "skytools-updater"

PLUGIN_SOURCE = os.path.join(PROJECT_ROOT, "backend")
INSTALLER_SOURCE = os.path.join(PROJECT_ROOT, "install.ps1")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "dist")
ZIP_NAME = "skytools_custom.zip"

def create_dist():
    print("--- SkyTools Custom Release Builder ---")
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    # 1. Zip the plugin files (backend) which contains your modified config.py
    print(f"Zipping plugin files from {PLUGIN_SOURCE}...")
    zip_path = os.path.join(OUTPUT_DIR, ZIP_NAME)
    
    # Exclude __pycache__ and other junk
    def zip_filter(path, names):
        ignore = []
        if "__pycache__" in names: ignore.append("__pycache__")
        return ignore

    # Manually zipping is safer to control structure
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add backend folder as root
        # Actually standard SkyTools zip structure usually has the contents directly or inside a folder?
        # Looking at install.ps1: Expand-Archive ... -DestinationPath .../ST-Steam_Plugin
        # So we should zip the CONTENTS of backend.
        
        for root, dirs, files in os.walk(PLUGIN_SOURCE):
            # Filtering
            if "__pycache__" in root: continue
            
            for file in files:
                if file.endswith(".pyc"): continue
                
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, PLUGIN_SOURCE)
                zipf.write(abs_path, rel_path)
                
    print(f"Created {zip_path}")
    
    # 2. Copy the installer
    dest_installer = os.path.join(OUTPUT_DIR, "install_custom.ps1")
    shutil.copy(INSTALLER_SOURCE, dest_installer)
    print(f"Copied installer to {dest_installer}")
    
    print("\n--- DONE ---")
    print(f"1. Upload '{ZIP_NAME}' to your GitHub Releases.")
    print(f"2. Edit '{dest_installer}' to point to your GitHub Release link.")
    print(f"3. Share '{dest_installer}' with your friends.")

if __name__ == "__main__":
    create_dist()
