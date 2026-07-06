#!/usr/bin/env python3
"""
실거래가 XML 파싱 → DataFrame 변환 + 전세가율 산출

수집된 XML 파일들을 파싱하여:
1. 아파트 매매 / 전월세 / 오피스텔 / 연립다세대 / 단독다가구 전체 통합
2. 전세가율(보증금 ÷ 매매가) 산출
3. data/processed/realestate_*.parquet 으로 저장
"""

import sys
from pathlib import Path

import pandas as pd
import xmltodict

# 프로젝트 루트 설정
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "collector"))

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "realestate"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# ── 유형별 파서 ──────────────────────────────────────────────

TRADE_TYPES = ["apt_trade", "offi_trade", "rh_trade", "sh_trade"]
RENT_TYPES = ["apt_rent", "offi_rent", "rh_rent", "sh_rent"]


def parse_xml_files(type_name: str) -> pd.DataFrame:
    """특정 유형의 XML 파일들을 파싱하여 DataFrame으로 반환."""
    type_dir = RAW_DIR / type_name
    if not type_dir.exists():
        print(f"  {type_name}: 디렉토리 없음")
        return pd.DataFrame()

    xml_files = sorted(type_dir.glob("*.xml"))
    if not xml_files:
        print(f"  {type_name}: 파일 없음")
        return pd.DataFrame()

    all_items = []
    errors = 0

    for xml_path in xml_files:
        try:
            content = xml_path.read_text(encoding="utf-8")
            parsed = xmltodict.parse(content)

            body = parsed.get("response", {}).get("body", {})
            items = body.get("items", {})

            if items is None or items == "":
                continue

            item_list = items.get("item", [])
            if isinstance(item_list, dict):
                item_list = [item_list]

            # 파일명에서 lawd_cd 추출
            fname = xml_path.stem  # e.g., "44131_202401"
            parts = fname.split("_")
            lawd_cd = parts[0] if len(parts) >= 2 else ""

            for item in item_list:
                item["_lawd_cd"] = lawd_cd
                item["_type"] = type_name
                item["_source_file"] = xml_path.name
                all_items.append(item)
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"  파싱 오류: {xml_path.name} — {e}")

    print(f"  {type_name}: {len(xml_files)}파일 → {len(all_items)}건 (에러 {errors})")
    return pd.DataFrame(all_items)


def clean_trade(df: pd.DataFrame) -> pd.DataFrame:
    """매매 데이터 정제."""
    if df.empty:
        return df

    # 숫자 컬럼 변환 (쉼표 제거)
    for col in ["dealAmount", "거래금액"]:
        if col in df.columns:
            df["거래금액_만원"] = (
                df[col]
                .astype(str)
                .str.replace(",", "")
                .str.strip()
                .apply(pd.to_numeric, errors="coerce")
            )
            break

    # 날짜
    for ycol, mcol, dcol in [
        ("dealYear", "dealMonth", "dealDay"),
        ("년", "월", "일"),
    ]:
        if ycol in df.columns:
            df["거래일"] = pd.to_datetime(
                df[ycol].astype(str).str.strip()
                + "-"
                + df[mcol].astype(str).str.strip().str.zfill(2)
                + "-"
                + df[dcol].astype(str).str.strip().str.zfill(2),
                errors="coerce",
            )
            break

    # 면적
    for col in ["excluUseAr", "전용면적", "totalFloorAr"]:
        if col in df.columns:
            df["전용면적_㎡"] = pd.to_numeric(
                df[col].astype(str).str.strip(), errors="coerce"
            )
            break

    # 건축년도
    for col in ["buildYear", "건축년도"]:
        if col in df.columns:
            df["건축년도"] = pd.to_numeric(
                df[col].astype(str).str.strip(), errors="coerce"
            )
            break

    # 동명
    for col in ["umdNm", "법정동"]:
        if col in df.columns:
            df["법정동명"] = df[col].astype(str).str.strip()
            break

    # 아파트/단지명
    for col in ["aptNm", "아파트", "aptDong"]:
        if col in df.columns:
            df["단지명"] = df[col].astype(str).str.strip()
            break

    # 층
    for col in ["floor", "층"]:
        if col in df.columns:
            df["층"] = pd.to_numeric(
                df[col].astype(str).str.strip(), errors="coerce"
            )
            break

    df["거래유형"] = "매매"
    return df


