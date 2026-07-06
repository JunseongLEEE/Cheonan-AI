#!/usr/bin/env python3
"""
건축물대장 XML 파싱 → DataFrame + 노후도 분석

핵심 피처:
- 건물연령 (2026 - 사용승인연도)
- 구조 (벽돌/철근콘크리트/철골)
- 용도 (단독/다가구/다세대/아파트/오피스텔)
- 층수 (지상/지하)
- 세대수
- 내진설계 여부
"""

import sys
from pathlib import Path

import pandas as pd
import xmltodict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "building"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

CURRENT_YEAR = 2026

# 핵심 컬럼만 추출
KEEP_COLS = [
    "platPlc", "newPlatPlc", "sigunguCd", "bjdongCd",
    "bldNm", "mainPurpsCdNm", "etcPurps",
    "strctCdNm", "etcStrct",
    "useAprDay", "grndFlrCnt", "ugrndFlrCnt",
    "hhldCnt", "fmlyCnt", "hoCnt",
    "totArea", "platArea", "archArea",
    "rserthqkDsgnApplyYn",
    "regstrKindCdNm",
]


def parse_building_files() -> pd.DataFrame:
    """건축물대장 XML 파일 전체 파싱."""
    all_items = []
    errors = 0

    for sigungu_dir in sorted(RAW_DIR.iterdir()):
        if not sigungu_dir.is_dir():
            continue
        sigungu_cd = sigungu_dir.name

        for bjdong_dir in sorted(sigungu_dir.iterdir()):
            if not bjdong_dir.is_dir():
                continue

            for xml_path in sorted(bjdong_dir.glob("*.xml")):
                try:
                    content = xml_path.read_text(encoding="utf-8")
                    parsed = xmltodict.parse(content)
                    body = parsed.get("response", {}).get("body", {})
                    items_data = body.get("items", {})

                    if not items_data:
                        continue

                    item_list = items_data.get("item", [])
                    if isinstance(item_list, dict):
                        item_list = [item_list]

                    for item in item_list:
                        all_items.append(item)
                except Exception as e:
                    errors += 1
                    if errors <= 5:
                        print(f"  파싱 오류: {xml_path} — {e}")

    print(f"건축물대장: {len(all_items):,}건 파싱 (에러 {errors})")
    return pd.DataFrame(all_items)


