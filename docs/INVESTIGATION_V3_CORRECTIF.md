# Correctif Investigation IA V3 — 14 novembre 2026

## Cause reproduite dans un vrai navigateur

Dans Chrome 157, `Element.scrollIntoView(...)` a réellement renvoyé une Promise.
L’effet React utilisait un retour implicite :

```tsx
useEffect(() => bottom.current?.scrollIntoView({behavior: 'smooth', block: 'nearest'}), [messages, loading]);
```

React interprète la valeur retournée par un effet comme sa fonction de nettoyage. Avec `StrictMode`,
le nettoyage intervient aussi pendant le montage de développement. La Promise a donc été appelée
comme une fonction : avertissement `useEffect must not return anything besides a function`,
exception **`destroy is not a function`**, puis page vide. Une compilation TypeScript et un test
FastAPI ne pouvaient pas établir le bon fonctionnement de ce parcours navigateur.

Le correctif utilise un bloc sans retour :

```tsx
useEffect(() => {
  bottom.current?.scrollIntoView({behavior: 'smooth', block: 'nearest'});
}, [messages, loading]);
```

Avant correction, les appels HTTP directs et via Vite répondaient déjà 200 pour les questions valides.
Il n’a pas été constaté d’incompatibilité LangGraph ou Pydantic dans les requêtes normales.
Les embeddings étaient présents et la recherche Qdrant locale retournait des chunks Airflow réels.
La cause principale de la page vide était donc le cycle de vie React, sans modification des modèles ML.

## Contrat et corrections complémentaires

React envoie toujours `{question: string, use_langgraph: boolean}` à `/api/investigate`.
Vite retire `/api` et transmet à `http://127.0.0.1:8000/investigate` par défaut.
Le résultat conserve `answer`, `mode`, `evidence`, `sources` et les champs V3 existants.

Les corrections complémentaires portent sur le diagnostic et la récupération après une erreur :

- Le client distingue une panne réseau, un délai dépassé, une réponse non JSON et un contrat incompatible.
- Les détails Pydantic 422 sont présentés par champ, sans afficher tout le JSON technique ni ses valeurs d’entrée.
- Une erreur d’investigation est un message `role=alert` avec possibilité de réessayer la question.
- Une garde empêche les doubles envois avant la mise à jour de l’état React.
- Les erreurs serveur conservent `detail` et ajoutent `code`, `error_type`, `correlation_id` et l’en-tête
  `X-Correlation-ID`. Les statuts d’erreur existants sont préservés : 400/422/503/504 ; une erreur
  inattendue retourne un JSON 500 exploitable par l’interface.
- Les journaux serveur conservent les types réels d’exception, leurs chaînes et les fichiers/lignes/fonctions
  de la pile. Les valeurs d’exception, les questions, les paramètres d’environnement et les locaux ne sont
  pas journalisés, car ils peuvent contenir des informations sensibles.
- Un verrou Qdrant réel a été reproduit : `portalocker.exceptions.AlreadyLocked`, enveloppé dans
  `RuntimeError: ... already accessed by another instance ...`. Le fallback TF-IDF existant fonctionnait,
  mais son avertissement ne précisait pas la raison. Il fournit maintenant `qdrant_locked`, le type réel,
  une instruction de fermeture des autres instances et la même corrélation que l’investigation.
- Le statut RAG expose aussi un diagnostic lisible. Aucun changement de cycle de vie des clients Qdrant,
  de modèle d’embeddings ou de mécanisme d’indexation n’a été nécessaire.

`RETAILMIND_API_PROXY_TARGET` permet au runner de test de lancer une API sur un port isolé.
Cette variable est lue uniquement par la configuration Vite ; sa valeur par défaut reste le port 8000.
Le runner force le frontend à utiliser `/api`, ce qui teste réellement le proxy utilisé par l’application.

## Fichiers modifiés ou créés pour ce correctif

Modifiés :

- `frontend/src/pages/Investigation.tsx` : effet corrigé, erreurs accessibles, réessai et garde d’envoi.
- `frontend/src/api.ts` : erreurs distinctes, timeout nettoyé et vérification du contrat de réponse.
- `frontend/src/types.ts` : diagnostics RAG optionnels.
- `frontend/vite.config.ts` : cible de proxy configurable pour les tests isolés.
- `src/retailmind/api.py` : erreurs JSON corrélées et traces serveur.
- `src/retailmind/agent.py` : propagation de la corrélation et des diagnostics, workflow inchangé.
- `src/retailmind/retrieval.py` : raisons de fallback explicites et traces sans données sensibles.
- `pyproject.toml` : extra de tests navigateur `e2e`.
- `docs/V3_GUIDE_WINDOWS.md` et `README.md` : lien vers ce diagnostic.

Créés :

- `src/retailmind/diagnostics.py` : journalisation des types et emplacements de pile.
- `tests/test_investigate_integration.py` : onze cas d’intégration FastAPI.
- `scripts/verify_investigation.py` : serveurs temporaires, vrais appels HTTP et tests Chrome/Edge.
- `docs/evaluation/investigation_hotfix_e2e.json` : résultats HTTP et navigateur exécutés.
- `docs/evaluation/investigation_hotfix_dark.png`, `investigation_hotfix_light.png`,
  `investigation_hotfix_mobile.png` : captures issues du parcours vérifié.
- Ce rapport.

