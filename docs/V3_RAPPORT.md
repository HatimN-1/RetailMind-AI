# Rapport de livraison RetailMind AI V3

Livraison locale du 14 novembre 2026. Projet académique, transactions et anomalies exclusivement synthétiques.

## 1. Architecture avant/après

La V2 proposait TF-IDF sur documents entiers, une intégration Qdrant optionnelle destructive à la
réindexation, deux nœuds LangGraph et une synthèse Ollama libre non vérifiée. La V3 conserve
FastAPI/SQLite, React/TypeScript, les routes existantes, le design sombre/clair et les modèles entraînés.

Le retrieval utilise maintenant un tokenizer réel, des chunks avec chevauchement, un checkpoint
multilingue épinglé, des payloads traçables, une publication par alias Qdrant et un fallback TF-IDF explicite.
Le workflow LangGraph exécute neuf responsabilités séparées. Ollama est facultatif et sélectionne
des extraits référencés ; le serveur conserve les faits SQL et recopie les citations originales.
Le [schéma détaillé et les contrats de chaque nœud](architecture/RAG_V3.md) décrivent les choix et limites.

## 2. Fonctionnalités implémentées

- Indexation locale d’administration, sans endpoint HTTP d’écriture ; réindexation idempotente,
  collections provisoires, vérification des points, conservation de l’index actif en cas d’erreur.
- Qdrant local persistant ou serveur configuré par URL ; contrôle de l’identité du modèle, des dimensions,
  de l’empreinte du corpus et du texte exact des chunks ; aucun téléchargement pendant une requête HTTP.
- Recherche sémantique, avec filtrage documentaire quand un composant est explicitement nommé.
- Workflow réel LangGraph, parcours déterministes, refus avant outils, contexte et étapes bornés,
  traces de nœuds, corrélation, latence et limites explicites.
- SQL strictement en lecture seule : trois templates fixes, paramètres liés, `mode=ro`, `query_only`, timeout.
- Synthèse extractive Ollama avec JSON Schema, température 0 et seed 42 ; candidat non vérifiable rejeté.
- Contrat `/investigate` enrichi sans suppression des champs V2, validation Pydantic stricte,
  statuts et documents accessibles uniquement en lecture.
- React : conversation, chargement, erreurs, faits/hypothèses/vérifications/sources, tables SQL,
  documents complets, scores et chunks, chronologie et statuts des services réellement vérifiés.
- Évaluation reproductible, tests de sécurité et d’indisponibilité, scripts Windows et tâches VS Code.

## 3. Fichiers modifiés et créés

Fichiers existants modifiés :

- `pyproject.toml`, `.env.example`, `.gitignore`, `README.md`.
- `src/retailmind/retrieval.py`, `agent.py`, `api.py`, `warehouse.py`, `settings.py`, `cli.py`.
- `src/retailmind/train.py` : suppression d’un import inutilisé uniquement, aucun changement d’algorithme.
- `frontend/src/pages/Investigation.tsx`, `frontend/src/api.ts`, `frontend/src/types.ts`, `frontend/src/styles.css`.
- `scripts/run_tests_windows.ps1`, `.vscode/tasks.json`, `.github/workflows/ci.yml`.
- `tests/test_generator.py`, `tests/test_optional_torch.py`, `tests/test_pipeline_api.py` : nettoyage
  d’imports/variable inutilisés signalés par Ruff ; scénarios de test conservés.

Fichiers source ou documentation créés :

- `src/retailmind/rag_evaluation.py`.
- `tests/test_rag_v3.py`, `tests/test_investigation_v3.py`, `tests/test_rag_evaluation.py`.
- `tests/fixtures/rag_questions.json` : 18 questions annotées et un contrôle hors périmètre.
- `scripts/setup_rag_windows.ps1`, `scripts/index_rag_windows.ps1`, `scripts/evaluate_rag_windows.ps1`,
  `scripts/smoke_v3.py`.
- `docs/V3_GUIDE_WINDOWS.md`, `docs/architecture/RAG_V3.md`, `docs/evaluation/README.md`, `docs/V3_RAPPORT.md`.
- `docs/evaluation/tfidf_v3.json`, `qdrant_dense_baseline_v3.json`, `qdrant_v3.json`,
  `ollama_smoke_v3.json`, `api_smoke_v3.json`, `runtime_versions_v3.json`, `ml_reference_manifest_v3.json`.