def clean_building(df: pd.DataFrame) -> pd.DataFrame:
    """건축물대장 정제 + 파생 피처 생성."""

    # 사용승인일 → 건물연령
    df["useAprDay"] = df["useAprDay"].astype(str).str.strip()
    df["사용승인연도"] = pd.to_numeric(
        df["useAprDay"].str[:4], errors="coerce"
    )
    df["건물연령"] = CURRENT_YEAR - df["사용승인연도"]
    # 비현실적 값 제거
    df.loc[df["건물연령"] < 0, "건물연령"] = None
    df.loc[df["건물연령"] > 200, "건물연령"] = None

    # 숫자 컬럼
    for col in ["grndFlrCnt", "ugrndFlrCnt", "hhldCnt", "fmlyCnt", "hoCnt",
                "totArea", "platArea", "archArea"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 내진설계
    df["내진설계"] = df["rserthqkDsgnApplyYn"].astype(str).str.strip() == "1"

    # 지하층 여부
    df["지하층있음"] = df["ugrndFlrCnt"].fillna(0) > 0

    # 용도 분류
    purps = df["mainPurpsCdNm"].astype(str).str.strip()
    df["용도_대분류"] = "기타"
    df.loc[purps.str.contains("단독", na=False), "용도_대분류"] = "단독주택"
    df.loc[purps.str.contains("다가구", na=False), "용도_대분류"] = "다가구주택"
    df.loc[purps.str.contains("다세대", na=False), "용도_대분류"] = "다세대주택"
    df.loc[purps.str.contains("연립", na=False), "용도_대분류"] = "연립주택"
    df.loc[purps.str.contains("아파트", na=False), "용도_대분류"] = "아파트"
    df.loc[purps.str.contains("오피스텔", na=False), "용도_대분류"] = "오피스텔"
    df.loc[purps.str.contains("근린생활", na=False), "용도_대분류"] = "근린생활"
    df.loc[purps.str.contains("공동주택", na=False) & (df["용도_대분류"] == "기타"), "용도_대분류"] = "공동주택(기타)"

    # 구조 분류
    strct = df["strctCdNm"].astype(str).str.strip()
    df["구조_대분류"] = "기타"
    df.loc[strct.str.contains("철근콘크리트", na=False), "구조_대분류"] = "철근콘크리트"
    df.loc[strct.str.contains("철골", na=False), "구조_대분류"] = "철골"
    df.loc[strct.str.contains("벽돌", na=False), "구조_대분류"] = "벽돌"
    df.loc[strct.str.contains("블록", na=False), "구조_대분류"] = "블록"
    df.loc[strct.str.contains("목", na=False), "구조_대분류"] = "목구조"

    # 노후도 등급
    df["노후도_등급"] = "양호"
    df.loc[df["건물연령"] >= 15, "노후도_등급"] = "보통"
    df.loc[df["건물연령"] >= 25, "노후도_등급"] = "노후"
    df.loc[df["건물연령"] >= 35, "노후도_등급"] = "심각"

    # 주소에서 법정동명 추출
    df["법정동명"] = (
        df["platPlc"]
        .astype(str)
        .str.extract(r"천안시\s+(?:동남구|서북구)\s+(\S+)")
    )

    return df


def main():
    print("=" * 60)
    print("건축물대장 XML → DataFrame 변환")
    print("=" * 60)

    df = parse_building_files()
    if df.empty:
        print("데이터 없음")
        return

    df = clean_building(df)

    # 주거용 건물만 필터
    residential = ["단독주택", "다가구주택", "다세대주택", "연립주택", "아파트", "오피스텔", "공동주택(기타)"]
    df_res = df[df["용도_대분류"].isin(residential)].copy()

    print(f"\n전체 건축물: {len(df):,}건")
    print(f"주거용 건축물: {len(df_res):,}건")

    # 용도별 통계
    print(f"\n[용도별 분포]")
    print(df_res["용도_대분류"].value_counts().to_string())

    # 구조별 통계
    print(f"\n[구조별 분포]")
    print(df_res["구조_대분류"].value_counts().to_string())

    # 노후도 통계
    print(f"\n[노후도 등급 분포]")
    print(df_res["노후도_등급"].value_counts().to_string())

    print(f"\n[건물연령 통계]")
    print(f"  평균: {df_res['건물연령'].mean():.1f}년")
    print(f"  중앙값: {df_res['건물연령'].median():.1f}년")
    print(f"  25년 이상 (노후): {(df_res['건물연령'] >= 25).sum():,}건 ({(df_res['건물연령'] >= 25).mean():.1%})")
    print(f"  35년 이상 (심각): {(df_res['건물연령'] >= 35).sum():,}건 ({(df_res['건물연령'] >= 35).mean():.1%})")

    # 내진설계
    print(f"\n[내진설계 적용]")
    print(f"  적용: {df_res['내진설계'].sum():,}건 ({df_res['내진설계'].mean():.1%})")
    print(f"  미적용: {(~df_res['내진설계']).sum():,}건")

    # 동별 노후도
    print(f"\n[동별 평균 건물연령 (노후도 높은 순, 상위 20)]")
    dong_age = df_res.groupby("법정동명").agg(
        건물수=("건물연령", "count"),
        평균연령=("건물연령", "mean"),
        노후비율=("건물연령", lambda x: (x >= 25).mean()),
    ).sort_values("평균연령", ascending=False)
    for dong, row in dong_age.head(20).iterrows():
        print(f"  {dong}: 평균 {row['평균연령']:.1f}년 / 노후 {row['노후비율']:.0%} ({int(row['건물수'])}동)")

    # 저장
    out_all = PROCESSED_DIR / "building_all.parquet"
    df.to_parquet(out_all, index=False)
    print(f"\n전체 저장: {out_all}")

    out_res = PROCESSED_DIR / "building_residential.parquet"
    df_res.to_parquet(out_res, index=False)
    print(f"주거용 저장: {out_res}")

    print("\n✅ 건축물대장 ETL 완료")


if __name__ == "__main__":
    main()
