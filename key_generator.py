"""
SkyTools - Générateur de Clés de Licence
=========================================
Utilisez ce script pour générer des clés de licence valides.
Gardez ce fichier SECRET - ne le partagez jamais !
"""

import random
import string
import hashlib
import sys

# ============== CLÉ SECRÈTE ==============
# IMPORTANT: Ne partagez JAMAIS cette clé !
SECRET_KEY = "SKYTOOLS_2025_ZLYTI_SECRET"


def generate_license_key():
    """Génère une clé de licence valide."""
    # Générer une partie aléatoire
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    
    # Créer le hash de vérification
    data = f"{random_part}{SECRET_KEY}"
    hash_check = hashlib.sha256(data.encode()).hexdigest()[:8].upper()
    
    # Format: XXXX-XXXX-XXXX-HASH
    formatted_random = f"{random_part[:4]}-{random_part[4:8]}-{random_part[8:12]}"
    license_key = f"SKY-{formatted_random}-{hash_check}"
    
    return license_key


def verify_license_key(license_key: str) -> bool:
    """Vérifie si une clé de licence est valide."""
    try:
        # Nettoyer la clé
        key = license_key.strip().upper()
        
        # Vérifier le format
        if not key.startswith("SKY-"):
            return False
        
        parts = key.split("-")
        if len(parts) != 5:
            return False
        
        # Extraire les parties
        random_part = parts[1] + parts[2] + parts[3]
        provided_hash = parts[4]
        
        # Recalculer le hash
        data = f"{random_part}{SECRET_KEY}"
        expected_hash = hashlib.sha256(data.encode()).hexdigest()[:8].upper()
        
        return provided_hash == expected_hash
    except Exception:
        return False


def main():
    print("""
╔═══════════════════════════════════════════════════════════╗
║         SKYTOOLS - GÉNÉRATEUR DE CLÉS DE LICENCE          ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    while True:
        print("\nOptions:")
        print("  1. Générer une clé")
        print("  2. Générer plusieurs clés")
        print("  3. Vérifier une clé")
        print("  4. Quitter")
        
        choice = input("\nChoix (1-4): ").strip()
        
        if choice == "1":
            key = generate_license_key()
            print(f"\n✓ Nouvelle clé générée:")
            print(f"  {key}")
            
        elif choice == "2":
            try:
                count = int(input("Combien de clés ? "))
                if count < 1 or count > 100:
                    print("Entrez un nombre entre 1 et 100")
                    continue
                    
                print(f"\n✓ {count} clés générées:\n")
                keys = []
                for i in range(count):
                    key = generate_license_key()
                    keys.append(key)
                    print(f"  {i+1}. {key}")
                
                # Sauvegarder dans un fichier
                save = input("\nSauvegarder dans un fichier ? (o/n): ").strip().lower()
                if save == 'o':
                    filename = f"skytools_keys_{len(keys)}.txt"
                    with open(filename, "w") as f:
                        for key in keys:
                            f.write(key + "\n")
                    print(f"✓ Clés sauvegardées dans: {filename}")
                    
            except ValueError:
                print("Nombre invalide")
                
        elif choice == "3":
            key = input("Entrez la clé à vérifier: ").strip()
            if verify_license_key(key):
                print("\n✓ Clé VALIDE !")
            else:
                print("\n✗ Clé INVALIDE !")
                
        elif choice == "4":
            print("\nAu revoir!")
            break
        else:
            print("Option invalide")


if __name__ == "__main__":
    main()

