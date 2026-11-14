# RetailMind AI · Frontend professionnel

Stack : React 18, TypeScript 5, Vite 6, Recharts 2, Lucide React et CSS responsive.
**Aucun composant Streamlit.**

```powershell
npm install
npm run dev
```

Ouvrir http://localhost:5173, avec FastAPI actif sur http://127.0.0.1:8000.
Pour vérifier la compilation : `npm run build`.
Le serveur de développement Vite relaie `/api` vers le backend (`vite.config.ts`).

## Écrans
- Vue exécutive : KPI, périodes, revenus quotidiens, régions et catégories.
- Transactions : filtres, tri SQL, pagination, détails dans un drawer.
- Anomalies : typologie et exploration des étiquettes injectées.
- Investigation : chat, questions suggérées, sources SQL/runbooks, option LangGraph.
- Qualité & ML : contrôles de données et comparaison de modèles.

Les données, les événements d'anomalies et les résultats ML sont synthétiques.
Pas d'authentification de production. Le backend doit rester sur localhost pour la démo.
