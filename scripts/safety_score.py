#!/usr/bin/env python3
"""
8축 종합 안전점수 계산

가용 데이터 기반 축:
  1. 금융안전 (0.25) — 전세가율, 보증금/매매가
  2. 건물노후 (0.15) — 건물연령, 구조, 내진설계
  3. 침수위험 (0.10) — 미구현 (WMS only → 0.5 기본값)
  4. 치안 (0.15) — SGIS proxy: 인구당 사업체수 + 인구밀도
  5. 소방 (0.05) — 미구현 → 0.5 기본값
  6. 교통 (0.10) — 미구현 → 0.5 기본값
  7. 편의시설 (0.10) — SGIS proxy: 인구당 사업체·종사자 밀도
  8. 환경 (0.10) — SGIS proxy: 가구대비 주택비율 (적정 공급)

→ 금융+건물노후+치안+편의+환경 5축 데이터 반영, 침수/소방/교통 중립값
"""

from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# 행정동(SGIS) → 법정동 매핑 (천안시)
# 행정동 1개가 여러 법정동을 관할하므로 법정동→행정동 역매핑 사용
BJDONG_TO_HJDONG = {
    # 동남구 읍면
    "목천읍 삼성리": "목천읍", "목천읍 신계리": "목천읍", "목천읍 운전리": "목천읍",
    "목천읍 응원리": "목천읍", "목천읍 서리": "목천읍",
    "풍세면 보성리": "풍세면",
    "북면 상동리": "북면", "북면 연춘리": "북면",
    "성남면 석곡리": "성남면",
    "병천면 가전리": "병천면", "병천면 병천리": "병천면", "병천면 탑원리": "병천면",
    # 동남구 동
    "대흥동": "중앙동", "사직동": "중앙동", "문화동": "중앙동",
    "구성동": "문성동", "오룡동": "문성동",
    "원성동": "원성1동", "삼룡동": "원성1동",  # 원성1동 관할
    "청수동": "원성2동", "구룡동": "원성2동",
    "봉명동": "봉명동",
    "성황동": "일봉동", "영성동": "일봉동", "와촌동": "일봉동",
    "신방동": "신방동",
    "신부동": "청룡동", "용곡동": "청룡동",
    "안서동": "신안동", "청당동": "신안동",
    # 서북구 읍면
    "성환읍 매주리": "성환읍", "성환읍 송덕리": "성환읍", "성환읍 수향리": "성환읍",
    "성환읍 율금리": "성환읍", "성환읍 성월리": "성환읍",
    "성거읍 요방리": "성거읍", "성거읍 저리": "성거읍", "성거읍 문덕리": "성거읍",
    "성거읍 천흥리": "성거읍", "성거읍 신월리": "성거읍", "성거읍 송남리": "성거읍",
    "성거읍 오목리": "성거읍",
    "직산읍 군서리": "직산읍", "직산읍 수헐리": "직산읍", "직산읍 상덕리": "직산읍",
    "직산읍 부송리": "직산읍", "직산읍 모시리": "직산읍", "직산읍 삼은리": "직산읍",
    "직산읍 군동리": "직산읍",
    "입장면 기로리": "입장면", "입장면 도림리": "입장면", "입장면 신덕리": "입장면",
    "입장면 하장리": "입장면",
    # 서북구 동
    "성정동": "성정1동",  # 대부분 성정1동 관할
    "쌍용동": "쌍용1동",
    "두정동": "쌍용2동",
    "백석동": "백석동",
    "불당동": "불당1동",
    "차암동": "부성1동",
    "부대동": "부성2동", "성성동": "부성2동",
    "다가동": "성정2동",
    "신당동": "쌍용3동", "유량동": "쌍용3동",
    "업성동": "불당2동",
}

# 가중치
WEIGHTS = {
    "금융안전": 0.25,
    "건물노후": 0.15,
    "침수위험": 0.10,
    "치안": 0.15,
    "소방": 0.05,
    "교통": 0.10,
    "편의시설": 0.10,
    "환경": 0.10,
}

# 전세가율 → 금융안전 점수 (0~1, 높을수록 안전)
def financial_score(jeonse_rate: float) -> float:
    if jeonse_rate <= 0.60:
        return 1.0
    elif jeonse_rate <= 0.75:
        return 1.0 - (jeonse_rate - 0.60) / 0.15 * 0.3  # 1.0 → 0.7
    elif jeonse_rate <= 0.80:
        return 0.7 - (jeonse_rate - 0.75) / 0.05 * 0.2  # 0.7 → 0.5
    elif jeonse_rate <= 0.90:
        return 0.5 - (jeonse_rate - 0.80) / 0.10 * 0.3  # 0.5 → 0.2
    else:
        return max(0.0, 0.2 - (jeonse_rate - 0.90) / 0.10 * 0.2)  # 0.2 → 0.0