Artefacts locaux : `.env` créé sans secret pour activer Qdrant, `data/embedding_cache/`,
`data/qdrant_local/`, `.test-temp/` et `frontend/dist/` généré par le build. Le cache et les données locales
sont ignorés par Git. Le dossier fourni n’est pas un dépôt Git détectable ; aucun commit n’a été créé.
Aucun runbook existant n’a été modifié et aucune donnée ni aucun modèle existant n’a été supprimé.

## 4. Dépendances et modèles

Installation réellement exécutée dans `.venv` : `qdrant-client==1.20.0`,
`sentence-transformers==5.7.0` et leurs dépendances transitives.
LangGraph 1.2.22, PyTorch 2.15.0 et python-dotenv 1.2.4 étaient déjà présents.
Le package éditable du projet a été réinstallé en version 0.3.0, sans réinstaller ses dépendances.
python-dotenv est maintenant déclaré explicitement dans les dépendances du projet.
Les [versions détaillées](evaluation/runtime_versions_v3.json) sont enregistrées sans clé ni chemin personnel.
Aucune dépendance frontend n’a été ajoutée.

Le modèle d’embeddings public `paraphrase-multilingual-MiniLM-L12-v2` a été effectivement téléchargé,
chargé sur CPU et exécuté : 384 dimensions, contexte de 128 tokens, révision
`e8f8c211226b894fcb81acc59f3b34ba3efd5f42`. L’index dense contient 6 documents et 12 chunks.
Ollama et `qwen3:1.7b` étaient déjà disponibles ; aucun modèle Ollama n’a été téléchargé.

## 5. Commandes réellement exécutées

Audit : `git status --short` (absence de dépôt Git), `rg --files`, lecture des modules backend/frontend,
runbooks, tests, configurations CI/Compose/VS Code et scripts PowerShell demandés.

Depuis la racine, les validations principales ont utilisé :

```powershell
.\.venv\Scripts\python.exe -m pip install 'qdrant-client>=1.12,<2.0' 'sentence-transformers>=3.0,<6.0'
.\.venv\Scripts\python.exe -m pip install -e . --no-deps --no-build-isolation
$env:TEMP = Join-Path (Get-Location) '.test-temp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pytest tests/test_rag_v3.py
.\.venv\Scripts\python.exe -m pytest tests/test_investigation_v3.py tests/test_retrieval_agent.py
.\.venv\Scripts\python.exe -m retailmind.cli index
.\.venv\Scripts\python.exe -m retailmind.cli investigate 'Que vérifier après un échec Airflow ?' --langgraph
$env:RETAILMIND_RETRIEVAL = 'qdrant'
.\.venv\Scripts\python.exe -m retailmind.cli evaluate-rag --backend qdrant --output docs/evaluation/qdrant_v3.json
.\.venv\Scripts\python.exe -m retailmind.cli evaluate-rag --backend tfidf --output docs/evaluation/tfidf_v3.json
$env:RETAILMIND_INTEGRATION = '1'
$env:RETAILMIND_RETRIEVAL = 'local'
$env:RETAILMIND_OLLAMA_MODEL = ''
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check src tests scripts/smoke_v3.py --select E4,E7,E9,F
.\.venv\Scripts\python.exe -m compileall -q src tests
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/smoke_v3.py
cd frontend
npm.cmd run build
```

L’appel réel Ollama a exécuté `agent.investigate(..., use_langgraph=True)` avec
`RETAILMIND_RETRIEVAL=qdrant`, `RETAILMIND_OLLAMA_MODEL=qwen3:1.7b` et `OLLAMA_TIMEOUT=35`.
La réponse publique a été enregistrée dans `ollama_smoke_v3.json`.
Une sonde GET sur `/api/tags` a confirmé le modèle disponible.
`docker info --format '{{.ServerVersion}}'` a échoué car le daemon n’était pas accessible.

Les premiers essais en sandbox ont rencontré les restrictions TEMP de Windows, le blocage de
`npm.ps1`, le réseau bloqué pour pip et les lectures de dossiers parents par esbuild. Les tests ont
été relancés avec TEMP/TMP locaux et `npm.cmd`. Les téléchargements et builds ont été autorisés
hors de ces restrictions ; aucune politique Windows globale n’a été modifiée.

