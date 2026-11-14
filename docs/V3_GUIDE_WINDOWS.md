# Démarrer et vérifier la V3 sous Windows 11

Le [correctif Investigation V3](INVESTIGATION_V3_CORRECTIF.md) décrit la page blanche liée au nettoyage
d’un effet React, sa correction et le parcours réellement vérifié avec Chrome, Vite et FastAPI.

Les commandes ci-dessous partent de `retailmind-ai` dans un terminal PowerShell de VS Code.
Le jeu synthétique et les modèles existants sont conservés. Ne pas relancer `bootstrap` ou le setup V2
pour activer le RAG : ces commandes réentraînent ou reconstruisent les artefacts.

## 1. Dépendances et configuration

```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[dev,rag,agent]'
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Le workspace livré dispose déjà des dépendances RAG, du cache du modèle et d’un index local réel.
Un `.env` local sans secret a été créé avec `RETAILMIND_RETRIEVAL=qdrant` ; Ollama reste désactivé
par défaut. Les variables du processus priment sur `.env`. Le fichier n’est pas envoyé à React.
`RETAILMIND_HOME` se définit dans le processus avant lancement si un environnement isolé est souhaité.

Installation équivalente via tâche VS Code « RetailMind V3: Install RAG » ou :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_rag_windows.ps1
```

## 2. Index Qdrant local sans Docker

Arrêter l’API et les autres processus accédant à l’index local avant ces commandes.
Le premier téléchargement du modèle nécessite Internet ; aucune clé commerciale n’est requise.
Le cache est dans `data/embedding_cache`, l’index dans `data/qdrant_local`.

```powershell
Remove-Item Env:QDRANT_URL -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m retailmind.cli index
.\.venv\Scripts\python.exe -m retailmind.cli index
.\.venv\Scripts\python.exe -m retailmind.cli rag-status
.\.venv\Scripts\python.exe -m retailmind.cli investigate 'Que vérifier après un échec Airflow ?' --langgraph
```

La deuxième indexation doit annoncer `unchanged`, avec 6 documents, 12 chunks et 384 dimensions
pour le corpus et la configuration livrés. Toute modification de modèle, de révision, de chunking ou
de contenu exige une réindexation. Les anciens index restent disponibles pour retour arrière manuel.
Ne jamais supprimer globalement `data/` pour résoudre une erreur de RAG.

## 3. FastAPI et React

Terminal 1, depuis la racine :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_api_windows.ps1
# Alternative :
# .\.venv\Scripts\python.exe -m uvicorn retailmind.api:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2 :

```powershell
cd frontend
npm.cmd run dev
```

Application : http://localhost:5173 ; Swagger : http://127.0.0.1:8000/docs.
Les tâches VS Code « API Windows » et « React Frontend » sont conservées.
Sur Investigation IA, LangGraph est coché par défaut. Vérifier le panneau des services puis le mode
de chaque message. Le mode attendu sans Ollama est `langgraph+qdrant+deterministic`.
Les sources sont dépliables et le document complet est consultable via un endpoint GET autorisé.

Exemples : anomalies synthétiques, `TX-0003699`, revenus régionaux, échec Airflow, schéma Spark,
test dbt échoué, contrôles qualité. `TX-00003699` comporte huit chiffres et ne doit pas être
silencieusement converti en identifiant existant. Les runbooks sont en anglais, y compris les extraits cités.

## 4. Qdrant via Docker, Python et React sur Windows

Ce parcours utilise le service Qdrant déjà présent dans Compose. Le daemon Docker doit être démarré.
Les dépendances `rag` restent nécessaires dans le `.venv` utilisé par l’API et la CLI.

```powershell
docker compose --profile rag up -d qdrant
$env:QDRANT_URL = 'http://127.0.0.1:6333'
$env:RETAILMIND_RETRIEVAL = 'qdrant'
.\.venv\Scripts\python.exe -m retailmind.cli index
.\.venv\Scripts\python.exe -m retailmind.cli rag-status
.\.venv\Scripts\python.exe -m uvicorn retailmind.api:app --host 127.0.0.1 --port 8000
```

Pour les lancements futurs, ajouter `QDRANT_URL=http://127.0.0.1:6333` à `.env`.
L’index distant est distinct de l’index local : indexer le serveur avant de basculer l’API.
Le mode serveur peut servir plusieurs processus ; le mode local doit rester mono-processus.
Le Compose complet V2 n’installe pas automatiquement les extras Python RAG dans son image API de base.
Les commandes ci-dessus exécutent donc FastAPI sur l’hôte et Qdrant dans Docker.
Le parcours Docker n’a pas été exécuté pendant cette livraison : daemon inaccessible.

## 5. Ollama facultatif

La livraison a testé le service local déjà disponible et le modèle `qwen3:1.7b`, sans télécharger de modèle Ollama.
Sur une autre machine, installer Ollama puis choisir un modèle local compatible JSON structuré.
Le téléchargement éventuel est une opération explicite de l’utilisateur :

