"""
SkyTools License Verification Module
Vérifie la licence au démarrage et bloque le plugin si invalide.
"""

import json
import os
import hashlib
import uuid
import urllib.request
import urllib.error

from logger import logger

# Configuration
LICENSE_API_URL = "https://skytools-license.skytoolskey.workers.dev"
LICENSE_FILE = os.path.join(os.path.expanduser("~"), ".skytools_license")

# État global de la licence
_license_valid = False
_license_error = None


def get_hardware_id() -> str:
    """Génère un ID unique basé sur le matériel de l'ordinateur."""
    try:
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
    except Exception as e:
        logger.error(f"Failed to load license file: {e}")
    return {}


def verify_license_online(key: str, hwid: str) -> dict:
    """Vérifie la licence auprès du serveur."""
    try:
        data = json.dumps({"key": key, "hwid": hwid}).encode('utf-8')
        req = urllib.request.Request(
            f"{LICENSE_API_URL}/plugin-check",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result
            
    except urllib.error.URLError as e:
        logger.warn(f"License server unreachable: {e}")
        return {"valid": False, "error": "NO_CONNECTION"}
    except Exception as e:
        logger.error(f"License verification failed: {e}")
        return {"valid": False, "error": "UNKNOWN"}


# --- LICENSE BYPASS PATCH ---
# This version always returns True to allow free usage for custom builds

def check_license_at_startup() -> bool:
    global _license_valid
    _license_valid = True
    logger.log("SkyTools: License check BYPASSED (Custom Build)")
    return True

def is_license_valid() -> bool:
    """Retourne l'état actuel de la licence."""
    return _license_valid


def get_license_error() -> str:
    """Retourne l'erreur de licence actuelle."""
    return _license_error or ""


def get_license_status() -> dict:
    """Retourne le statut complet de la licence."""
    return {
        "valid": _license_valid,
        "error": _license_error,
        "hwid": get_hardware_id()
    }

