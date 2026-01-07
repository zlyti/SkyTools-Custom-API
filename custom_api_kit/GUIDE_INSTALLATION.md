# Guide d'Installation & Distribution

## Partie 1 : Votre API (Le Menu)
*(Déjà fait normalement)*
1.  Mettez `custom_games.json` et `build_api.py` sur GitHub.
2.  Activez les Actions.
3.  Récupérez le lien `raw` de `api.json`.

## Partie 2 : Distribuer à vos amis (La Livraison)
Pour que vos amis aient votre configuration (et donc votre API) :

### 1. Créer le Paquet
J'ai créé un script `build_release.py` dans votre dossier `custom_api_kit`.
1.  Double-cliquez dessus (ou lancez `python build_release.py` dans le terminal).
2.  Il va créer un dossier `dist` avec :
    *   `skytools_custom.zip` (Votre version modifiée du plugin).
    *   `install_custom.ps1` (L'installateur).

### 2. Mettre en ligne
1.  Allez sur votre GitHub > **Releases** (à droite).
2.  Créez une "New Release" (ex: "v1.0-MyVersion").
3.  Uploadez le fichier `skytools_custom.zip`.
4.  Copiez le lien de téléchargement de ce zip.

### 3. Configurer l'installateur
1.  Ouvrez le fichier `dist/install_custom.ps1` (avec Bloc-notes ou VS Code).
2.  Cherchez la ligne qui commence par `$PluginUrl =` (ou cherchez "github" pour trouver le lien de téléchargement du plugin).
3.  Remplacez le lien officiel par **le lien de VOTRE zip** sur GitHub.
4.  Sauvegardez.

### 4. Partager
Envoyez ce fichier `install_custom.ps1` à vos amis.
Quand ils le lanceront :
- Il téléchargera VOTRE zip.
- Il installera VOTRE config.
- Ils auront VOS jeux + les officiels.