```powershell
ollama list
# Uniquement si le modèle est absent et son téléchargement souhaité :
# ollama pull qwen3:1.7b
$env:RETAILMIND_OLLAMA_MODEL = 'qwen3:1.7b'
$env:OLLAMA_TIMEOUT = '35'
.\.venv\Scripts\python.exe -m retailmind.cli investigate 'Que vérifier après un échec Airflow ?' --langgraph
```

Reporter les variables dans `.env` puis redémarrer FastAPI pour activer Ollama dans l’interface.
Une sélection acceptée donne `ollama_extractive`. Un timeout, un candidat non étayé ou un modèle
absent donne une réponse déterministe avec avertissement. Le modèle sélectionne des extraits par
identifiant ; le serveur recopie le texte original. Ce mode ne produit pas de cause racine libre.
Le timeout par défaut est de 20 secondes ; la mesure réelle de livraison a utilisé 35 secondes.

Pour désactiver Ollama dans le terminal courant :

```powershell
$env:RETAILMIND_OLLAMA_MODEL = ''
```

Pour forcer TF-IDF, y compris lorsque Qdrant est installé :

```powershell
$env:RETAILMIND_RETRIEVAL = 'local'
```

## 6. Tests et mesures

Arrêter l’API avant les tests d’intégration et les évaluations qui ouvrent le même index local.
Les tests ordinaires n’effectuent aucun téléchargement de modèle ; Qdrant utilise des embeddings stub
pour ses tests unitaires. LangGraph et Qdrant manquants provoquent des skips des tests optionnels.

```powershell
$env:TEMP = Join-Path (Get-Location) '.test-temp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
$env:RETAILMIND_RETRIEVAL = 'local'
$env:RETAILMIND_OLLAMA_MODEL = ''
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pytest tests/test_rag_v3.py tests/test_investigation_v3.py tests/test_rag_evaluation.py
$env:RETAILMIND_INTEGRATION = '1'
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check src tests scripts/smoke_v3.py --select E4,E7,E9,F
.\.venv\Scripts\python.exe -m compileall -q src tests
.\.venv\Scripts\python.exe -m pip check
$env:RETAILMIND_RETRIEVAL = 'qdrant'
.\.venv\Scripts\python.exe -m retailmind.cli evaluate-rag --backend qdrant --output data/reports/rag_qdrant.json
.\.venv\Scripts\python.exe -m retailmind.cli evaluate-rag --backend tfidf --output data/reports/rag_tfidf.json
.\.venv\Scripts\python.exe scripts/smoke_v3.py
cd frontend
npm.cmd run build
```

Le smoke test démarre un serveur temporaire sur un port disponible, vérifie les routes HTTP,
puis arrête uniquement le processus qu’il a créé. Il force Ollama désactivé et n’entraîne aucun modèle.
La suite Pytest conserve ses jeux générés et entraînements unitaires dans des répertoires temporaires,
sans écraser les artefacts de démonstration. La CI installe LangGraph et le client Qdrant ; le vrai
modèle reste réservé au test d’intégration explicite.

## Dépannage

| Symptôme | Action |
|---|---|
| `npm.ps1` bloqué | Utiliser `npm.cmd` ; aucune modification globale d’ExecutionPolicy nécessaire |
| Accès refusé au temp Pytest | Utiliser le dossier `.test-temp` et les variables TEMP/TMP ci-dessus |
| Verrou Qdrant local | Arrêter API/CLI concurrentes ; un seul processus par répertoire local |
| Index `stale` | Réindexer avec le même modèle, la même révision et le corpus actuel |
| Qdrant indisponible | Lire l’avertissement TF-IDF, vérifier URL/daemon ou utiliser le mode local sans Docker |
| Modèle non présent en cache | Exécuter `index` avec Internet ; les requêtes HTTP ne téléchargent pas le modèle |
| Avertissement de symlinks Hugging Face Windows | Cache fonctionnel avec davantage d’espace ; mode développeur facultatif |
| Ollama `disabled` | Définir RETAILMIND_OLLAMA_MODEL puis redémarrer l’API |
| Ollama disponible mais non utilisé | Lire `ollama_attempted`, `ollama_used` et les avertissements de la réponse |
| Extrait Ollama rejeté | Repli déterministe attendu ; aucun texte non vérifiable n’est affiché comme constat |
| Transaction introuvable | Vérifier l’identifiant exact ; aucun ajout/retrait de zéro automatique |
| Build Vite, accès refusé aux dossiers parents | Restriction du sandbox ; exécuter le build dans un terminal Windows autorisé |
| Bundle supérieur à 500 Ko | Avertissement Vite déjà présent ; le build fonctionne, découpage futur possible |

Les anciens scripts FastAPI, React, bootstrap et setup restent disponibles. Cette V3 ne relance
jamais un pipeline ou une opération d’administration à partir d’une question utilisateur.
