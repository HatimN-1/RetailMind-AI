# RetailMind AI V2 — Guide Windows pour VS Code

Tu as déjà **Python 3.11**, un environnement `.venv` situé dans le **dossier parent** et un backend FastAPI fonctionnel. Cette version **remplace Streamlit par React** : ne réinstalle pas Python.

## Prérequis frontend

Ouvre un terminal VS Code :

```powershell
node -v
npm -v
```

Si l'une des commandes est introuvable, installe Node.js LTS depuis <https://nodejs.org/en/download>, puis ferme et rouvre VS Code. Pour Vite 6 : utiliser une version Node moderne, de préférence 22 LTS ou supérieure compatible. Aucun compte cloud n'est nécessaire.

## Ouvre le bon dossier

Dans VS Code, `File > Open Folder` et choisis **`retailmind-ai`** contenant `pyproject.toml`, `src/` et `frontend/`.

## Méthode recommandée : installation automatique (nouveau dossier ou réutilisation du .venv existant)

Depuis la racine `retailmind-ai`, lance :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1
```

Ce script détecte ton `.venv` dans `retailmind-ai` **ou dans son parent**. S'il n'existe pas, il essaie la version Python 3.11 déjà installée à `C:\Users\pc\AppData\Local\Programs\Python\Python311\python.exe`. Ensuite il installe les dépendances Python, génère les données, exécute les tests et installe les paquets React via npm.

Après cette installation, exécute dans **Terminal 1** :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_api_windows.ps1
```

Dans **Terminal 2** :

```powershell
cd frontend
npm run dev
```

La méthode ci-dessous est la version manuelle si tu souhaites comprendre chaque commande.

## Terminal 1 : backend Python

Depuis `retailmind-ai` lorsque le `.venv` est **dans le dossier parent** :

```powershell
..\.venv\Scripts\python.exe -m pip install -e ".[dev]"
..\.venv\Scripts\python.exe -m retailmind.bootstrap --rows 5000
..\.venv\Scripts\python.exe -m uvicorn retailmind.api:app --reload --port 8000
```

Laisse le terminal ouvert. Vérifie <http://127.0.0.1:8000/health> et <http://127.0.0.1:8000/analytics>.
Si tu conserves le backend du **projet ancien** dans un terminal, arrête-le avec `Ctrl+C` avant de lancer la V2 : sinon le port 8000 est déjà utilisé.

## Terminal 2 : frontend React

```powershell
cd frontend
npm install
npm run dev
```

Ouvre **<http://127.0.0.1:5173>**. Le frontend utilise `/api` ; Vite transfère ces requêtes à FastAPI sur le port 8000.

### Problèmes fréquents

- **`npm n'est pas reconnu`** → Node.js absent du PATH ; installer Node.js LTS et redémarrer VS Code.
- **`EADDRINUSE` / port 5173 occupé** → fermer l'ancien frontend (ou l'autre application Vite), puis relancer.
- **`API non connectée`** → vérifier que le terminal Python affiche `Uvicorn running on http://127.0.0.1:8000`.
- **`Warehouse not initialized`** → relancer le `retailmind.bootstrap`.
- **`Cannot find .venv`** → depuis le sous-dossier `frontend`, revenir au projet avec `cd ..`.
- **Page blanche / TypeScript** → consulter les erreurs du terminal `npm run dev` et vérifier `npm install`.
- **LangGraph optionnel non disponible** → laisser la case LangGraph décochée jusqu'à installation du module Python `.[agent]`.

## Vérifications

Depuis la racine `retailmind-ai` :

```powershell
..\.venv\Scripts\python.exe -m pytest
cd frontend
npm run build
```

L'UI React n'a **pas** besoin de Streamlit. Le `frontend/` et le backend Python restent séparés comme dans une application professionnelle.
