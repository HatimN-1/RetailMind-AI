from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
OUTPUT = ROOT / "docs" / "assets" / "v4_7"

OUTPUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(REPORTS / "spark_benchmark_summary.csv")
df = df.sort_values("Volume")

required = {
    "Volume", "Runs", "MedianSeconds",
    "MeanSeconds", "TransactionsPerSecond"
}

if not required.issubset(df.columns):
    raise ValueError("Colonnes manquantes dans le résumé benchmark")

volumes = df["Volume"]
labels = [f"{int(v):,}".replace(",", " ") for v in volumes]

# Graphique 1 : temps d'exécution
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(volumes, df["MedianSeconds"], marker="o", linewidth=2)

for x, y in zip(volumes, df["MedianSeconds"]):
    ax.annotate(f"{y:.2f}s", (x, y), xytext=(0, 10),
                textcoords="offset points", ha="center")

ax.set_title("RetailMind AI - Spark Execution Time")
ax.set_xlabel("Transactions")
ax.set_ylabel("Median execution time (seconds)")
ax.set_xticks(volumes, labels)
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(OUTPUT / "spark_execution_time.png", dpi=180)
plt.close(fig)

# Graphique 2 : débit
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(volumes, df["TransactionsPerSecond"], marker="o", linewidth=2)

for x, y in zip(volumes, df["TransactionsPerSecond"]):
    ax.annotate(f"{y:.2f} tx/s", (x, y), xytext=(0, 10),
                textcoords="offset points", ha="center")

ax.set_title("RetailMind AI - Spark Throughput")
ax.set_xlabel("Transactions")
ax.set_ylabel("Transactions per second")
ax.set_xticks(volumes, labels)
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(OUTPUT / "spark_throughput.png", dpi=180)
plt.close(fig)

# Graphique 3 : montée en charge
baseline = df.iloc[0]
observed = df["TransactionsPerSecond"] / baseline["TransactionsPerSecond"]
ideal = volumes / baseline["Volume"]

fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(volumes, observed, marker="o",
        linewidth=2, label="Observed throughput")
ax.plot(volumes, ideal, marker="s",
        linestyle="--", label="Ideal linear scaling")

ax.set_title("RetailMind AI - Scaling Analysis")
ax.set_xlabel("Transactions")
ax.set_ylabel("Relative throughput (baseline = 1)")
ax.set_xticks(volumes, labels)
ax.legend()
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(OUTPUT / "spark_scaling_analysis.png", dpi=180)
plt.close(fig)

print("BENCHMARK VISUALIZATION: PASSED")
print(f"Output directory: {OUTPUT}")

for path in sorted(OUTPUT.glob("*.png")):
    print(f"Generated: {path.name}")
