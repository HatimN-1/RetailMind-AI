# Matrice de preuves — RetailMind AI V4 (15 novembre 2026)

Cette matrice distingue **résultat mesuré**, **source vérifiable** et
**limite de la preuve**. Les sorties locales sont celles recueillies pendant
le développement sur Windows ; elles ne sont pas stockées automatiquement
dans Git. Les liens Actions renvoient à des exécutions précises, parfois
associées à un commit antérieur au plus récent.

| Affirmation | Preuve observée | Où la reproduire ou la consulter |
| --- | --- | --- |
| Tests Python V4.5.2 | 83 passés, 1 ignoré sous Windows | `scripts/run_tests_windows.ps1` ; [CI Python du commit c8116ad](https://github.com/HatimN-1/RetailMind-AI/actions/runs/43705785772) |
| Interface React | Build Vite/TypeScript réussi | `npm.cmd --prefix .\frontend run build` ; [CI React c8116ad](https://github.com/HatimN-1/RetailMind-AI/actions/runs/43705785623) |
| PySpark, dbt, DuckDB sur Linux | CI Data Engineering réussie et rapport JSON disponible | [Workflow V4 data, commit ba75e94](https://github.com/HatimN-1/RetailMind-AI/actions/runs/43704278130) |
| DAG Airflow sous Docker local | Run manuel terminé en `success`, 4 tâches en `success` | `airflow dags list-runs` et `airflow tasks states-for-dag-run` dans Docker ; `docs/V4_3_AIRFLOW.md` |
| Docker local | Conteneur `healthy`, DAG sans erreurs d'import, versions et droits OK | `python scripts/check_v4_docker.py --check-data` ; `docs/V4_4_DOCKER.md` |
| Monitoring React | Run réel, durées des tâches, capture et données affichées | `GET /v4/monitoring` ; `docs/V4_5_MONITORING.md` |
| Données reconciliées | 5 000 transactions, 334 anomalies injectées, 4 003 524,57 MAD et 0 / 0 écart | `scripts/verify_dbt.py`, rapport CI `retailmind-v4-data-contract` |

## Exécution Airflow effectivement observée

- DAG : `retailmind_v4_spark_dbt_pipeline`
- Run ID : `manual__2026-11-14T21:49:59+00:00`
- Début effectif : `2026-11-14T23:22:09.713407+00:00`
- Fin : `2026-11-14T23:23:15.347988+00:00`
- Durée totale : environ **65,63 secondes** (temps d'attente entre tâches compris)
- `generate_synthetic_transactions` : success (~0,51 s)
- `spark_etl_to_parquet` : success (~34,89 s)
- `dbt_build_marts_and_tests` : success (~11,99 s)
- `verify_dbt_vs_spark` : success (~1,42 s)

Les données métriques ont été validées pour l'état de l'entrepôt au moment du
contrôle ; le sélecteur historique React ne prétend pas calculer des métriques
spécifiques à chaque ancien run.

## Contrat reproductible de la fixture

```json
{
  "status": "passed",
  "transactions": 5000,
  "injected_anomalies": 334,
  "paid_revenue_mad": 4003524.57,
  "daily_mismatches": 0,
  "region_mismatches": 0
}
```

Valeurs de référence, pas données commerciales : le générateur utilise
`--rows 5000 --seed 42`, ajoute 25 doublons puis PySpark déduplique.
Ce rapport ne valide pas un vrai système anti-fraude ni une charge production.

## Ce qu'il ne faut pas confondre

- Une **CI GitHub réussie** valide les étapes Spark/dbt/DuckDB et les tests,
  **pas** l'exécution du scheduler et du webserver Airflow dans cette CI.
- Un **DAG réussi dans Docker local** ne démontre pas un déploiement cloud ou
  une architecture multi-worker.
- L'onglet **Pipelines V4** montre un **instantané** : sa date de capture
  peut être ancienne, même si React vient de relire le fichier.
- Les métriques de la fixture sont déterministes ; les scores ML évaluent
  seulement des labels artificiels.

## Collecte de preuves pour un entretien

1. Conserver une capture des cartes KPI, des quatre tâches et de l'horodatage
   de l'onglet **Pipelines V4**, sans données sensibles.
2. Conserver une capture de **Actions** avec les bons commits / noms de jobs.
3. Télécharger l'artefact `retailmind-v4-data-contract` tant qu'il est
   disponible sur la page du workflow V4 data.
4. Conserver localement le rapport du smoke test Docker et l'export monitoring.
   Ils sont **ignorés par Git** et ne doivent pas être publiés avec des secrets.
5. Ne jamais inventer de captures ou d'exécutions supplémentaires.

**Lien de navigation :** [dossier portfolio](V4_6_PORTFOLIO.md) ·
[architecture](V4_6_ARCHITECTURE.md) ·
[démonstration](V4_6_DEMO.md).
