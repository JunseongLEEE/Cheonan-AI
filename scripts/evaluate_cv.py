#!/usr/bin/env python3
"""Evaluate experiment results: compare against baseline, check domain validity, assess evaluation axis contribution.
천안 청년 자취방 안전지도 프로젝트용.
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPERIMENT_LOG = PROJECT_ROOT / "EXPERIMENT_LOG.csv"


def load_experiment_log():
    """Load experiment log as list of dicts."""
    if not EXPERIMENT_LOG.exists():
        return []
    with open(EXPERIMENT_LOG) as f:
        reader = csv.DictReader(f)
        return list(reader)


def get_baseline_score(log_entries, model_type=None):
    """Get the best baseline score from completed experiments."""
    completed = [e for e in log_entries if e.get("status") in ("COMPLETED", "INTEGRATE") and e.get("cv_score")]
    if model_type:
        completed = [e for e in completed if e.get("model_type") == model_type]
    if not completed:
        return None
    return max(float(e["cv_score"]) for e in completed)


def check_domain_validity(exp_path: Path, train_log: dict):
    """Check domain-specific validity for 천안 프로젝트."""
    flags = []

    # 천안 법정동코드 확인
    cheonan_codes = train_log.get("cheonan_codes", [])
    if cheonan_codes and set(cheonan_codes) != {"44131", "44133"}:
        flags.append(f"천안 외 법정동코드 포함: {cheonan_codes}")

    # SHAP 확인 (분류기 모델)
    model_type = train_log.get("model_type", "")
    if model_type == "gangton_classifier":
        shap_dir = exp_path / "shap"
        if not shap_dir.exists() or not any(shap_dir.iterdir()):
            flags.append("SHAP 출력 누락 — 깡통전세 분류기는 SHAP 필수")

    # 피처 중요도에 전세가율 포함 확인
    feat_imp = train_log.get("feature_importance", {})
    if model_type == "gangton_classifier" and feat_imp:
        jeonse_related = [k for k in feat_imp if "전세" in k or "jeonse" in k.lower() or "rate" in k.lower()]
        if not jeonse_related:
            flags.append("피처 중요도에 전세가율 관련 피처가 없음 — 도메인 적합성 확인 필요")

    # 데이터 출처 확인
    data_sources = train_log.get("data_sources", [])
    if not data_sources:
        flags.append("data_sources 미기재 — 출처 명기 필요 (대회 규정)")

    return flags


def check_stability(cv_scores: list):
    """Check CV stability."""
    if not cv_scores or len(cv_scores) < 2:
        return [], "N/A"

    cv_std = np.std(cv_scores)
    cv_mean = np.mean(cv_scores)
    flags = []

    # Stability grade
    if cv_std < 0.005:
        grade = "A"
    elif cv_std < 0.01:
        grade = "B"
    elif cv_std < 0.02:
        grade = "C"
    else:
        grade = "D"

    # Check fold deviation
    if cv_std > 0:
        max_deviation = max(abs(s - cv_mean) for s in cv_scores)
        if max_deviation > 3 * cv_std:
            flags.append(f"단일 fold가 평균에서 {max_deviation/cv_std:.1f}σ 벗어남")

    return flags, grade


def evaluate(exp_path: Path):
    """Full evaluation of an experiment."""
    exp_path = Path(exp_path).resolve()

    if not exp_path.exists():
        print(f"ERROR: {exp_path} not found")
        sys.exit(1)

    # Load training results
    train_log_path = exp_path / "train_log.json"
    if not train_log_path.exists():
        print("ERROR: train_log.json not found. Run the experiment first.")
        sys.exit(1)

    with open(train_log_path) as f:
        results = json.load(f)

    cv_scores = results.get("cv_scores", [])
    cv_mean = results.get("cv_mean", 0)
    cv_std = results.get("cv_std", 0)
    model_type = results.get("model_type", "unknown")

    # Load log for comparison
    log_entries = load_experiment_log()
    baseline_score = get_baseline_score(log_entries, model_type)

    # Run checks
    stability_flags, stability_grade = check_stability(cv_scores)
    domain_flags = check_domain_validity(exp_path, results)

    # Compute improvement
    improvement = (cv_mean - baseline_score) if baseline_score else None

    # Evaluation axis contribution
    axis_contribution = {
        "주제적합성": "HIGH" if model_type == "gangton_classifier" else "MEDIUM",
        "창의성": "HIGH" if model_type in ("anomaly_detection", "graph") else "MEDIUM",
        "데이터적정성": "HIGH" if results.get("data_sources") else "LOW",
        "활용가능성": "HIGH" if results.get("shap_generated") else "MEDIUM",
    }

    # Recommendation
    if domain_flags and any("SHAP" not in f for f in domain_flags):
        recommendation = "REJECT"
        reason = f"도메인 체크 실패: {'; '.join(domain_flags)}"
    elif baseline_score and cv_mean < baseline_score:
        recommendation = "REJECT"
        reason = f"CV ({cv_mean:.6f}) < baseline ({baseline_score:.6f})"
    elif stability_grade == "D":
        recommendation = "REVIEW"
        reason = "CV 분산 과다 (grade D)"
    elif domain_flags:
        recommendation = "REVIEW"
        reason = f"도메인 경고: {'; '.join(domain_flags)}"
    else:
        recommendation = "INTEGRATE"
        reason = f"개선: {improvement:+.6f}" if improvement else "첫 실험"

    # Build report
    report = {
        "experiment_id": exp_path.name,
        "evaluation_date": datetime.now().strftime("%Y-%m-%d"),
        "model_type": model_type,
        "cv_score": cv_mean,
        "cv_std": cv_std,
        "cv_fold_scores": cv_scores,
        "baseline_score": baseline_score,
        "improvement": improvement,
        "stability_grade": stability_grade,
        "stability_flags": stability_flags,
        "domain_flags": domain_flags,
        "axis_contribution": axis_contribution,
        "recommendation": recommendation,
        "reason": reason,
    }

    # Print report
    print(f"\n{'='*60}")
    print(f"EVALUATION: {exp_path.name}")
    print(f"{'='*60}")
    print(f"  Model Type:   {model_type}")
    print(f"  CV Score:     {cv_mean:.6f} +/- {cv_std:.6f}")
    if baseline_score:
        print(f"  Baseline:     {baseline_score:.6f}")
        print(f"  Improvement:  {improvement:+.6f}")
    else:
        print(f"  Baseline:     N/A (첫 실험)")
    print(f"  Stability:    {stability_grade}")
    print(f"  Domain Check: {'PASS' if not domain_flags else 'FLAGS'}")
    for flag in domain_flags:
        print(f"    - {flag}")
    for flag in stability_flags:
        print(f"    - {flag}")
    print(f"  평가축 기여:")
    for axis, level in axis_contribution.items():
        print(f"    {axis}: {level}")
    print(f"  Recommendation: {recommendation}")
    print(f"  Reason: {reason}")
    print(f"{'='*60}")

    # Save evaluation report
    eval_path = exp_path / "evaluation.json"
    with open(eval_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nSaved evaluation to: {eval_path}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate experiment results")
    parser.add_argument("--exp", required=True, help="Path to experiment directory")
    args = parser.parse_args()

    evaluate(Path(args.exp))
