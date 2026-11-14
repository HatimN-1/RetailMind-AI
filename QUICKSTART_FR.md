# Démarrage rapide RetailMind AI V2

Le frontend est désormais **React + TypeScript**, pas Streamlit.

**Dans le dossier `retailmind-ai`**, conserve l'environnement virtuel Python déjà présent :

```powershell
..\.venv\Scripts\python.exe -m pip install -e ".[dev]"
..\.venv\Scripts\python.exe -m retailmind.bootstrap --rows 5000
```

**Terminal 1** (laisser ouvert) :

```powershell
..\.venv\Scripts\python.exe -m uvicorn retailmind.api:app --reload --port 8000
```

**Terminal 2** :

```powershell
cd frontend
node --version
npm --version
npm install
npm run dev
```

Ouvrir **http://localhost:5173** dans le navigateur.

Si `node` ou `npm` ne sont pas reconnus, installer Node.js LTS depuis https://nodejs.org et rouvrir VS Code.
Si l'environnement Python se trouve dans le dossier `retailmind-ai` lui-même, utiliser `.\.venv` au lieu de `..\.venv`.

Le guide adapté à ton installation : **DEMARRAGE_V2_WINDOWS.md**.