# 건물연령 → 노후도 점수 (0~1, 높을수록 안전)
def building_score(age: float, seismic: bool = False) -> float:
    if pd.isna(age):
        return 0.5

    if age <= 10:
        base = 1.0
    elif age <= 20:
        base = 1.0 - (age - 10) / 10 * 0.2  # 1.0 → 0.8
    elif age <= 30:
        base = 0.8 - (age - 20) / 10 * 0.3  # 0.8 → 0.5
    elif age <= 40:
        base = 0.5 - (age - 30) / 10 * 0.2  # 0.5 → 0.3
    else:
        base = max(0.1, 0.3 - (age - 40) / 20 * 0.2)

    # 내진설계 보너스
    if seismic:
        base = min(1.0, base + 0.1)

    return base


def security_score(pop_density: float, biz_per_capita: float) -> float:
    """치안 proxy 점수 (0~1). 인구밀도 높고 사업체 많으면 안전."""
    if pd.isna(pop_density) or pd.isna(biz_per_capita):
        return 0.5

    # 인구밀도 점수 (적정 밀도 20000~50000이 안전, 너무 낮으면 취약)
    if pop_density >= 30000:
        density_s = 0.8
    elif pop_density >= 15000:
        density_s = 0.5 + (pop_density - 15000) / 15000 * 0.3
    else:
        density_s = max(0.2, 0.5 * pop_density / 15000)

    # 인구당 사업체수 (높을수록 생활 인프라 = 눈 많음 = 안전)
    # 천안 평균 ~0.08 정도
    if biz_per_capita >= 0.12:
        biz_s = 0.9
    elif biz_per_capita >= 0.06:
        biz_s = 0.5 + (biz_per_capita - 0.06) / 0.06 * 0.4
    else:
        biz_s = max(0.2, 0.5 * biz_per_capita / 0.06)

    return density_s * 0.4 + biz_s * 0.6


def amenity_score(biz_per_capita: float, worker_per_capita: float) -> float:
    """편의시설 proxy 점수 (0~1). 사업체·종사자 밀도."""
    if pd.isna(biz_per_capita) or pd.isna(worker_per_capita):
        return 0.5

    # 인구당 종사자수 (높으면 상업/서비스 인프라 풍부)
    if worker_per_capita >= 0.5:
        worker_s = 0.9
    elif worker_per_capita >= 0.2:
        worker_s = 0.5 + (worker_per_capita - 0.2) / 0.3 * 0.4
    else:
        worker_s = max(0.2, 0.5 * worker_per_capita / 0.2)

    # 사업체 밀도 재활용
    if biz_per_capita >= 0.10:
        biz_s = 0.85
    elif biz_per_capita >= 0.05:
        biz_s = 0.5 + (biz_per_capita - 0.05) / 0.05 * 0.35
    else:
        biz_s = max(0.2, 0.5 * biz_per_capita / 0.05)

    return biz_s * 0.5 + worker_s * 0.5


def environment_score(house_ratio: float) -> float:
    """환경 proxy 점수 (0~1). 가구대비 주택비율 — 적정 공급이면 높음."""
    if pd.isna(house_ratio):
        return 0.5

    # 1.0 근처가 적정, 너무 낮으면 주택 부족 (과밀), 너무 높으면 공실
    if 0.85 <= house_ratio <= 1.15:
        return 0.9
    elif 0.70 <= house_ratio <= 1.30:
        return 0.7
    elif 0.50 <= house_ratio <= 1.50:
        return 0.5
    else:
        return 0.3


