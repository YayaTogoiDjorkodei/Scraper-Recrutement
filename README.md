# 🔎 Scraper d'offres d'emploi IT (LinkedIn & Indeed)

Application de bureau (interface **Tkinter**) qui collecte des offres d'emploi IT sur **LinkedIn** et **Indeed**, en extrait automatiquement des informations utiles (technologies, niveau d'études, expérience, type de contrat…) puis exporte le tout dans un fichier **Excel** mis en forme.

> ⚠️ **Usage éducatif / personnel.** Le scraping de LinkedIn et d'Indeed peut contrevenir à leurs conditions d'utilisation. Utilisez ce projet de manière responsable, avec des volumes raisonnables, et à vos propres risques.

---

## ✨ Fonctionnalités

- Interface graphique simple : poste recherché, sélection de plusieurs villes, nombre de pages.
- Liste de villes chargée dynamiquement via l'API **GeoNames** (1000 plus grandes villes).
- Collecte en **deux temps** :
  1. requête HTTP rapide (`requests` + `BeautifulSoup`) ;
  2. si rien n'est récupéré, **repli automatique sur Playwright** (navigateur Chromium headless qui exécute le JavaScript).
- **Rotation de proxies** (choix aléatoire dans `IP_proxies.txt`) et **User-Agent aléatoire** (`fake-useragent`) à chaque requête.
- **Pauses aléatoires** entre les pages (3–8 s) et entre les villes (5–12 s) pour limiter les blocages.
- **Extraction intelligente** du texte de chaque offre avec correspondance floue (`rapidfuzz`) : technologies, niveau d'études, expérience, type de contrat, détection BAC+2 / BAC+5-Master.
- Détection de mécanismes anti-bot (captcha, reCAPTCHA, hCaptcha, Turnstile…).
- Bouton **Arrêter** (thread séparé, l'interface ne se fige pas).
- **Sauvegarde de secours** en CSV si vous fermez la fenêtre sans avoir exporté.
- Export **Excel** stylé : en-têtes colorés, liens cliquables, largeurs de colonnes ajustées.

---

## 📁 Structure du projet

| Fichier | Rôle |
|---|---|
| `main.py` | Application principale pour **LinkedIn** (interface, scraping, export Excel) |
| `indeed.py` | Version adaptée à **Indeed** (même principe, sélecteurs et URL différents) |
| `liste.py` | Listes de référence utilisées pour l'extraction : `technologies`, `niveaux_etudes`, `experience`, `type_contrat`, `niveaux_master`, `mots_technicien` |
| `IP_proxies.txt` | Liste des proxys, un par ligne, au format `ip:port:utilisateur:mot_de_passe` |
| `procyverification.py` | Petit script pour tester qu'un proxy fonctionne (appel à `httpbin.org/ip`) |
| `entretien.py` | Ancienne version de `main.py` (proxys codés en dur) — conservée pour référence |
| `tempCodeRunnerFile.py` | Fichier temporaire de VS Code (URL de test LinkedIn) |
| `Fichier_Scrapinge_Recrutement.xlsx` | Exemple de résultat exporté (feuille `IT Jobs Data`) |
| `Fichier_sauvergarder_sans_exporter.csv` | Sauvegarde automatique des données non exportées |
| `requirements.txt` | Dépendances Python |

---

## 🛠️ Installation

### 1. Prérequis

- **Python 3.10+** (Tkinter est inclus dans l'installation standard de Python)
- Un compte gratuit sur [GeoNames](https://www.geonames.org/login) avec le **service web gratuit activé** (pour la liste des villes)
- Des proxys (optionnel mais recommandé)

### 2. Cloner et installer

```bash
git clone <url-de-votre-depot>
cd <nom-du-dossier>

python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
pip install rapidfuzz        # utilisé par le code, voir remarque ci-dessous
playwright install chromium  # télécharge le navigateur utilisé par Playwright
```

> 📝 **Remarque sur `requirements.txt`** : le code importe `rapidfuzz`, qui n'apparaît pas dans le fichier — d'où l'installation manuelle ci-dessus. Le fichier contient aussi des paquets sans rapport avec ce projet (`mediapipe`, `opencv`, `matplotlib`, `sounddevice`…) que vous pouvez supprimer. Le strict nécessaire est :
> `requests`, `beautifulsoup4`, `lxml`, `pandas`, `openpyxl`, `playwright`, `fake-useragent`, `rapidfuzz`.

### 3. Configurer les proxys

Créez `IP_proxies.txt` à la racine, un proxy par ligne :

```
ip:port:utilisateur:mot_de_passe
```

Testez-en un avec :

```bash
python procyverification.py
```

Vous devez obtenir un code `200` et l'adresse IP du proxy.

### 4. Configurer GeoNames

Dans `main.py` et `indeed.py`, remplacez l'identifiant GeoNames par le vôtre (paramètre `username` de `charger_villes_geonames`). Idéalement, stockez-le dans un fichier `.env` (`python-dotenv` est déjà dans les dépendances) plutôt que dans le code.

---

## ▶️ Utilisation

```bash
python main.py      # LinkedIn
python indeed.py    # Indeed
```

1. Saisissez le **poste recherché** (ex. `Python`, `DevOps`, `Data Engineer`).
2. Cliquez sur **Choisir Ville** et cochez une ou plusieurs villes (champ de recherche intégré).
3. Indiquez le **nombre de pages** (25 offres par page).
4. Cliquez sur **Démarrer**. La barre de statut affiche l'avancement.
5. **Arrêter** interrompt la collecte à la fin de la page en cours.
6. **Exporter** génère `Fichier_Scrapinge_Recrutement.xlsx`.

Si vous fermez la fenêtre avec des données non exportées, l'application propose de les sauvegarder dans `Fichier_sauvergarder_sans_exporter.csv`.

---

## 📊 Colonnes du fichier Excel

| Colonne | Description |
|---|---|
| Company Name | Nom de l'entreprise |
| Job Title | Intitulé du poste |
| City / Region | Localisation |
| Job Link | Lien cliquable vers l'offre |
| Education Level Required | Niveau d'études détecté (ex. `BAC+5-Master`, `BAC+2`) |
| Tech Stack / Skills | Technologies détectées dans l'offre |
| Contract Type | CDI, CDD, stage… |
| Experience Required | Expérience demandée (junior, 2 ans…) |
| Salary | Salaire si affiché |
| source | `linkedin` ou `indeed` |
| Posted Date | Date de publication (ex. « 2 days ago ») |
| Status / Date Detail | Statut de l'offre (Activé / Désactivé) + date |
| Recruiter Contact | Contact du recruteur si disponible |

Les champs non trouvés sont remplis avec `N/A`.

---

## ⚙️ Comment ça marche

```
Interface Tkinter ──► Thread de recherche
                          │
                          ├─ pour chaque ville / chaque page :
                          │     1. requests + proxy + User-Agent aléatoire
                          │     2. si vide → Playwright (Chromium headless)
                          │     3. BeautifulSoup : titre, entreprise, lieu, lien, date…
                          │     4. rapidfuzz : technologies, niveau, expérience, contrat
                          │     5. pause aléatoire
                          ▼
                    Liste de dictionnaires ──► pandas ──► Excel (openpyxl)
```

Pour enrichir l'extraction, il suffit d'ajouter des mots-clés dans les listes de `liste.py`. Le seuil de similarité par défaut est de **88** (85 pour la détection technicien / master).

---

## 🔒 Fichiers sensibles et `.gitignore`

Ne publiez **jamais** vos identifiants de proxy ni votre nom d'utilisateur GeoNames. Le projet ignore déjà :

```
venv/
__pycache__/
*.pyc
*tempCodeRunnerFile.py
*entretien.py
*liste.py
*IP_proxies.txt
```

Points d'attention :

- Le fichier fourni s'appelle `_gitignore` : renommez-le en **`.gitignore`** (avec le point), sinon Git ne le lira pas. Il est aussi encodé en UTF-16 ; enregistrez-le en **UTF-8**.
- `liste.py` est ignoré par Git alors que `main.py` en dépend. Si vous publiez le dépôt, retirez-le du `.gitignore` ou fournissez un `liste.example.py` et un `IP_proxies.example.txt` (sans vrais identifiants).
- `entretien.py` contient des proxys en clair : ne le publiez pas.
- Pensez à ajouter `.env`, `*.xlsx` et `*.csv` au `.gitignore` si vos données ne doivent pas être partagées.
- Si des identifiants de proxy ont déjà été publiés quelque part, **changez-les** chez votre fournisseur.

---

## 🧩 Limites connues

- LinkedIn et Indeed **modifient régulièrement leur HTML** : les sélecteurs CSS peuvent devoir être mis à jour.
- Indeed bloque souvent les navigateurs headless : en cas d'échec, le HTML brut est récupéré pour débogage.
- Seules les informations visibles sur la **page de résultats** sont analysées (pas le descriptif complet de chaque offre), donc certaines colonnes restent à `N/A`.
- La détection du niveau BAC+2 / Master repose sur des mots-clés et peut produire des faux positifs.
- La détection des captchas est présente dans le code mais commentée dans `collecter_donnees_brutes`.

---

## 🚀 Idées d'amélioration

- Dépendances dans un `requirements.txt` propre (UTF-8, `rapidfuzz` inclus, sans paquets inutiles).
- Variables sensibles dans un fichier `.env`.
- Récupération du descriptif complet de chaque offre.
- Suppression des doublons entre plusieurs recherches.
- Fusion de `main.py` et `indeed.py` en un seul programme avec choix de la source.
- Journalisation (`logging`) à la place des `print`.

---


