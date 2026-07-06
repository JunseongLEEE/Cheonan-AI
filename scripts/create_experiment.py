#!/usr/bin/env python3
"""Create a new experiment directory with boilerplate config and code.
천안 청년 자취방 안전지도 프로젝트용.
"""

import argparse
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPERIMENTS_DIR = PROJECT_ROOT / "experiments"

MODEL_TYPES = ["gangton_classifier", "safety_score", "anomaly_detection", "recommender", "timeseries", "graph"]


def get_next_experiment_id():
    """Get the next experiment number."""
    existing = sorted(EXPERIMENTS_DIR.glob("exp_*"))
    if not existing:
        return 1
    last_num = int(existing[-1].name.split("_")[1])
    return last_num + 1


def get_git_commit():
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=PROJECT_ROOT
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def create_experiment(name: str, hypothesis: str, base: str = None, model_type: str = "gangton_classifier"):
    """Create a new experiment directory."""
    exp_num = get_next_experiment_id()
    exp_id = f"exp_{exp_num:03d}_{name}"
    exp_dir = EXPERIMENTS_DIR / exp_id

    if exp_dir.exists():
        print(f"ERROR: {exp_dir} already exists")
        return

    exp_dir.mkdir(parents=True)
    (exp_dir / "models").mkdir()
    if model_type == "gangton_classifier":
        (exp_dir / "shap").mkdir()

    # Copy base experiment if specified
    if base:
        base_dir = EXPERIMENTS_DIR / base
        if base_dir.exists():
            for f in ["train.py", "features.py", "model.py"]:
                src = base_dir / f
                if src.exists():
                    shutil.copy2(src, exp_dir / f)
            print(f"Copied base files from {base}")

    # Write config.yaml
    config_content = f"""experiment:
  id: {exp_id}
  hypothesis: "{hypothesis}"
  created: "{datetime.now().strftime('%Y-%m-%d %H:%M')}"
  git_commit: "{get_git_commit()}"
  status: PLANNED
  model_type: {model_type}
  evaluation_axis: "주제적합성|데이터적정성|활용가능성"

data:
  source_dir: ../../data/processed/
  raw_dir: ../../data/raw/
  cheonan_codes:
    - "44131"  # 동남구
    - "44133"  # 서북구

cv:
  n_splits: 5
  strategy: stratified  # stratified | pu_learning | spatial
  seed: 42

model:
  type: {model_type}
  params:
    # 모델별 하이퍼파라미터
    n_estimators: 1000
    learning_rate: 0.05
    early_stopping_rounds: 100

features:
  # 피처 엔지니어링 설정
  jeonse_rate: true           # 전세가율 (전세금/매매가)
  hug_126_ratio: true         # 공시가×1.26 대비 보증금
  building_age: true          # 건물연령 (현재연도-사용승인년도)
  area_features: true         # 전용면적, 세대수
  neighborhood_stats: true    # 동네 평균 전세가율, 거래량

output:
  model_dir: models/
  log_file: train_log.json
  shap_dir: shap/            # 분류기 모델일 때만
"""
    (exp_dir / "config.yaml").write_text(config_content)

    # Write README
    readme_content = f"""# {exp_id}

## Hypothesis
{hypothesis}

## Model Type
{model_type}

## Approach
<!-- 구현 방법 설명 -->

## Data Sources
<!-- 사용한 공공 API 데이터 출처 URL -->

## Expected Outcome
<!-- 예상 결과와 근거 -->

## Results
<!-- 실행 후 자동 채워짐 -->
- CV Score:
- CV Std:
- Runtime:
- SHAP: {'생성 예정' if model_type == 'gangton_classifier' else 'N/A'}

## Conclusion
<!-- 무엇을 배웠는가? -->
"""
    (exp_dir / "README.md").write_text(readme_content)

    # Write SUMMARY.md
    summary_template = PROJECT_ROOT / "experiments" / "TEMPLATE_SUMMARY.md"
    if summary_template.exists():
        shutil.copy2(summary_template, exp_dir / "SUMMARY.md")

    # Write minimal train.py if not copied from base
    if not (exp_dir / "train.py").exists():
        train_content = '''#!/usr/bin/env python3
"""Training script for 천안 자취방 안전지도 experiment."""

import json
import numpy as np
import yaml
from pathlib import Path
from datetime import datetime

# Load config
config_path = Path(__file__).parent / "config.yaml"
with open(config_path) as f:
    config = yaml.safe_load(f)

SEED = config["cv"]["seed"]
np.random.seed(SEED)


def main():
    exp_id = config["experiment"]["id"]
    model_type = config["experiment"]["model_type"]
    print(f"Running experiment: {exp_id}")
    print(f"Model type: {model_type}")
    print(f"Hypothesis: {config['experiment']['hypothesis']}")
    print(f"Cheonan codes: {config['data']['cheonan_codes']}")

    start_time = datetime.now()

    # TODO: Implement training pipeline
    # 1. Load processed data from ../../data/processed/
    # 2. Feature engineering (전세가율, 공시가 비율, 건물연령 등)
    # 3. CV loop (5-fold stratified or PU-learning)
    # 4. Train + evaluate
    # 5. SHAP explanations (분류기 모델)
    # 6. Save outputs

    elapsed = (datetime.now() - start_time).total_seconds()

    # Placeholder for results
    results = {
        "experiment_id": exp_id,
        "model_type": model_type,
        "cv_scores": [],
        "cv_mean": 0.0,
        "cv_std": 0.0,
        "metric_name": "f1",
        "runtime_seconds": elapsed,
        "n_features": 0,
        "feature_importance": {},
        "shap_generated": False,
        "data_sources": [],
        "cheonan_codes": config["data"]["cheonan_codes"],
    }

    # Save results
    with open("train_log.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"CV Score: {results['cv_mean']:.6f} +/- {results['cv_std']:.6f}")
    print(f"Runtime: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
'''
        (exp_dir / "train.py").write_text(train_content)

    # Write requirements.txt
    (exp_dir / "requirements.txt").write_text("# 추가 의존성 (기본: numpy, pandas, scikit-learn, lightgbm)\n")

    print(f"Created experiment: {exp_id}")
    print(f"  Directory: {exp_dir}")
    print(f"  Model type: {model_type}")
    print(f"  Status: PLANNED")
    print(f"  Next: implement train.py, then /run {exp_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a new experiment")
    parser.add_argument("--name", required=True, help="Short experiment name (no spaces)")
    parser.add_argument("--hypothesis", default="TBD", help="Experiment hypothesis")
    parser.add_argument("--base", default=None, help="Base experiment to copy from")
    parser.add_argument("--model", default="gangton_classifier",
                       choices=MODEL_TYPES, help="Model type")
    args = parser.parse_args()

    create_experiment(args.name, args.hypothesis, args.base, args.model)
