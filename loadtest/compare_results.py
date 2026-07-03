import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# 결과 폴더 경로
BASE_DIR = os.path.join(os.path.dirname(__file__), "results", "baseline_random")

VERSIONS = {
    "no_cache": "No Cache",
    "exact_cache": "Exact Cache\n(Redis)",
    "embedding_cache": "Embedding\nNaive",
    "embedding_cache_pgvector": "Embedding\npgvector",
}

COLORS = ["#e74c3c", "#f39c12", "#e67e22", "#27ae60"]


def load_input_stats(folder: str) -> dict:
    """requests.csv에서 /input 엔드포인트 통계 추출."""
    path = os.path.join(BASE_DIR, folder, "requests.csv")
    df = pd.read_csv(path)
    row = df[df["Name"] == "/input"]
    if row.empty:
        row = df[df["Name"].str.contains("input", na=False)]
    row = row.iloc[0]
    return {
        "p50": row["50%"],
        "p95": row["95%ile (ms)"] if "95%ile (ms)" in row else row["95%"],
        "rps": row["Requests/s"],
        "error_rate": (row["Failure Count"] / row["Request Count"] * 100)
        if row["Request Count"] > 0
        else 0,
    }


def load_aggregated_stats(folder: str) -> dict:
    """requests.csv에서 Aggregated 통계 추출."""
    path = os.path.join(BASE_DIR, folder, "requests.csv")
    df = pd.read_csv(path)
    row = df[df["Name"] == "Aggregated"].iloc[0]
    return {
        "rps": row["Requests/s"],
    }


def main():
    stats = {}
    for folder, label in VERSIONS.items():
        try:
            s = load_input_stats(folder)
            agg = load_aggregated_stats(folder)
            s["total_rps"] = agg["rps"]
            stats[label] = s
            print(f"{label}: p50={s['p50']}ms, p95={s['p95']}ms, rps={s['rps']}")
        except Exception as e:
            print(f"[ERROR] {folder}: {e}")

    labels = list(stats.keys())
    p50_vals = [stats[l]["p50"] for l in labels]
    p95_vals = [stats[l]["p95"] for l in labels]
    rps_vals = [stats[l]["total_rps"] for l in labels]
    hit_rates = [0, 11.5, 0, 18.2]  # 직접 입력 (측정값)

    x = np.arange(len(labels))
    width = 0.35

    fig, axes = plt.subplots(1, 3, figsize=(16, 6))
    fig.suptitle(
        "AI Personal Assistant — Caching Strategy Comparison\n(50 concurrent users, 5 min)",
        fontsize=14,
        fontweight="bold",
        y=1.02,
    )

    # --- 그래프 1: /input 응답시간 ---
    ax1 = axes[0]
    bars1 = ax1.bar(x - width / 2, p50_vals, width, label="p50", color=COLORS, alpha=0.85)
    bars2 = ax1.bar(x + width / 2, p95_vals, width, label="p95", color=COLORS, alpha=0.45)
    ax1.set_title("POST /input Response Time (ms)", fontweight="bold")
    ax1.set_ylabel("Response Time (ms)")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=9)
    ax1.legend(["p50", "p95"])
    for bar in bars1:
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 30,
            f"{int(bar.get_height())}",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    # --- 그래프 2: 캐시 히트율 ---
    ax2 = axes[1]
    bar_colors = [COLORS[i] for i in range(len(labels))]
    bars3 = ax2.bar(labels, hit_rates, color=bar_colors, alpha=0.85)
    ax2.set_title("Cache Hit Rate (%)", fontweight="bold")
    ax2.set_ylabel("Hit Rate (%)")
    ax2.set_ylim(0, 30)
    for bar, val in zip(bars3, hit_rates):
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            f"{val}%",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )

    # --- 그래프 3: RPS ---
    ax3 = axes[2]
    bars4 = ax3.bar(labels, rps_vals, color=bar_colors, alpha=0.85)
    ax3.set_title("Total RPS (Requests per Second)", fontweight="bold")
    ax3.set_ylabel("RPS")
    for bar in bars4:
        ax3.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.2,
            f"{bar.get_height():.1f}",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )

    plt.tight_layout()

    output_path = os.path.join(os.path.dirname(__file__), "results", "comparison.png")
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"\n저장 완료: {output_path}")
    plt.show()


if __name__ == "__main__":
    main()