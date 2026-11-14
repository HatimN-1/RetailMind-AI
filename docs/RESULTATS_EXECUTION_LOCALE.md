# Résultats d'exécution locale — référence de livraison

**Attention :** expérience 100 % synthétique, exécutée le 14 novembre 2026 dans un environnement Linux Python.
Les métriques ne prouvent pas un système anti-fraude réel ni un déploiement de production.

## Génération et pipeline
- 5 000 transactions uniques synthétiques (graine 42).
- 5025 lignes sources dont 25 doublons injectés.
- 5000 transactions après contrôles de qualité.
- 334 anomalies injectées comme labels artificiels.
- Valeur brute des commandes (incluant échecs de paiement) : 4,693,961.02 MAD.
- Revenus simulés de commandes payées uniquement : 4,003,524.57 MAD.

## Modèles (holdout temporel de 1250 transactions)

| Modèle | Precision | Recall | F1 | AP (PR-AUC) | ROC-AUC |
|---|---:|---:|---:|---:|---:|
| IsolationForest | 0.540 | 0.340 | 0.417 | 0.597 | 0.946 |
| PyTorch autoencodeur (5 époques) | 0.747 | 0.620 | 0.678 | 0.812 | 0.965 |

**Protocole :** 75 % train / 25 % test par ordre chronologique ; label exclu des variables d'entrée. Un seuil est calculé sur le train, sans ajustement sur les labels du test. Données artificielles plus faciles que des cas réels.

## Contrôles de livraison
- Installation editable (`pip install --no-deps --no-build-isolation -e .`) : PASS.
- `python -m retailmind.bootstrap --rows 5000` : PASS.
- `python -m retailmind.train --torch --epochs 5` : PASS.
- `python -m pytest -q tests` : **11 tests PASS** dans l'environnement de construction.
- Invocation CLI d'investigation par ID de transaction : PASS.
- Compilation Python : PASS.
- Syntaxe YAML vérifiée pour Compose, dbt, CI, Azure Pipelines et Kubernetes : PASS.

## Non validé ici
Docker/Compose, Airflow, PySpark, dbt exécutable, Streamlit affiché, LangGraph,
Qdrant dense RAG, Ollama, Kubernetes, Terraform et Azure DevOps réel. Les scripts et
configurations correspondants sont inclus mais leur exécution nécessite les dépendances,
services et permissions locales.