def compute_dong_safety():
    """동별 종합 안전점수 계산."""
    # 전세가율 데이터
    df_rate = pd.read_parquet(PROCESSED_DIR / "jeonse_rate.parquet")
    df_bldg = pd.read_parquet(PROCESSED_DIR / "building_residential.parquet")
    df_sgis = pd.read_parquet(PROCESSED_DIR / "sgis_dong_stats.parquet")

    # 최근 3년 전세가율
    recent = df_rate[df_rate["연월"].astype(str) >= "2022-01"]
    dong_jeonse = recent.groupby("법정동명")["전세가율"].agg(["mean", "median", "count"]).reset_index()
    dong_jeonse.columns = ["법정동명", "전세가율_평균", "전세가율_중앙값", "전세거래수"]

    # 동별 건물 통계
    dong_bldg = df_bldg.groupby("법정동명").agg(
        건물수=("건물연령", "count"),
        평균건물연령=("건물연령", "mean"),
        노후비율=("건물연령", lambda x: (x >= 25).mean()),
        내진비율=("내진설계", "mean"),
    ).reset_index()

    # SGIS 통계 준비 (행정동 기준)
    sgis_cols = df_sgis[["읍면동명", "총인구", "인구밀도", "사업체수", "종사자수",
                          "가구대비_주택비율"]].copy()
    sgis_cols = sgis_cols.rename(columns={"읍면동명": "행정동명"})
    sgis_cols["인구당_사업체수"] = sgis_cols["사업체수"] / sgis_cols["총인구"].replace(0, np.nan)
    sgis_cols["인구당_종사자수"] = sgis_cols["종사자수"] / sgis_cols["총인구"].replace(0, np.nan)

    # 병합
    result = dong_jeonse.merge(dong_bldg, on="법정동명", how="outer")

    # 법정동 → 행정동 매핑 후 SGIS 조인
    result["행정동명"] = result["법정동명"].map(BJDONG_TO_HJDONG).fillna(result["법정동명"])
    result = result.merge(sgis_cols, on="행정동명", how="left")

    # 축별 점수 계산
    result["금융안전_점수"] = result["전세가율_평균"].apply(
        lambda x: financial_score(x) if pd.notna(x) else 0.5
    )
    result["건물노후_점수"] = result.apply(
        lambda row: building_score(
            row.get("평균건물연령", None),
            row.get("내진비율", 0) > 0.3
        ),
        axis=1,
    )

    # SGIS 기반 축
    result["치안_점수"] = result.apply(
        lambda row: security_score(row.get("인구밀도"), row.get("인구당_사업체수")),
        axis=1,
    )
    result["편의시설_점수"] = result.apply(
        lambda row: amenity_score(row.get("인구당_사업체수"), row.get("인구당_종사자수")),
        axis=1,
    )
    result["환경_점수"] = result["가구대비_주택비율"].apply(environment_score)

    # 아직 미구현 축
    for axis in ["침수위험", "소방", "교통"]:
        result[f"{axis}_점수"] = 0.5

    # 종합 점수 (가중합 → 0~100)
    result["종합안전점수"] = 0
    for axis, weight in WEIGHTS.items():
        result["종합안전점수"] += result[f"{axis}_점수"] * weight
    result["종합안전점수"] = (result["종합안전점수"] * 100).round(1)

    # 신호등
    result["신호등"] = "노랑"
    result.loc[result["종합안전점수"] >= 65, "신호등"] = "초록"
    result.loc[result["종합안전점수"] < 45, "신호등"] = "빨강"

    return result


def main():
    print("=" * 60)
    print("8축 종합 안전점수 — 동별 계산")
    print("=" * 60)

    result = compute_dong_safety()
    result = result.sort_values("종합안전점수", ascending=True)

    print(f"\n총 {len(result)}개 동 분석")
    print(f"\n{'동':>12} | {'종합':>5} | {'신호등':>4} | {'금융':>4} | {'건물':>4} | {'전세가율':>6} | {'건물연령':>5}")
    print("-" * 70)

    for _, row in result.iterrows():
        dong = row["법정동명"] if pd.notna(row["법정동명"]) else "?"
        total = row["종합안전점수"]
        signal = row["신호등"]
        fin = row["금융안전_점수"]
        bld = row["건물노후_점수"]
        jr = row.get("전세가율_평균", float("nan"))
        ba = row.get("평균건물연령", float("nan"))

        jr_str = f"{jr:.0%}" if pd.notna(jr) else "N/A"
        ba_str = f"{ba:.0f}년" if pd.notna(ba) else "N/A"
        signal_icon = {"빨강": "🔴", "노랑": "🟡", "초록": "🟢"}[signal]

        print(f"{dong:>12} | {total:>5.1f} | {signal_icon} {signal} | {fin:.2f} | {bld:.2f} | {jr_str:>6} | {ba_str:>5}")

    # 위험 동네 요약
    red = result[result["신호등"] == "빨강"]
    yellow = result[result["신호등"] == "노랑"]
    green = result[result["신호등"] == "초록"]
    print(f"\n🔴 빨강 (위험): {len(red)}개 동")
    print(f"🟡 노랑 (주의): {len(yellow)}개 동")
    print(f"🟢 초록 (안전): {len(green)}개 동")

    # 저장
    out_path = PROCESSED_DIR / "dong_safety_score.parquet"
    result.to_parquet(out_path, index=False)
    print(f"\n저장: {out_path}")
    print("✅ 안전점수 계산 완료")


if __name__ == "__main__":
    main()
