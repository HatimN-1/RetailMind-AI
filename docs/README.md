# Documentation — RetailMind AI

## V4 — Data Engineering, orchestration et observabilité

Commencer par le **[dossier portfolio V4.6](V4_6_PORTFOLIO.md)** :
architecture, runbook de démonstration Windows et preuves GitHub Actions.

- [Architecture V4](V4_6_ARCHITECTURE.md) : diagramme et frontières V3/V4
- [Démo V4](V4_6_DEMO.md) : commandes PowerShell reproductibles
- [Preuves V4](V4_6_PREUVES.md) : résultats mesurés et limites
- [Airflow V4.3](V4_3_AIRFLOW.md)
- [CI Data Engineering V4.4.1](V4_4_CI.md)
- [Docker readiness V4.4.2](V4_4_DOCKER.md)
- [Monitoring React V4.5](V4_5_MONITORING.md)

Les données du projet sont **synthétiques**. Le workflow CI vérifie
PySpark/dbt/DuckDB sur Linux ; Airflow est orchestré localement dans Docker.
Le monitoring React est un **instantané opérateur**, pas une supervision live.

## Versions précédentes

La V3 (FastAPI/SQLite, investigation IA, RAG, ML et React) reste distincte et
accessible dans les guides V3 du dépôt. La V4 conserve les fonctionnalités
existantes et isole sa chaîne Data Engineering dans un volume Docker dédié.
