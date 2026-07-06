#!/usr/bin/env python3
"""
SGIS 통계 데이터 ETL — 읍면동별 인구/가구/주택 집계

출력: data/processed/sgis_dong_stats.parquet
"""

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "sgis"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# SGIS 행정동코드 → 읍면동명 매핑
DONG_CODE_MAP = {
    "34011110": "목천읍", "34011310": "풍세면", "34011320": "광덕면",
    "34011330": "북면", "34011340": "성남면", "34011350": "수신면",
    "34011360": "병천면", "34011370": "동면", "34011510": "중앙동",
    "34011520": "문성동", "34011530": "원성1동", "34011540": "원성2동",
    "34011550": "봉명동", "34011560": "일봉동", "34011570": "신방동",
    "34011580": "청룡동", "34011590": "신안동",
    "34012110": "성환읍", "34012120": "성거읍", "34012130": "직산읍",
    "34012310": "입장면", "34012510": "성정1동", "34012520": "성정2동",
    "34012530": "쌍용1동", "34012540": "쌍용2동", "34012550": "쌍용3동",
    "34012580": "백석동", "34012600": "부성1동", "34012610": "부성2동",
    "34012620": "불당1동", "34012630": "불당2동",
}


def load_sgis_json(api_name: str) -> list[dict]:
    """특정 API 유형의 모든 JSON 파일을 읽어 리스트로 반환."""
    api_dir = RAW_DIR / api_name
    if not api_dir.exists():
        return []

    all_items = []
    for f in sorted(api_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, list):
                all_items.extend(data)
            elif isinstance(data, dict) and "result" in data:
                result = data["result"]
                if isinstance(result, list):
                    all_items.extend(result)
        except Exception:
            pass

    return all_items


def aggregate_population() -> pd.DataFrame:
    """인구통계를 읍면동 단위로 집계."""
    items = load_sgis_json("population")
    if not items:
        print("  인구통계 데이터 없음")
        return pd.DataFrame()

    df = pd.DataFrame(items)
    print(f"  인구통계 원본: {len(df)}건")

    # adm_cd에서 읍면동 코드 추출 (앞 8자리)
    df["dong_cd"] = df["adm_cd"].astype(str).str[:8]

    # 읍면동별 집계
    agg = df.groupby("dong_cd").agg(
        총인구=("tot_ppltn", lambda x: pd.to_numeric(x, errors="coerce").sum()),
        총가구=("tot_family", lambda x: pd.to_numeric(x, errors="coerce").sum()),
        총주택=("tot_house", lambda x: pd.to_numeric(x, errors="coerce").sum()),
        평균연령=("avg_age", lambda x: pd.to_numeric(x, errors="coerce").mean()),
        인구밀도=("ppltn_dnsty", lambda x: pd.to_numeric(x, errors="coerce").mean()),
        평균가구원수=("avg_fmember_cnt", lambda x: pd.to_numeric(x, errors="coerce").mean()),
        사업체수=("corp_cnt", lambda x: pd.to_numeric(x, errors="coerce").sum()),
        종사자수=("employee_cnt", lambda x: pd.to_numeric(x, errors="coerce").sum()),
    ).reset_index()

    # 읍면동명 매핑
    agg["읍면동명"] = agg["dong_cd"].map(DONG_CODE_MAP)

    # 구 분류
    agg["구"] = agg["dong_cd"].apply(
        lambda x: "동남구" if x.startswith("34011") else "서북구"
    )

    return agg


def aggregate_household() -> pd.DataFrame:
    """가구통계를 읍면동 단위로 집계."""
    items = load_sgis_json("household")
    if not items:
        return pd.DataFrame()

    df = pd.DataFrame(items)
    print(f"  가구통계 원본: {len(df)}건")

    df["dong_cd"] = df["adm_cd"].astype(str).str[:8]

    agg = df.groupby("dong_cd").agg(
        가구수=("household_cnt", lambda x: pd.to_numeric(x, errors="coerce").sum()),
        가구원수합=("family_member_cnt", lambda x: pd.to_numeric(x, errors="coerce").sum()),
    ).reset_index()

    # 1인세대 비율 추정 (가구원수합/가구수가 1에 가까울수록 1인가구 많음)
    agg["평균가구원수_hh"] = agg["가구원수합"] / agg["가구수"].replace(0, float("nan"))

    return agg


def aggregate_house() -> pd.DataFrame:
    """주택통계를 읍면동 단위로 집계."""
    items = load_sgis_json("house")
    if not items:
        return pd.DataFrame()

    df = pd.DataFrame(items)
    print(f"  주택통계 원본: {len(df)}건")

    df["dong_cd"] = df["adm_cd"].astype(str).str[:8]

    agg = df.groupby("dong_cd").agg(
        주택수=("house_cnt", lambda x: pd.to_numeric(x, errors="coerce").sum()),
    ).reset_index()

    return agg


def main():
    print("=" * 60)
    print("SGIS 통계 데이터 ETL — 읍면동별 집계")
    print("=" * 60)

    # 인구
    df_pop = aggregate_population()
    # 가구
    df_hh = aggregate_household()
    # 주택
    df_house = aggregate_house()

    if df_pop.empty:
        print("인구통계 데이터가 없습니다.")
        return

    # 병합
    result = df_pop.copy()
    if not df_hh.empty:
        result = result.merge(df_hh[["dong_cd", "가구수", "평균가구원수_hh"]], on="dong_cd", how="left")
    if not df_house.empty:
        result = result.merge(df_house[["dong_cd", "주택수"]], on="dong_cd", how="left")

    # 파생 지표
    result["인구대비_주택비율"] = result["총주택"] / result["총인구"].replace(0, float("nan"))
    result["가구대비_주택비율"] = result["총주택"] / result["총가구"].replace(0, float("nan"))

    # 정렬
    result = result.sort_values("총인구", ascending=False)

    print(f"\n=== 천안시 읍면동별 통계 (총 {len(result)}개 행정동) ===")
    print(f"총인구: {result['총인구'].sum():,.0f}명")
    print(f"총가구: {result['총가구'].sum():,.0f}세대")

    print(f"\n[인구 상위 15개 동]")
    for _, row in result.head(15).iterrows():
        dong = row.get("읍면동명", row["dong_cd"])
        print(f"  {dong} ({row['구']}): 인구 {row['총인구']:,.0f} / 평균연령 {row['평균연령']:.1f}세 / 인구밀도 {row['인구밀도']:.0f}")

    print(f"\n[평균연령 낮은 동 (청년 밀집 추정) 상위 10]")
    young = result.nsmallest(10, "평균연령")
    for _, row in young.iterrows():
        dong = row.get("읍면동명", row["dong_cd"])
        print(f"  {dong}: 평균연령 {row['평균연령']:.1f}세 / 인구 {row['총인구']:,.0f}")

    print(f"\n[평균가구원수 낮은 동 (1인세대 밀집 추정) 상위 10]")
    single = result.nsmallest(10, "평균가구원수")
    for _, row in single.iterrows():
        dong = row.get("읍면동명", row["dong_cd"])
        print(f"  {dong}: 평균가구원 {row['평균가구원수']:.2f}명 / 인구 {row['총인구']:,.0f}")

    # 저장
    out_path = PROCESSED_DIR / "sgis_dong_stats.parquet"
    result.to_parquet(out_path, index=False)
    print(f"\n저장: {out_path}")
    print("✅ SGIS ETL 완료")


if __name__ == "__main__":
    main()