def clean_rent(df: pd.DataFrame) -> pd.DataFrame:
    """전월세 데이터 정제."""
    if df.empty:
        return df

    # 보증금
    for col in ["deposit", "보증금액"]:
        if col in df.columns:
            df["보증금_만원"] = (
                df[col]
                .astype(str)
                .str.replace(",", "")
                .str.strip()
                .apply(pd.to_numeric, errors="coerce")
            )
            break

    # 월세
    for col in ["monthlyRent", "월세금액"]:
        if col in df.columns:
            df["월세_만원"] = (
                df[col]
                .astype(str)
                .str.replace(",", "")
                .str.strip()
                .apply(pd.to_numeric, errors="coerce")
            )
            break

    # 전세 여부
    if "월세_만원" in df.columns:
        df["전세여부"] = df["월세_만원"].fillna(0) == 0

    # 날짜
    for ycol, mcol, dcol in [
        ("dealYear", "dealMonth", "dealDay"),
        ("년", "월", "일"),
    ]:
        if ycol in df.columns:
            df["거래일"] = pd.to_datetime(
                df[ycol].astype(str).str.strip()
                + "-"
                + df[mcol].astype(str).str.strip().str.zfill(2)
                + "-"
                + df[dcol].astype(str).str.strip().str.zfill(2),
                errors="coerce",
            )
            break

    # 면적
    for col in ["excluUseAr", "전용면적", "totalFloorAr"]:
        if col in df.columns:
            df["전용면적_㎡"] = pd.to_numeric(
                df[col].astype(str).str.strip(), errors="coerce"
            )
            break

    # 건축년도
    for col in ["buildYear", "건축년도"]:
        if col in df.columns:
            df["건축년도"] = pd.to_numeric(
                df[col].astype(str).str.strip(), errors="coerce"
            )
            break

    # 동명
    for col in ["umdNm", "법정동"]:
        if col in df.columns:
            df["법정동명"] = df[col].astype(str).str.strip()
            break

    # 주택유형
    for col in ["houseType"]:
        if col in df.columns:
            df["주택유형"] = df[col].astype(str).str.strip()
            break

    # 단지명
    for col in ["aptNm", "아파트", "aptDong"]:
        if col in df.columns:
            df["단지명"] = df[col].astype(str).str.strip()
            break

    df["거래유형"] = "전월세"
    return df


