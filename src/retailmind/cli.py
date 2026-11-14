"""RetailMind command line entrypoint."""
from __future__ import annotations
import argparse
import json


def main():
    parser = argparse.ArgumentParser(prog="retailmind")
    commands = parser.add_subparsers(dest="command", required=True)
    boot = commands.add_parser("bootstrap", help="generate -> ETL -> marts -> ML")
    boot.add_argument("--rows", type=int, default=5000)
    boot.add_argument("--seed", type=int, default=42)
    boot.add_argument("--torch", action="store_true")
    commands.add_parser("spark", help="optional Spark Parquet ETL")
    commands.add_parser("index", help="optional Qdrant dense RAG index")
    commands.add_parser("rag-status", help="read-only Qdrant index status")
    evaluation = commands.add_parser("evaluate-rag", help="measure actual retrieval, without silent fallback")
    evaluation.add_argument("--backend", choices=["tfidf", "qdrant"], default="tfidf")
    evaluation.add_argument("--output", type=str)
    investigation = commands.add_parser("investigate", help="grounded local investigation")
    investigation.add_argument("question", type=str)
    investigation.add_argument("--langgraph", action="store_true")
    args = parser.parse_args()
    if args.command == "bootstrap":
        from retailmind.bootstrap import run
        result = run(args.rows, args.seed, args.torch)
    elif args.command == "spark":
        from retailmind.spark_etl import run
        result = run()
    elif args.command == "index":
        from retailmind.retrieval import index_qdrant
        try:
            result = index_qdrant()
        except Exception as exc:
            parser.exit(1, json.dumps({"status": "index_failed", "error_type": type(exc).__name__,
                        "hint": "Vérifier les dépendances RAG, le modèle en cache et Qdrant. En mode local, arrêter FastAPI avant indexation."},
                        ensure_ascii=False) + "\n")
    elif args.command == "rag-status":
        from retailmind.retrieval import index_status
        result = index_status()
    elif args.command == "evaluate-rag":
        from pathlib import Path
        from retailmind.rag_evaluation import evaluate
        result = evaluate(args.backend)
        if args.output:
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        from retailmind.agent import investigate
        result = investigate(args.question, use_langgraph=args.langgraph)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if args.command == "evaluate-rag" and result["retrieval_errors"]:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
