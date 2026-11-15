# RetailMind AI V4.6 — Portfolio Data Engineering

> **Statut de la livraison :** dossier documentaire de démonstration. Les résultats
> ci-dessous sont les mesures des exécutions V4.1–V4.5.2 déjà effectuées ;
> ils ne constituent pas une nouvelle exécution de tests lors de la consultation.

**Objectif.** Montrer, sur des transactions exclusivement **synthétiques**, le
passage de l'ingestion au contrôle qualité puis à l'observabilité : PySpark,
Parquet, dbt, DuckDB, Airflow, Docker, GitHub Actions, FastAPI et React.

## Parcours conseillé

1. [Architecture V4 et limites](V4_6_ARCHITECTURE.md) : composants, flux,
   isolation V3/V4, décisions de conception et périmètre de sécurité.
2. [Démonstration locale reproductible](V4_6_DEMO.md) : vérifications
   PowerShell, Airflow, API, React et dépannage sans supprimer les volumes.
3. [Preuves et matrice de validation](V4_6_PREUVES.md) : engagements mesurables,
   résultats observés, commandes et exécutions GitHub Actions correspondantes.

## Résultats observés, fixture seed 42

| Indicateur | Résultat |
| --- | ---: |
| Transactions brutes, doublons inclus | 5 025 |
| Transactions dédupliquées | 5 000 |
| Doublons éliminés | 25 |
| Anomalies **injectées** | 334 |
| Revenu payé du jeu synthétique | 4 003 524,57 MAD |
| Écarts du rapprochement quotidien / régional | 0 / 0 |
| Tâches du DAG Airflow réussies sur le run observé | 4 / 4 |
| Tests Python locaux V4.5.2 | 83 réussis, 1 ignoré |

Ces nombres caractérisent une fixture déterministe, **pas une performance
anti-fraude ni un volume de transactions clients**. La preuve de l'exécution
sur Linux est l'artefact JSON du workflow Data Engineering GitHub Actions ;
la preuve d'orchestration Airflow vient de l'exécution Docker locale.

## Parcours démo en entretien (3 à 5 minutes)

- Présenter le diagramme [d'architecture](V4_6_ARCHITECTURE.md).
- Ouvrir l'onglet **Pipelines V4** de React : statut du run, quatre durées,
  filtres d'historique, contrôle de données et horodatage de capture.
- Expliquer que le bouton React relit un **instantané** ; l'opérateur exporte
  les nouveaux états depuis Docker, sans accès Docker dans le navigateur.
- Ouvrir les [preuves GitHub](V4_6_PREUVES.md), notamment la CI Linux réelle.
- Montrer le [runbook de démonstration](V4_6_DEMO.md) et les limites d'une
  installation locale (sans authentification de production).

## Évolutions possibles, non réalisées dans cette livraison

Orchestration multi-nœuds, PostgreSQL pour les métadonnées Airflow,
observabilité temps réel, alertes automatisées, gestion de secrets, RBAC,
stockage cloud et déploiement Kubernetes. Les documenter comme **perspectives**,
non comme fonctionnalités déjà livrées.

**Branche de travail :** `feature/v4-data-engineering`. La branche `main` reste
inchangée jusqu'à une éventuelle intégration volontaire.