Les journaux et fichiers intermédiaires sont dans `.test-temp/urgent-investigation/`, ignoré par Git.
Les modèles, leurs rapports de référence, les transactions, les runbooks et les mesures RAG précédentes
n’ont pas été modifiés. Les empreintes SQLite et ML ont été comparées avant/après les vérifications.

## Tests et résultats réellement exécutés

Installation de test : Playwright **1.65.2**, greenlet **3.5.6** dans `.venv`. Chrome déjà installé a été
utilisé ; aucun navigateur et aucune dépendance frontend supplémentaires n’ont été téléchargés.

Commandes principales, depuis la racine :

```powershell
.\.venv\Scripts\python.exe -m pip install playwright
$env:TEMP = Join-Path (Get-Location) '.test-temp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
$env:RETAILMIND_RETRIEVAL = 'local'
$env:RETAILMIND_OLLAMA_MODEL = ''
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pytest tests/test_investigate_integration.py
.\.venv\Scripts\python.exe scripts/verify_investigation.py --browser --output .test-temp/urgent-investigation/release-verified
$env:RETAILMIND_INTEGRATION = '1'
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check src tests scripts/verify_investigation.py --select E4,E7,E9,F
.\.venv\Scripts\python.exe -m compileall -q src tests scripts/verify_investigation.py
.\.venv\Scripts\python.exe -m pip check
cd frontend
npm.cmd run build
```

Résultats : **59 tests réussis et 1 test optionnel ignoré** sans activation du vrai modèle ;
**60 tests réussis** avec `RETAILMIND_INTEGRATION=1` ; onze cas dans le nouveau fichier d’intégration.
Ruff, compileall et pip check réussis. Build TypeScript/Vite réussi, 2 001 modules transformés.
L’avertissement de bundle supérieur à 500 Ko reste présent.

Le runner lance ses propres serveurs FastAPI et Vite sur des ports disponibles, puis arrête uniquement
les processus qu’il a créés. Les serveurs de l’utilisateur ne sont jamais arrêtés. Il exige un index
Qdrant local existant et les vrais embeddings déjà en cache ; il n’indexe ni n’entraîne aucun modèle.

| Vérification HTTP directe et via le proxy Vite | Résultat |
|---|---|
| `GET /health` | 200, warehouse prêt |
| Transaction `TX-0003699`, sans LangGraph | 200, `sequential+qdrant+deterministic`, preuve SQL conservée |
| Même transaction, avec LangGraph | 200, `langgraph+qdrant+deterministic`, neuf étapes |
| Investigation documentaire Airflow | 200, chunks de `04_airflow_retry.md` avec scores |
| Question vide | 422 Pydantic attendu |
| Verrou Qdrant réel, pendant le test navigateur | 200, `langgraph+tfidf+deterministic`, avertissement explicite |
| Ollama désactivé | Aucun appel Ollama, réponse déterministe utile |

Le test navigateur vérifie l’envoi réel et le rendu de la transaction, le changement de parcours,
les quatre sections de réponse, les sources/scores, le document complet, le verrou Qdrant, une vraie
validation Pydantic, le réessai, le démontage/remontage et les thèmes. Le scénario mobile attend la fin
des transitions CSS et vérifie l’absence de débordement horizontal ainsi qu’un champ utilisable.

Un scénario force aussi `scrollIntoView` à retourner une Promise pour reproduire le défaut sur tout
navigateur compatible avec Playwright. **Aucune exception JavaScript de page** n’est constatée après correction.

Les erreurs HTTP 503/504 et la réponse au contrat incompatible sont des réponses contrôlées par
Playwright, explicitement marquées dans le rapport. Elles vérifient les messages de l’interface et ne
constituent pas des pannes réelles du serveur. Les erreurs console HTTP attendues sont conservées,
ainsi qu’un 404 de ressource accessoire ; elles ne sont pas présentées comme des exceptions JavaScript.

Preuves : [rapport brut](evaluation/investigation_hotfix_e2e.json),
[thème sombre](evaluation/investigation_hotfix_dark.png),
[thème clair](evaluation/investigation_hotfix_light.png),
[mobile](evaluation/investigation_hotfix_mobile.png).

## Redémarrer dans VS Code sous Windows

Arrêter les anciens terminaux FastAPI/Vite avec Ctrl+C, puis lancer :

```powershell
# Terminal 1, depuis retailmind-ai
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_api_windows.ps1
```

```powershell
# Terminal 2, depuis retailmind-ai
cd frontend
npm.cmd run dev
```

Ouvrir http://localhost:5173, effectuer un rechargement complet du navigateur si une ancienne erreur
de rendu persiste, puis ouvrir Investigation IA et envoyer `Analyse la transaction TX-0003699`.
Le mode affiché doit correspondre aux composants effectivement utilisés.

Pour reproduire le test navigateur sur une autre machine, installer l’extra `.venv` :

```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[dev,rag,agent,e2e]'
.\.venv\Scripts\python.exe scripts/verify_investigation.py --browser
# Si seul Edge est installé :
.\.venv\Scripts\python.exe scripts/verify_investigation.py --browser --channel msedge
```

Le test a été exécuté avec Chrome sur Windows ; Edge, Firefox, Safari et Qdrant Docker n’ont pas été
validés dans ce correctif. Ne pas supprimer `.lock`, les modèles ou `data/` pour résoudre un verrou.
Fermer l’instance propriétaire, ou utiliser le mode serveur Qdrant pour des accès multi-processus.