def main():
    print("=" * 60)
    print("실거래가 XML → DataFrame 변환")
    print("=" * 60)

    # 1. 매매 데이터 파싱
    print("\n[1/2] 매매 데이터 파싱...")
    trade_dfs = []
    for t in TRADE_TYPES:
        df = parse_xml_files(t)
        if not df.empty:
            trade_dfs.append(clean_trade(df))

    if trade_dfs:
        df_trade = pd.concat(trade_dfs, ignore_index=True)
        print(f"\n매매 통합: {len(df_trade):,}건")
        print(f"  기간: {df_trade['거래일'].min()} ~ {df_trade['거래일'].max()}")
        print(f"  금액 범위: {df_trade['거래금액_만원'].min():,.0f} ~ {df_trade['거래금액_만원'].max():,.0f} 만원")
        out_path = PROCESSED_DIR / "realestate_trade.parquet"
        df_trade.to_parquet(out_path, index=False)
        print(f"  저장: {out_path}")
    else:
        df_trade = pd.DataFrame()
        print("매매 데이터 없음")

    # 2. 전월세 데이터 파싱
    print("\n[2/2] 전월세 데이터 파싱...")
    rent_dfs = []
    for t in RENT_TYPES:
        df = parse_xml_files(t)
        if not df.empty:
            rent_dfs.append(clean_rent(df))

    if rent_dfs:
        df_rent = pd.concat(rent_dfs, ignore_index=True)
        print(f"\n전월세 통합: {len(df_rent):,}건")
        print(f"  기간: {df_rent['거래일'].min()} ~ {df_rent['거래일'].max()}")

        jeonse = df_rent[df_rent["전세여부"] == True]
        wolse = df_rent[df_rent["전세여부"] == False]
        print(f"  전세: {len(jeonse):,}건 / 월세: {len(wolse):,}건")
        print(f"  전세 보증금 범위: {jeonse['보증금_만원'].min():,.0f} ~ {jeonse['보증금_만원'].max():,.0f} 만원")

        out_path = PROCESSED_DIR / "realestate_rent.parquet"
        df_rent.to_parquet(out_path, index=False)
        print(f"  저장: {out_path}")
    else:
        df_rent = pd.DataFrame()
        print("전월세 데이터 없음")

    # 3. 전세가율 산출 (아파트 기준)
    if not df_trade.empty and not df_rent.empty:
        print("\n" + "=" * 60)
        print("전세가율 산출 (아파트 매매 × 전세 매칭)")
        print("=" * 60)

        # 아파트 매매만
        apt_trade = df_trade[df_trade["_type"] == "apt_trade"].copy()
        apt_jeonse = df_rent[
            (df_rent["_type"] == "apt_rent") & (df_rent["전세여부"] == True)
        ].copy()

        if not apt_trade.empty and not apt_jeonse.empty:
            # 연월 기준 매칭 (같은 단지, 비슷한 면적, 같은 연월)
            apt_trade["연월"] = apt_trade["거래일"].dt.to_period("M")
            apt_jeonse["연월"] = apt_jeonse["거래일"].dt.to_period("M")

            # 동·단지명·면적 기준으로 동일연월 매칭
            trade_avg = (
                apt_trade.groupby(["법정동명", "단지명", "연월"])["거래금액_만원"]
                .median()
                .reset_index()
                .rename(columns={"거래금액_만원": "매매가_중앙값"})
            )

            jeonse_avg = (
                apt_jeonse.groupby(["법정동명", "단지명", "연월"])["보증금_만원"]
                .median()
                .reset_index()
                .rename(columns={"보증금_만원": "전세금_중앙값"})
            )

            merged = pd.merge(
                jeonse_avg,
                trade_avg,
                on=["법정동명", "단지명", "연월"],
                how="inner",
            )
            merged["전세가율"] = merged["전세금_중앙값"] / merged["매매가_중앙값"]

            print(f"  매칭 성공: {len(merged):,}건")
            print(f"  전세가율 통계:")
            print(f"    평균: {merged['전세가율'].mean():.1%}")
            print(f"    중앙값: {merged['전세가율'].median():.1%}")
            print(f"    80% 이상 (위험): {(merged['전세가율'] >= 0.8).sum():,}건 ({(merged['전세가율'] >= 0.8).mean():.1%})")
            print(f"    90% 이상 (매우위험): {(merged['전세가율'] >= 0.9).sum():,}건 ({(merged['전세가율'] >= 0.9).mean():.1%})")
            print(f"    100% 이상 (깡통): {(merged['전세가율'] >= 1.0).sum():,}건 ({(merged['전세가율'] >= 1.0).mean():.1%})")

            # 동별 전세가율
            print(f"\n  동별 전세가율 (최근 3년):")
            recent = merged[merged["연월"] >= "2022-01"]
            dong_rate = recent.groupby("법정동명")["전세가율"].agg(["mean", "median", "count"])
            dong_rate = dong_rate.sort_values("mean", ascending=False)
            for dong, row in dong_rate.iterrows():
                flag = " ⚠️" if row["mean"] >= 0.75 else ""
                print(f"    {dong}: 평균 {row['mean']:.1%} / 중앙값 {row['median']:.1%} ({int(row['count'])}건){flag}")

            out_path = PROCESSED_DIR / "jeonse_rate.parquet"
            merged.to_parquet(out_path, index=False)
            print(f"\n  저장: {out_path}")

    # 4. 요약 통계
    print("\n" + "=" * 60)
    print("동별 거래 현황 (전체 기간)")
    print("=" * 60)

    if not df_rent.empty:
        dong_summary = df_rent.groupby("법정동명").agg(
            전월세건수=("보증금_만원", "count"),
            전세건수=("전세여부", "sum"),
            평균보증금=("보증금_만원", "mean"),
        )
        dong_summary = dong_summary.sort_values("전월세건수", ascending=False)
        print(dong_summary.head(20).to_string())

    print("\n✅ ETL 완료")


if __name__ == "__main__":
    main()