## 6. Résultats exécutés

| Vérification | Résultat |
|---|---|
| Référence Python avant modifications | 15 tests réussis |
| Référence React avant modifications | Build TypeScript/Vite réussi |
| Suite finale, intégration réelle activée | **49 tests réussis** |
| Ruff E4/E7/E9/F | Tous les contrôles réussis |
| compileall | Réussi |
| pip check | Aucune dépendance cassée |
| Scripts PowerShell et tâches VS Code | Syntaxe analysée sans erreur |
| React final | Build réussi, 2 001 modules transformés |
| Index réel et réindexation | 6 documents, 12 chunks, 384 dimensions ; réindexation identique sans doublons |
| LangGraph | Neuf nœuds réellement exécutés |
| API HTTP | Routes V2 et nouvelles lectures vérifiées ; `/predict` et `/investigate` fonctionnels |
| Sans Ollama | Mode réel `langgraph+qdrant+deterministic` |
| Avec Ollama | Mode réel `langgraph+qdrant+ollama_extractive`, candidat validé |
| Indisponibilités et attaques contrôlées | Fallbacks, refus, quarantaine et rejet de citations vérifiés |

Sans `RETAILMIND_INTEGRATION=1`, le test du vrai modèle est volontairement ignoré.
Les résultats de retrieval sur 18 questions annotées sont de 83,33 % pour TF-IDF, 94,44 % pour
le dense initial et 100 % pour le système final avec filtre explicite, à @3 et @5.
Le système final a répondu sans erreur aux 19 requêtes, avec une requête sans correspondance,
une moyenne chaude de 51,069 ms et un P95 de 69,708 ms.
Le [protocole complet](evaluation/README.md) explique le dénominateur, le contrôle, la correction dbt
et l’utilisation du même échantillon pour diagnostiquer cette correction.

Le rapport ML existant a été relu, sans réentraînement de démonstration :

| Modèle | Precision | Recall | F1 |
|---|---:|---:|---:|
| Isolation Forest | 0,5396825397 | 0,34 | 0,4171779141 |
| Autoencodeur PyTorch | 0,8764044944 | 0,78 | 0,8253968254 |

L’architecture `MLP_autoencoder_24_8_24` et les 12 epochs du rapport existant restent préservées.
Les entraînements de tests sont isolés dans des répertoires temporaires. Les empreintes finales
des artefacts présents sont fournies dans le manifeste ; il ne s’agit pas d’une comparaison Git.

## 7. Limites et éléments non vérifiés

- Le serveur Qdrant Docker n’a pas été exercé : daemon Docker inaccessible. Le stockage local réel est vérifié.
- L’interface a passé la compilation et les contrats API ; aucune session de navigateur automatisée
  n’était disponible pour contrôler visuellement les thèmes, le responsive et les interactions des pages.
- Le benchmark est petit et guidé par le corpus ; il ne démontre pas une généralisation ni une performance de production.
- Le filtre de composant corrige un échec observé sur le même échantillon ; une validation indépendante reste nécessaire.
- La synthèse Ollama est extractive, les extraits restent dans la langue des runbooks, et aucun diagnostic causal libre n’est accepté.
- Le classement d’intentions et la détection d’injections sont heuristiques ; la sécurité repose surtout
  sur les outils absents, les templates fixes et la vérification de provenance.
- Qdrant local ne doit pas être partagé entre processus. Les anciennes collections consomment de l’espace jusqu’au nettoyage manuel.
- Le budget global est coopératif entre nœuds ; une inférence CPU bloquée n’est pas tuée par un sous-processus.
- L’avertissement Vite de bundle supérieur à 500 Ko persiste ; aucun nouvel échec de build.
- L’application reste locale, sans authentification de production ni conformité réglementaire démontrée.

## 8. Démarrer dans VS Code

Le workspace est configuré pour Qdrant local, avec Ollama désactivé par défaut. Depuis la racine :

```powershell
# Terminal 1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_api_windows.ps1
# Terminal 2
cd frontend
npm.cmd run dev
```

Ouvrir http://localhost:5173 puis Investigation IA. Les instructions d’installation, d’indexation,
d’activation Ollama, d’évaluation et de dépannage sont dans le [guide Windows V3](V3_GUIDE_WINDOWS.md).
