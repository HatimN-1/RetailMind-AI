# RetailMind AI 3.0 â€” Professional Analytics & Governed AI

La V3 conserve les donnÃ©es et les modÃ¨les V2 et complÃ¨te lâ€™investigation : workflow LangGraph
Ã  neuf nÅ“uds, Qdrant persistant avec embeddings multilingues, preuves SQL et synthÃ¨se
extractive Ollama facultative. Aucun bootstrap ni rÃ©entraÃ®nement nâ€™est nÃ©cessaire sur ce workspace.

- [DÃ©marrage V3 Windows et dÃ©pannage](docs/V3_GUIDE_WINDOWS.md)
- [Architecture RAG, workflow et sÃ©curitÃ©](docs/architecture/RAG_V3.md)
- [Protocole et mesures rÃ©ellement exÃ©cutÃ©es](docs/evaluation/README.md)
- [Rapport de livraison et inventaire des fichiers](docs/V3_RAPPORT.md)
- [Correctif Investigation : cause, tests HTTP et navigateur](docs/INVESTIGATION_V3_CORRECTIF.md)

Le guide V3 utilise `npm.cmd` si PowerShell bloque `npm.ps1`, ainsi quâ€™un dossier temporaire
local pour les tests. Les instructions V2 ci-dessous restent disponibles pour lâ€™historique.

**Portfolio technique : Hatim Nadir Â· ENSA FÃ¨s Â· 2026â€“2027**

**NOUVELLE VERSION : React + TypeScript + Vite + Recharts, sans Streamlit.**
Lâ€™application est une plateforme Data Engineering / Data Science / IA sur des transactions **exclusivement synthÃ©tiques**.
Elle conserve le backend FastAPI, les jeux gÃ©nÃ©rÃ©s, les modÃ¨les et lâ€™agent de diagnostic gouvernÃ©.

## Lancer dans VS Code sur Windows (Python dÃ©jÃ  installÃ©)

**Le plus simple :** depuis le dossier `retailmind-ai` dÃ©compressÃ©, exÃ©cuter
`powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1`.
Le script rÃ©utilise un `.venv` existant dans le dossier ou le parent, et installe les dÃ©pendances React si npm est disponible.
Lancer ensuite `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_api_windows.ps1` dans un terminal,
puis `cd frontend; npm run dev` dans un second terminal. Voir `DEMARRAGE_V2_WINDOWS.md`.


1. DÃ©compresser le ZIP puis ouvrir le dossier `retailmind-ai` dans VS Code.
2. VÃ©rifier que Node.js (version **20.19+ ou 22.12+**) est disponible : `node -v` et `npm -v`.
   Si besoin, installer la version LTS depuis https://nodejs.org puis **redÃ©marrer VS Code**.
3. Dans le terminal PowerShell, depuis `retailmind-ai` :

```powershell
# Environnement virtuel Python dÃ©jÃ  crÃ©Ã© dans le dossier parent ? On le conserve :
..\.venv\Scripts\python.exe -m pip install -e ".[dev]"
# Si .venv est au mÃªme niveau que pyproject.toml, remplacer ..\.venv par .\.venv
..\.venv\Scripts\python.exe -m retailmind.bootstrap --rows 5000
..\.venv\Scripts\python.exe -m pytest
```

4. **Terminal 1 (FastAPI)**, depuis `retailmind-ai` :

```powershell
..\.venv\Scripts\python.exe -m uvicorn retailmind.api:app --reload --port 8000
```

5. **Terminal 2 (React)** :

```powershell
cd frontend
npm install
npm run dev
```

**Application web : http://localhost:5173**
**API Swagger : http://localhost:8000/docs**

La commande `npm install` installe les bibliothÃ¨ques JavaScript, dont Recharts et React.
Ne pas essayer de lancer `src/retailmind/dashboard.py` : Streamlit a Ã©tÃ© supprimÃ© dans cette version.

### Lancement automatique possible

- VS Code â†’ Terminal â†’ **Run Task** â†’ `RetailMind: API Windows` et `RetailMind: React Frontend`.
- Les scripts PowerShell cherchent `.venv` dans le dossier du projet **ou son parent**.
- Pour les dÃ©tails prÃ©cis adaptÃ©s Ã  ton PC, lire **`DEMARRAGE_V2_WINDOWS.md`**.

