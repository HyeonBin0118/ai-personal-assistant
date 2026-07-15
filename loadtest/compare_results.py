import os
import matplotlib.pyplot as plt
import matplotlib
import numpy as np

matplotlib.rcParams['font.family'] = 'DejaVu Sans'

BASE_DIR = os.path.join(os.path.dirname(__file__), "results")

COLORS_CACHE = ["#e74c3c", "#f39c12", "#e67e22", "#27ae60"]
COLORS_RAG   = ["#95a5a6", "#8e44ad", "#2980b9"]


def plot_cache_comparison():
    labels  = ["No Cache", "Exact Cache\n(Redis)", "Embedding\nNaive", "Embedding\npgvector"]
    p50     = [1500, 1300, 4600, 1600]
    p95     = [2800, 2100, 15000, 2800]
    error   = [2.2,  4.1,  4.5,  3.5]
    rps     = [16.9, 18.7, 5.0,  19.0]
    hit     = [None, 11.5, None, 18.2]  # None = N/A

    x = np.arange(len(labels))
    width = 0.35

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle(
        "Phase 4~6: Caching Strategy Comparison\n(50 concurrent users, 5 min)",
        fontsize=14, fontweight="bold"
    )

    # 응답시간
    ax1 = axes[0]
    b1 = ax1.bar(x - width/2, p50, width, color=COLORS_CACHE, alpha=0.9, label="p50")
    b2 = ax1.bar(x + width/2, p95, width, color=COLORS_CACHE, alpha=0.4, label="p95")
    ax1.set_title("Response Time (ms)", fontweight="bold")
    ax1.set_ylabel("ms")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=9)
    ax1.legend()
    for bar in b1:
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50,
                 f"{int(bar.get_height())}", ha="center", fontsize=8)

    # 에러율
    ax2 = axes[1]
    bars2 = ax2.bar(labels, error, color=COLORS_CACHE, alpha=0.9)
    ax2.set_title("Error Rate (%)", fontweight="bold")
    ax2.set_ylabel("%")
    ax2.set_xticklabels(labels, fontsize=9)
    for bar, val in zip(bars2, error):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                 f"{val}%", ha="center", fontsize=9, fontweight="bold")

    # RPS + 캐시 히트율 (우축)
    ax3 = axes[2]
    ax3_twin = ax3.twinx()
    bars3 = ax3.bar(x - width/2, rps, width, color=COLORS_CACHE, alpha=0.9, label="RPS")
    hit_vals   = [v if v is not None else 0 for v in hit]
    hit_labels_text = [f"{v}%" if v is not None else "N/A" for v in hit]
    bars4 = ax3_twin.bar(x + width/2, hit_vals, width, color=COLORS_CACHE, alpha=0.4, label="Hit Rate")
    ax3.set_title("RPS & Cache Hit Rate", fontweight="bold")
    ax3.set_ylabel("RPS")
    ax3_twin.set_ylabel("Hit Rate (%)")
    ax3_twin.set_ylim(0, 30)
    ax3.set_xticks(x)
    ax3.set_xticklabels(labels, fontsize=9)
    for bar in bars3:
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                 f"{bar.get_height():.1f}", ha="center", fontsize=8, fontweight="bold")
    for bar, label in zip(bars4, hit_labels_text):
        if label != "N/A" and bar.get_height() > 0:
            ax3_twin.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                          label, ha="center", fontsize=8, fontweight="bold")

    plt.tight_layout()
    path = os.path.join(BASE_DIR, "comparison_cache.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"저장: {path}")
    plt.show()


def plot_rag_comparison():
    labels = ["No Cache\n(baseline)", "RAG +\nLLM Intent", "RAG +\nKeyword Intent"]
    p50    = [1500, 2800, 2100]
    p95    = [2800, 5100, 3600]
    error  = [2.2,  22.9, 1.9]
    rps    = [16.9, 14.5, 17.6]

    x = np.arange(len(labels))
    width = 0.35

    fig, axes = plt.subplots(1, 3, figsize=(14, 6))
    fig.suptitle(
        "Phase 7~9: RAG Pipeline & Optimization\n(50 concurrent users, 5 min)",
        fontsize=14, fontweight="bold"
    )

    # 응답시간
    ax1 = axes[0]
    b1 = ax1.bar(x - width/2, p50, width, color=COLORS_RAG, alpha=0.9, label="p50")
    b2 = ax1.bar(x + width/2, p95, width, color=COLORS_RAG, alpha=0.4, label="p95")
    ax1.set_title("Response Time (ms)", fontweight="bold")
    ax1.set_ylabel("ms")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=9)
    ax1.legend()
    for bar in b1:
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 30,
                 f"{int(bar.get_height())}", ha="center", fontsize=9)

    # 에러율
    ax2 = axes[1]
    bars2 = ax2.bar(labels, error, color=COLORS_RAG, alpha=0.9)
    ax2.set_title("Error Rate (%)", fontweight="bold")
    ax2.set_ylabel("%")
    ax2.set_xticklabels(labels, fontsize=9)
    for bar, val in zip(bars2, error):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                 f"{val}%", ha="center", fontsize=10, fontweight="bold")

    # RPS
    ax3 = axes[2]
    bars3 = ax3.bar(labels, rps, color=COLORS_RAG, alpha=0.9)
    ax3.set_title("RPS (Requests per Second)", fontweight="bold")
    ax3.set_ylabel("RPS")
    ax3.set_ylim(0, 22)
    ax3.set_xticklabels(labels, fontsize=9)
    for bar in bars3:
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                 f"{bar.get_height():.1f}", ha="center", fontsize=10, fontweight="bold")

    plt.tight_layout()
    path = os.path.join(BASE_DIR, "comparison_rag.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"저장: {path}")
    plt.show()


if __name__ == "__main__":
    plot_cache_comparison()
    plot_rag_comparison()