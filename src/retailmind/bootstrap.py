"""One command to build an offline end-to-end demo."""
from __future__ import annotations
import argparse
import json
from retailmind import generate, etl, warehouse, train


def run(rows: int = 5000, seed: int = 42, deep: bool = False) -> dict:
    return {"generator": generate.generate(rows, seed),
            "quality": etl.run(),
            "warehouse": warehouse.build(),
            "models": train.run(train_torch=deep, seed=seed)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--torch", action="store_true")
    args = parser.parse_args()
    result = run(args.rows, args.seed, args.torch)
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