## Ce qui change dans la V2

| Partie | FonctionnalitÃ©s |
|---|---|
| **React UI** | Sidebar, thÃ¨me clair/sombre, navigation, indicateurs, composants responsives |
| **Analyse** | Graphiques Recharts, filtres 7/30 jours/global, revenus par rÃ©gion et catÃ©gorie |
| **Transactions** | Recherche SQL, filtres, tris, pagination et panneau de dÃ©tails |
| **Anomalies** | Typologie, filtres et inspection ; les labels sont des scÃ©narios synthÃ©tiques |
| **Investigation IA** | Interface conversationnelle, prompts suggÃ©rÃ©s, preuves structurÃ©es, sources locales |
| **QualitÃ© & ML** | ContrÃ´les qualitÃ© et comparaison de performances Isolation Forest / PyTorch |
| **FastAPI** | Nouvelles routes `/analytics`, `/transactions-page`, `/alerts-page` |
| **Docker** | Nouveau service Nginx servant lâ€™application React et relayant `/api/` |

## DÃ©marrage Docker (Docker Desktop requis)

```bash
docker compose up --build
```

Application : **http://127.0.0.1:5173**
API : **http://127.0.0.1:8000/docs**

> Docker, les builds npm et les dÃ©ploiements cloud n'ont pas pu Ãªtre exÃ©cutÃ©s dans l'environnement de gÃ©nÃ©ration de cette archive ; les scripts et configurations sont fournis pour exÃ©cution et vÃ©rification sur ta machine.

## API de dÃ©monstration

- `/health`, `/ready` â€” statut de l'API et du warehouse
- `/metrics` â€” KPI historiques (rÃ©trocompatibilitÃ©)
- `/analytics?period=7d|30d|all` â€” agrÃ©gations et sÃ©ries chronologiques
- `/transactions-page` â€” recherche, pagination, tri et filtres
- `/alerts-page` â€” Ã©tiquettes d'anomalies simulÃ©es, paginÃ©es
- `/quality` et `/model-evaluation` â€” rÃ©sultats de rÃ©fÃ©rence
- `/investigate` â€” investigation locale en lecture seule (LangGraph optionnel)
- `/predict` â€” infÃ©rence Isolation Forest d'aprÃ¨s les features fournis

Le Vite dev-server envoie `/api/...` Ã  `127.0.0.1:8000`. Dans Docker, Nginx fait de mÃªme via le service `api`.
Les routes d'analytique interrogent SQLite en mode lecture seule avec requÃªtes paramÃ©trÃ©es.

## Extensions du projet original prÃ©servÃ©es

PySpark, Airflow, dbt/DuckDB, PyTorch, LangGraph, Qdrant, CI GitHub Actions, Azure Pipelines, Kubernetes et Terraform. Voir `docs/ROADMAP.md`, `docs/architecture/ARCHITECTURE.md` et `docs/runbooks/`.

Pour les dÃ©pendances Python optionnelles : `pip install -e ".[deep]"`, `.[spark]`, `.[analytics]`, `.[agent]`, `.[rag]`.
Les modules optionnels ne sont pas automatiquement activÃ©s par le frontend React.

## SÃ©curitÃ© et validitÃ© scientifique

- **Aucune donnÃ©e rÃ©elle** : toutes les transactions, clients et anomalies sont fictifs.
- Les 334 anomalies de la dÃ©monstration sont des **labels injectÃ©s**, pas des cas rÃ©els de fraude.
- Les mÃ©triques des modÃ¨les ne mesurent pas une performance rÃ©elle de production.
- Le backend de dÃ©monstration n'a **pas d'authentification de production** : le maintenir sur localhost ou derriÃ¨re un dispositif sÃ©curisÃ©.
- L'agent ne peut ni exÃ©cuter de commande systÃ¨me, ni modifier les pipelines, ni Ã©crire arbitrairement dans SQL.
- L'application n'exige aucune clÃ© API pour le parcours dÃ©terministe.

**RÃ©sultats de rÃ©fÃ©rence livrÃ©s** : 5 000 transactions uniques, 25 doublons Ã©liminÃ©s, 334 anomalies injectÃ©es, 15 tests Python rÃ©ussis, incluant les 4 tests des nouvelles routes backend. Reproduire sur ton PC avant de citer dans un CV.
