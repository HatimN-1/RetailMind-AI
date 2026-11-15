# Runbook V4.6 — Démonstration reproductible sous Windows

> Commandes depuis la racine du dépôt `retailmind-ai` dans PowerShell.
> Prérequis : Python 3.11 avec `.venv`, Java 17, Docker Desktop (Linux
> containers) et Node.js/npm pour l'interface. Les services nécessaires
> doivent être installés avant la démonstration.

## 0. Contrôle initial, sans modification des données

```powershell
git branch --show-current
git status --short
docker compose --profile airflow config --quiet
docker compose --profile airflow ps airflow
```

La branche de travail doit être `feature/v4-data-engineering`. Si Airflow est
arrêté, la commande ci-dessous **démarre/recrée si nécessaire le conteneur**,
mais conserve les volumes nommés :

```powershell
docker compose --profile airflow up -d airflow
docker compose --profile airflow ps airflow
```

Sur un nouveau démarrage, le statut peut être `health: starting`. Vérifier
qu'il devient `healthy` avant les commandes suivantes. Ne pas confondre le
conteneur `airflow-data-init` **Exited** (prévu) avec une panne d'Airflow.

## 1. Valider l'infrastructure et le contrat de données

```powershell
.\.venv\Scripts\python.exe scripts/check_v4_docker.py --check-data --output data/reports/v4_docker_validation.json
```

Ce contrôle ne crée pas de nouveau DAG. Il exige toutefois qu'un DAG ait déjà
produit Parquet et DuckDB. Sur un clone neuf, le contrat de données peut ne pas
être disponible : exécuter une fois le DAG **manuellement** après vérification
que les données générées resteront dans le volume V4 isolé.

Pour déclencher **volontairement** une nouvelle exécution synthétique (optionnel) :

```powershell
docker compose --profile airflow exec airflow airflow dags trigger retailmind_v4_spark_dbt_pipeline
```

Cela **regénère la fixture V4** ; ne pas l'utiliser pour une simple consultation
ou pour réparer un contrôle de santé. Inspecter les tâches dans l'interface
Airflow sur `http://127.0.0.1:8080` avant de vérifier les métriques.

## 2. Exporter l'historique réel sans déclencher le DAG

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\refresh_v4_monitoring_windows.ps1 -Limit 20
```

L'export doit répondre `status: passed` et créer/actualiser
`monitoring/v4_pipeline.json` (fichier local ignoré par Git). Une seule
exécution dans l'historique donne normalement : Tous `1`, Réussis `1`,
Échecs `0`, En cours `0`. Les dates affichées dans React sont localisées à
Casablanca ; les horodatages Airflow bruts sont en UTC.

## 3. Vérifier l'API et lancer l'interface

**Terminal 1**, uniquement si FastAPI n'est pas déjà démarré sur le port 8000 :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_api_windows.ps1
```

**Terminal 2**, uniquement si Vite n'est pas déjà lancé sur le port 5173 :

```powershell
npm.cmd --prefix .\frontend run dev
```

**Terminal 3**, requête lecture seule :

```powershell
(Invoke-RestMethod http://127.0.0.1:8000/v4/monitoring).runs.Count
```

Ouvrir `http://127.0.0.1:5173` → **Pipelines V4**. Montrer les états et
durées des quatre tâches, les filtres, les KPI et l'heure de capture.
Le bouton « Relire l'instantané » relit le fichier ; il **ne lance aucun DAG**.
Un rafraîchissement automatique de l'écran toutes les 60 s ne remplace pas
la commande PowerShell d'export.

## 4. Expliquer la preuve de CI

Dans le dépôt GitHub, ouvrir **Actions** : Python, React et, pour les commits
qui touchent les fichiers de données, **RetailMind V4 data pipeline**.
Le job Data Engineering vérifie un dataset créé sur un runner Linux propre et
publie `retailmind-v4-data-contract` (artefact à durée de conservation limitée).
Ce job ne démarre pas l'interface Airflow : l'orchestration a été validée
localement sous Docker.

## 5. Vérifications de non-régression

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_tests_windows.ps1
.\.venv\Scripts\python.exe -m ruff check src tests scripts/export_v4_monitoring.py --select E4,E7,E9,F
npm.cmd --prefix .\frontend run build
```

Mesure locale de référence constatée au commit `c8116ad` : **83 tests passés,
1 ignoré**. Une exécution future peut faire évoluer ce nombre. L'avertissement
Vite sur la taille du bundle n'est pas un échec du build.

## Dépannage, sans perte de données

| Symptôme | Vérification / action sûre |
| --- | --- |
| Airflow `starting` | `docker compose --profile airflow ps airflow`, puis consulter les logs |
| Airflow `unhealthy` | `docker compose --profile airflow logs --tail 120 airflow` |
| DAG manquant | `docker compose --profile airflow exec airflow airflow dags list-import-errors` |
| API `503` sur `/v4/monitoring` | Relancer l'export PowerShell, vérifier le fichier local |
| Historique ancien dans React | Export PowerShell d'abord, puis « Relire l'instantané » |
| Contrat absent | Ne pas inventer `passed` : confirmer la dernière exécution V4 |

**Interdit en dépannage :** `docker compose down --volumes` (supprime les
volumes persistants) ; exposer `.env`, les identifiants Airflow ou la socket
Docker au navigateur. Arrêt sans suppression :
`docker compose --profile airflow stop airflow`.
