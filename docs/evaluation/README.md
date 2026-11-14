# Évaluation RAG V3 — mesures exécutées le 14 novembre 2026

## Protocole

Le fixture versionné `tests/fixtures/rag_questions.json` contient 18 questions annotées : trois par
runbook existant, en français et en anglais, plus une question hors périmètre. Aucun runbook n’a été
créé, réécrit ou traduit pour augmenter les scores. Chaque question annotée attend un document précis.

Pour chaque question, la recherche renvoie au plus cinq chunks. Recall@k est la fraction des sources
attendues présentes dans les k premiers chunks ; la moyenne porte sur les 18 questions annotées.
Le contrôle hors périmètre est exclu du dénominateur de recall et reste visible dans les résultats.
Les répétitions de chunks d’un même document ne sont pas dédupliquées avant le calcul.

Une requête réussie signifie que le moteur a répondu sans exception, même avec zéro résultat.
Les recherches sans correspondance et les erreurs sont comptées séparément. Une panne Qdrant ne
substitue jamais TF-IDF dans cette évaluation. La CLI écrit le rapport puis retourne un code non nul
si des recherches ont échoué. En investigation interactive, le fallback TF-IDF reste disponible et explicite.

Une requête de préchauffage est chronométrée séparément. La moyenne et le P95, calculé avec
`numpy.percentile`, concernent les 19 requêtes suivantes, contrôle inclus. Il s’agit d’un passage local,
sans charge concurrente ni intervalle de confiance. Ces latences ne sont pas celles d’une requête
complète avec LangGraph et Ollama.

## Résultats conservés

| Moteur et stratégie | Recall@3 | Recall@5 | Sans correspondance | Sans erreur | Moyenne chaude | P95 chaud |
|---|---:|---:|---:|---:|---:|---:|
| TF-IDF, fenêtres de mots | 83,33 % | 83,33 % | 4/19 | 19/19 | 10,599 ms | 12,192 ms |
| Qdrant dense initial, sans filtre de composant | 94,44 % | 94,44 % | 1/19 | 19/19 | 65,795 ms | 77,996 ms |
| Qdrant V3, filtre explicite puis similarité cosinus | 100 % | 100 % | 1/19 | 19/19 | 51,069 ms | 69,708 ms |

L’échec initial concernait la question française sur un test dbt échoué, rapprochée des paiements
échoués. La correction limite la recherche aux documents mentionnant le composant explicitement
nommé, puis laisse Qdrant classer leurs chunks par vecteurs réels. Le dernier résultat évalue donc
le système de retrieval avec filtre, et ne doit pas être présenté comme la performance du modèle seul.
Le même échantillon a guidé cette correction : un jeu de validation indépendant reste à constituer.

Artefacts bruts :

- [TF-IDF](tfidf_v3.json)
- [Qdrant dense initial](qdrant_dense_baseline_v3.json)
- [Qdrant V3 final](qdrant_v3.json)
- [Appel réel LangGraph + Qdrant + Ollama](ollama_smoke_v3.json)
- [Démarrage et routes HTTP, Ollama désactivé](api_smoke_v3.json)
- [Versions de l’environnement testé](runtime_versions_v3.json)
- [Empreintes des artefacts ML/SQLite existants au contrôle final](ml_reference_manifest_v3.json)

Les rapports contiennent les questions, sources attendues et retrouvées, scores, références de chunks,
latences, erreurs, révision du modèle, empreinte du corpus et empreinte du fixture.

## Vérifications de gouvernance

Les rapports d’évaluation enregistrent quatre refus sur quatre demandes non autorisées, la conservation
exacte de deux identifiants et les références des observations SQL dans un scénario contrôlé.
`TX-0003699` retrouve une ligne ; `TX-00003699` conserve ses huit chiffres et ne retrouve aucune ligne.
Les tests automatisés complètent ces sondes : aucun outil lors d’un refus, quarantaine documentaire,
citation modifiée rejetée, réponse Ollama invalide rejetée, timeout et absence de service avec fallback,
LangGraph absent avec fallback, validation API stricte et absence d’endpoint d’indexation public.

L’assertion de provenance signifie que les observations contrôlées sont construites directement à partir
des lignes SQL et que les recommandations acceptées sont des extraits référencés. Elle ne démontre
pas une immunité générale aux hallucinations ou aux injections. Aucune cause racine n’est affirmée
sans journal d’incident connecté. Les anomalies sont exclusivement synthétiques.

## Reproduction PowerShell

Arrêter FastAPI avant d’ouvrir le même répertoire Qdrant local depuis une autre CLI.

```powershell
$env:RETAILMIND_RETRIEVAL = 'qdrant'
$env:RETAILMIND_OLLAMA_MODEL = ''
.\.venv\Scripts\python.exe -m retailmind.cli evaluate-rag --backend qdrant --output data/reports/rag_qdrant.json
.\.venv\Scripts\python.exe -m retailmind.cli evaluate-rag --backend tfidf --output data/reports/rag_tfidf.json
$env:RETAILMIND_INTEGRATION = '1'
$env:TEMP = Join-Path (Get-Location) '.test-temp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
.\.venv\Scripts\python.exe -m pytest tests/test_rag_v3.py
```

Le modèle public doit avoir été mis en cache par `index`. Les tests unitaires de stockage utilisent
un embedding stub déterministe et le vrai client Qdrant local ; le test marqué `integration` utilise
le vrai modèle. Le benchmark dense initial est une mesure historique conservée ; le code final applique
le filtre de composant documenté. Les chiffres varient selon la machine et l’état du cache.
