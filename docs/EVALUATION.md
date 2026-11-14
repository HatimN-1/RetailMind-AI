# Protocole d'évaluation et traçabilité

## Protocole
- Les événements sont entièrement synthétiques, datés à partir du 1 janvier 2026.
- Seed fixe (42 par défaut), label injecté et documenté.
- Split temporel 75 % / 25 % après nettoyage et tri.
- IsolationForest : 140 arbres, seuil de détection = quantile 95 % du train uniquement.
- Autoencodeur PyTorch optionnel : MLP 24-8-24, perte reconstruction MSE, seuil du train.
- Résultats : precision/recall/F1, PR-AUC, ROC-AUC, nombre prédit, dans model_evaluation.json.
- Les labels `is_anomaly` et `anomaly_type` sont exclus de l'apprentissage; seulement pour évaluation.

## Modules fournis
| Module | Statut du code | Validation requise sur PC utilisateur |
|---|---|---|
| Générateur / pandas ETL / SQLite | implémenté | pytest, bootstrap |
| Scikit-learn Isolation Forest | implémenté | bootstrap, JSON de résultats |
| FastAPI / agent local / tests | implémenté | pytest, requêtes |
| Streamlit | implémenté | exécuter interface |
| PyTorch autoencodeur | implémenté optionnel | installer extra deep, lancer --torch |
| PySpark Parquet | implémenté optionnel | installer Java + PySpark, lancer job |
| dbt DuckDB | modèles et tests fournis | dbt debug/run/test |
| Airflow DAG | fichier et image Docker optionnelle | test Docker et logs DAG |
| LangGraph | graphe exécutable optionnel | installer extra agent |
| Qdrant dense RAG | index + requête optionnels | télécharger embedding, indexer |
| Ollama Qwen3 | synthèse conditionnelle | modèle local et revue humaine |
| Kubernetes / Terraform | exemples de déploiement | appliquer uniquement en environnement autorisé |

## Qualité
Aucun chiffre de performance n'est une mesure de fraude réelle. Ne pas confondre labels injectés,
précision d'un modèle sur synthétique, disponibilité API, satisfaction utilisateur et conformité sécurité.
