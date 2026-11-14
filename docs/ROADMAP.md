# Roadmap des extensions

1. MVP local : génération, ETL qualité, SQL, IsolationForest, API, Streamlit, agent, tests.
2. Ajouter PyTorch et mesurer le modèle sur le même holdout, sans toucher aux labels pour l'entraînement.
3. Exécuter Spark et comparer les comptes avec le pipeline pandas.
4. Exécuter dbt run/test, vérifier marts DuckDB et seuils de qualité.
5. Tester LangGraph et l'indexation Qdrant, constituer un jeu de 20 questions avec sources attendues.
6. Déclencher manuellement le DAG Airflow et capturer logs/temps d'exécution.
7. Valider Docker Compose puis Minikube avec preuve de démarrage et health probes.
8. Éventuellement ajouter Kafka et un micro-batch Spark Structured Streaming, avec justification métier.
9. Option Azure DevOps/Fabric : uniquement après disposer d'un compte autorisé.

Ne pas ajouter ces technologies au CV tant que leur exécution n'est pas prouvée.
