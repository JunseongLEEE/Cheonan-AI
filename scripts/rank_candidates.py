#!/usr/bin/env python3
"""Rank components for final service and presentation.
천안 청년 자취방 안전지도 프로젝트 — 대회 평가축 기반 순위.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPERIMENTS_DIR = PROJECT_ROOT / "experiments"
CANDIDATES_MD = PROJECT_ROOT / "SUBMISSION_CANDIDATES.md"


AXIS_WEIGHTS = {
    "주제적합성": 0.20,
    "창의성": 0.20,
    "데이터적정성": 0.20,
    "활용가능성": 0.20,
    "기획력": 0.20,
}

LEVEL_SCORES = {"HIGH": 1.0, "MEDIUM": 0.5, "LOW": 0.2}

# 시연 임팩트 사전 정의
DEMO_IMPACT = {
    "gangton_classifier": 0.9,   # SHAP 막대그래프 → 매우 직관적
    "safety_score": 0.7,         # 점수 + 신호등 → 직관적
    "anomaly_detection": 0.5,    # 그래프 시각화 가능하나 설명 필요
    "recommender": 0.6,          # 대체 매물 추천 → 실용적
    "timeseries": 0.4,           # 추세 그래프 → 보조적
    "graph": 0.5,                # 네트워크 시각화 → 창의적이나 복잡
}


def load_components():
    """Find all evaluated experiments."""
    components = []

    for exp_dir in sorted(EXPERIMENTS_DIR.glob("exp_*")):
        eval_path = exp_dir / "evaluation.json"
        train_log_path = exp_dir / "train_log.json"

        if not eval_path.exists():
            continue

        with open(eval_path) as f:
            evaluation = json.load(f)

        if evaluation.get("recommendation") not in ("INTEGRATE", "REVIEW"):
            continue

        model_type = evaluation.get("model_type", "unknown")
        cv_score = evaluation.get("cv_score", 0)
        cv_std = evaluation.get("cv_std", 0)
        axis_contrib = evaluation.get("axis_contribution", {})

        # 평가축 커버리지 점수
        axis_score = sum(
            LEVEL_SCORES.get(level, 0) * AXIS_WEIGHTS.get(axis, 0)
            for axis, level in axis_contrib.items()
        )

        # 시연 임팩트
        demo_score = DEMO_IMPACT.get(model_type, 0.3)

        # 구현 완성도 (train_log 존재 + CV > 0)
        readiness = 1.0 if cv_score > 0 else 0.3

        components.append({
            "experiment_id": exp_dir.name,
            "model_type": model_type,
            "cv_score": cv_score,
            "cv_std": cv_std,
            "axis_score": axis_score,
            "demo_score": demo_score,
            "readiness": readiness,
            "recommendation": evaluation.get("recommendation"),
            "stability_grade": evaluation.get("stability_grade", "N/A"),
        })

    return components


def compute_composite(component, all_components):
    """Compute composite ranking score."""
    scores = [c["cv_score"] for c in all_components if c["cv_score"] > 0]

    if scores:
        max_score = max(scores)
        min_score = min(scores)
        score_range = max_score - min_score if max_score != min_score else 1
        norm_cv = (component["cv_score"] - min_score) / score_range if component["cv_score"] > 0 else 0
    else:
        norm_cv = 0

    composite = (
        0.3 * norm_cv
        + 0.3 * component["axis_score"]
        + 0.2 * component["demo_score"]
        + 0.2 * component["readiness"]
    )
    return round(composite, 3)


def rank_components(components):
    """Rank and classify components."""
    for c in components:
        c["composite"] = compute_composite(c, components)

    ranked = sorted(components, key=lambda x: x["composite"], reverse=True)

    # Classify priority
    must_types = {"gangton_classifier"}  # 깡통전세 분류기는 반드시 포함
    for c in ranked:
        if c["model_type"] in must_types:
            c["priority"] = "MUST"
        elif c["composite"] >= 0.7:
            c["priority"] = "SHOULD"
        else:
            c["priority"] = "NICE_TO_HAVE"

    return ranked


def update_candidates_md(ranked):
    """Update SUBMISSION_CANDIDATES.md."""
    today = datetime.now().strftime("%Y-%m-%d")

    lines = [
        "# Component Ranking — 천안 자취방 안전지도\n",
        f"\n## 최종 서비스 포함 우선순위 ({today})\n\n",
        "| 순위 | 실험 | 모델 유형 | CV Score | 평가축 | 시연 | 완성도 | 종합 | 우선순위 |\n",
        "|------|------|----------|----------|--------|------|--------|------|----------|\n",
    ]

    for i, c in enumerate(ranked, 1):
        lines.append(
            f"| {i} | {c['experiment_id']} | {c['model_type']} | "
            f"{c['cv_score']:.4f} | {c['axis_score']:.2f} | {c['demo_score']:.1f} | "
            f"{c['readiness']:.1f} | {c['composite']:.3f} | {c['priority']} |\n"
        )

    lines.extend([
        "\n## 순위 기준\n",
        "1. **모델 성능** (30%) — CV score\n",
        "2. **평가축 커버리지** (30%) — 5대 평가축 기여도\n",
        "3. **시연 임팩트** (20%) — PT에서 시각적 효과\n",
        "4. **구현 완성도** (20%) — 실제 동작 여부\n",
        "\n## 우선순위 분류\n",
        "- **MUST**: 핵심 차별성, 반드시 포함\n",
        "- **SHOULD**: 높은 가치, 가능하면 포함\n",
        "- **NICE_TO_HAVE**: 시간 여유 시 포함\n",
    ])

    CANDIDATES_MD.write_text("".join(lines))
    print(f"Updated: {CANDIDATES_MD}")


def main():
    print("Ranking components for 천안 자취방 안전지도...")
    print(f"{'='*50}")

    components = load_components()
    print(f"Found {len(components)} evaluated components")

    if not components:
        print("No evaluated components found. Run /eval first.")
        sys.exit(0)

    ranked = rank_components(components)

    print(f"\nRanking:")
    for i, c in enumerate(ranked, 1):
        print(f"  {i}. [{c['priority']}] {c['experiment_id']} — {c['model_type']} (score: {c['composite']:.3f})")

    update_candidates_md(ranked)


if __name__ == "__main__":
    main()
