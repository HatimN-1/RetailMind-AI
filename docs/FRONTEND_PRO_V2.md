# Frontend professionnel RetailMind AI V2

## Stack et choix
- React + TypeScript : composants réutilisables et interfaces réactives.
- Vite : développement local rapide et proxy vers FastAPI.
- Recharts : courbes, histogrammes, donut responsive et tooltips.
- Lucide React : icônes homogènes.
- CSS design system : thème clair/sombre, grilles fluides, navigation mobile, cartes, drawers et états de chargement/erreur.
- Aucune dépendance Streamlit n'est nécessaire.

## Flux de données
1. La SPA appelle `/api/*` (Vite proxy ou Nginx Docker).
2. FastAPI valide les paramètres de filtres et réalise des requêtes SQL préparées en lecture seule.
3. Les métriques sont calculées à partir de SQLite ; la génération des données reste dans la commande de bootstrap.
4. Les réponses à l'investigation proviennent de l'agent Python avec sources et preuves structurées.

## Page par page
- **Overview** : KPI par période, revenus quotidiens, catégories, régions, statuts des paiements et top anomalies.
- **Transactions** : recherche, pagination, tri, régions et statuts, panneau de détails, export CSV de la page.
- **Anomalies** : scénarios d'injection, registre filtrable et inspection de lignes.
- **Investigation IA** : chat, suggestions, mode LangGraph optionnel, historique local, sources et éléments de preuve.
- **Qualité/ML** : déduplication, tests qualité, protocole temporel et comparaison des scores ML.

## Limites techniques honnêtes
- Le frontend est une démonstration locale, pas une solution de production authentifiée.
- Le générateur de transactions n'est pas une source métier réelle.
- Les alertes présentées sont des labels injectés pour l'évaluation ; ce ne sont pas des prédictions ML.
- Les modèles ML ont été évalués sur le même jeu synthétique et sont fournis séparément de l'affichage.
- L'accès au registre npm est indisponible dans l'environnement de génération actuel : compilation React complète à vérifier sur la machine de l'utilisateur par `npm install; npm run build`.
