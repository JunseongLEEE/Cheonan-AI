#!/usr/bin/env python3
"""
exp_007 — 천안 깡통전세 Tool-Calling 학습 데이터셋 생성기

원칙: 툴 출력은 전부 '실제 시스템 값'이다.
  - simulator  → scripts/simulator.predict (exp_004 LightGBM + SHAP) 실호출
  - dong_lookup → data/processed/dong_safety_score.parquet 실값
  - recommend  → scripts/recommender.recommend (exp_006 앙상블) 실호출
  - news_search → 실제 통계(288세대·145억 등) 기반 헤드라인 템플릿 (형식 학습용)

대화 유형 (intent):
  A. simulator      — 매물 위험 진단 (단일 툴)
  B. dong_lookup    — 동네 안전 조회
  C. news           — 최근 이슈/뉴스
  D. recommend      — 예산 기반 추천
  E. kb_qa          — 정책·개념 질문 (툴 없이 직접 답변)
  F. multi_tool     — 동네 조회 + 뉴스 (순차 2-툴)
  G. clarify        — 정보 부족 → 되묻기 (툴 호출 금지 학습)
  H. out_of_scope   — 범위 밖 질문 거절

출력: experiments/exp_007_cheonan_llm/data/{train,eval}.jsonl
  {"messages": [...], "intent": "..."}  (tools는 학습 시 공통 주입)
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.llm.tools_schema import CHEONAN_SYSTEM_PROMPT  # noqa: E402

DATA_DIR = PROJECT_ROOT / "experiments" / "exp_007_cheonan_llm" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED = PROJECT_ROOT / "data" / "processed"

SEED = 42
rng = random.Random(SEED)
np.random.seed(SEED)

# 생성 규모
N_SIM, N_DONG, N_NEWS, N_RECO, N_KB, N_MULTI, N_CLARIFY, N_OOS = (
    2200, 1300, 700, 700, 900, 450, 350, 250
)
EVAL_RATIO = 0.08

# ─────────────────────────────────────────────
# 유틸 — 금액·면적 한국어 표기 다양화
# ─────────────────────────────────────────────

def won_phrase(man: float) -> str:
    """만원 금액 → 자연스러운 한국어 표기 (여러 변형)."""
    man = int(round(man))
    eok, rem = divmod(man, 10000)
    styles = []
    if eok and rem:
        styles += [f"{eok}억 {rem}만원", f"{eok}억{rem}만"]
        if rem % 1000 == 0:
            styles += [f"{eok}억 {rem // 1000}천", f"{eok}억 {rem // 1000}천만원"]
    elif eok:
        styles += [f"{eok}억", f"{eok}억원"]
    else:
        styles += [f"{man}만원", f"{man}만"]
        if man % 1000 == 0 and man >= 1000:
            styles += [f"{man // 1000}천만원", f"{man // 1000}천만 원"]
    return rng.choice(styles)


def area_phrase(m2: float) -> str:
    m2 = round(float(m2), 1)
    if rng.random() < 0.35:
        pyeong = round(m2 / 3.3058)
        return f"{pyeong}평"
    return f"{m2:g}㎡" if rng.random() < 0.7 else f"{m2:g}제곱미터"


def round_floats(obj, nd=3):
    if isinstance(obj, dict):
        return {k: round_floats(v, nd) for k, v in obj.items()}
    if isinstance(obj, list):
        return [round_floats(v, nd) for v in obj]
    if isinstance(obj, float):
        return round(obj, nd)
    return obj


def tool_call_msg(name: str, args: dict) -> dict:
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [{
            "type": "function",
            "function": {"name": name, "arguments": args},
        }],
    }


def tool_result_msg(name: str, result) -> dict:
    return {
        "role": "tool",
        "name": name,
        "content": json.dumps(round_floats(result), ensure_ascii=False),
    }


def convo(intent: str, messages: list[dict]) -> dict:
    return {"intent": intent,
            "messages": [{"role": "system", "content": CHEONAN_SYSTEM_PROMPT}] + messages}


# ─────────────────────────────────────────────
# 실데이터 로드
# ─────────────────────────────────────────────

print("실데이터 로드 중...")
df_safety = pd.read_parquet(PROCESSED / "dong_safety_score.parquet")
df_trends = pd.read_parquet(PROCESSED / "dong_jeonse_trends.parquet")
df_rent = pd.read_parquet(PROCESSED / "realestate_rent.parquet")
df_jeonse = df_rent[df_rent["전세여부"] == True].copy()
df_jeonse = df_jeonse.dropna(subset=["법정동명", "보증금_만원", "전용면적_㎡", "건축년도"])
df_jeonse = df_jeonse[df_jeonse["건축년도"].between(1975, 2026)]
DONGS = df_safety["법정동명"].dropna().unique().tolist()
DONGNAM_KEYS = ["목천", "병천", "북면", "풍세", "성남", "수신", "동면", "광덕"]

from scripts.rag_chatbot import tool_dong_lookup  # noqa: E402
from scripts.simulator import predict as sim_predict  # noqa: E402
from scripts.recommender import recommend as reco_fn  # noqa: E402

AXES = ["금융안전", "건물노후", "침수위험", "치안", "소방", "교통", "편의시설", "환경"]
SIGNAL_ICON = {"빨강": "🔴", "노랑": "🟡", "초록": "🟢"}


def slim_sim_result(s: dict) -> dict:
    """simulator.predict 결과를 학습용으로 축약 (핵심 필드만)."""
    return {
        "risk_prob": s["risk_prob"],
        "signal": s["signal"],
        "signal_label": s["signal_label"],
        "safety_score": s.get("safety_score"),
        "shap_top5": [
            {"feature": x["feature"], "shap_value": round(float(x["shap_value"]), 3)}
            for x in s["shap_top5"][:5]
        ],
        "input": s["input"],
    }


# ─────────────────────────────────────────────
# A. simulator — 매물 위험 진단
# ─────────────────────────────────────────────

SIM_TEMPLATES = [
    "{dong}에 보증금 {won}짜리 {area} 전세 매물이 있는데 깡통전세일까?",
    "{dong} {won} 전세 계약하려고 하는데 위험한지 봐줘. 면적은 {area}, {year}년식이야.",
    "{year}년에 지어진 {dong} 빌라, 전세 {won}인데 괜찮을까요? {area}쯤 돼요.",
    "보증금 {won}, {dong}, {area}, {year}년 준공. 위험도 진단해줘.",
    "천안 {dong}에서 {won}에 전세 들어가려는데 안전한지 확인 부탁해",
    "{dong} 원룸 전세 {won}이면 위험해? 건물은 {year}년에 지어졌대.",
    "지금 {dong} {area} 매물 보고 있는데 보증금이 {won}이야. 깡통 위험 있어?",
    "부모님이 {dong} 전세 {won} 계약하라는데 AI 진단 좀… {year}년식 {area}",
    "{dong}동네에 {won} 전세면 전세가율 괜찮은 편이야? 면적 {area}야.",
    "계약 직전인데 불안해서. {dong}, 보증금 {won}, {area}, {year}년 건물이야.",
]

SIM_ANSWER_OPENERS = {
    "빨강": ["⚠️ 이 매물은 **위험** 등급입니다.", "결론부터 말하면 계약을 재고하셔야 합니다.",
             "🔴 위험 신호가 강하게 잡힙니다."],
    "노랑": ["🟡 **주의** 등급이 나왔습니다.", "안전하다고 단정하기 어려운 매물입니다.",
             "주의가 필요한 수준입니다."],
    "초록": ["🟢 비교적 **안전**한 매물로 진단됩니다.", "다행히 위험 신호는 낮은 편입니다.",
             "AI 진단 결과 안전 등급입니다."],
}

FEATURE_KO = {
    "보증금_만원": "보증금 수준", "보증금_log": "보증금 수준", "㎡당_보증금": "㎡당 보증금",
    "전용면적": "전용면적", "건물연령": "건물 연식", "동남구": "구도심(동남구) 여부",
    "동_평균보증금": "동네 평균 보증금", "동_거래건수": "동네 거래량",
    "보증금_동평균_비율": "동네 평균 대비 보증금", "보증금_구평균_비율": "구 평균 대비 보증금",
    "면적_구평균_비율": "구 평균 대비 면적", "연도별_동_위험도": "동네 과거 위험 이력",
    "거래연도": "거래 연도", "동_평균건물연령": "동네 평균 건물연령",
    "동_건물연령_std": "동네 건물연령 편차", "동_노후비율": "동네 노후건물 비율",
    "동_심각노후비율": "동네 심각노후 비율", "동_내진비율": "동네 내진설계 비율",
    "동_건물수": "동네 건물 수", "동_평균세대수": "동네 평균 세대수",
    "동_평균총면적": "동네 평균 연면적", "동_평균지상층": "동네 평균 층수",
    "동_철근콘크리트비율": "철근콘크리트 비율", "동_벽돌비율": "벽돌구조 비율",
    "동_목구조비율": "목구조 비율", "건물연령_동평균차": "동네 평균 대비 연식",
    "보증금_노후도_교차": "보증금×노후도 결합",
}


def compose_sim_answer(s: dict) -> str:
    sig = s["signal"]
    opener = rng.choice(SIM_ANSWER_OPENERS[sig])
    inp = s["input"]
    lines = [
        opener,
        f"{inp['법정동명']} 보증금 {inp['보증금_만원']:,.0f}만원 · {inp['전용면적']:g}㎡ · "
        f"{inp['건축년도']}년식 기준, AI 위험확률은 **{s['risk_prob']:.1%}** "
        f"({SIGNAL_ICON[sig]} {s['signal_label']})입니다.",
    ]
    if s.get("safety_score") is not None:
        lines.append(f"{inp['법정동명']}의 동네 종합 안전점수는 {s['safety_score']:.1f}/100점입니다.")
    ups = [x for x in s["shap_top5"] if x["shap_value"] > 0][:2]
    downs = [x for x in s["shap_top5"] if x["shap_value"] < 0][:1]
    if ups:
        lines.append("위험을 높인 요인: " + ", ".join(
            f"{FEATURE_KO.get(x['feature'], x['feature'])}(+{x['shap_value']:.2f})" for x in ups) + ".")
    if downs:
        x = downs[0]
        lines.append(f"반대로 {FEATURE_KO.get(x['feature'], x['feature'])}({x['shap_value']:.2f})는 위험을 낮췄습니다.")
    advice = {
        "빨강": "계약 전 등기부등본으로 선순위 근저당을 반드시 확인하고, HUG 반환보증 가입이 가능한지 먼저 알아보세요. 가능하면 보증금 조정 협상이나 다른 매물 검토를 권합니다.",
        "노랑": "계약하신다면 HUG 전세보증금 반환보증 가입과 전입신고+확정일자를 필수로 챙기시고, 등기부등본에서 근저당을 확인하세요.",
        "초록": "그래도 등기부등본 확인과 전입신고+확정일자는 기본으로 챙기세요.",
    }[sig]
    lines.append(advice)
    return "\n".join(lines)


def gen_simulator(n: int) -> list[dict]:
    out = []
    sample = df_jeonse.sample(n=min(n * 2, len(df_jeonse)), random_state=SEED)
    rows = [r for _, r in sample.iterrows() if r["법정동명"] in set(DONGS)][:n]
    print(f"  simulator 예측 {len(rows)}건 실행 중...")
    for i, r in enumerate(rows):
        dong = r["법정동명"]
        gu = "동남구" if any(k in dong for k in DONGNAM_KEYS) or rng.random() < 0.4 else "서북구"
        try:
            s = sim_predict(
                보증금_만원=float(r["보증금_만원"]), 전용면적=float(r["전용면적_㎡"]),
                법정동명=dong, 건축년도=int(r["건축년도"]), 구=gu,
            )
        except Exception:
            continue
        s = slim_sim_result(s)
        tmpl = rng.choice(SIM_TEMPLATES)
        user = tmpl.format(
            dong=dong, won=won_phrase(r["보증금_만원"]),
            area=area_phrase(r["전용면적_㎡"]), year=int(r["건축년도"]),
        )
        args = {
            "보증금_만원": float(round(r["보증금_만원"])),
            "전용면적": round(float(r["전용면적_㎡"]), 1),
            "법정동명": dong,
            "건축년도": int(r["건축년도"]),
        }
        # 템플릿에 면적/년도가 없는 경우 args에서도 생략 → 기본값 학습
        if "{area}" not in tmpl:
            args.pop("전용면적", None)
        if "{year}" not in tmpl:
            args.pop("건축년도", None)
        out.append(convo("simulator", [
            {"role": "user", "content": user},
            tool_call_msg("simulator", args),
            tool_result_msg("simulator", s),
            {"role": "assistant", "content": compose_sim_answer(s)},
        ]))
        if (i + 1) % 500 == 0:
            print(f"    {i + 1}/{len(rows)}")
    return out


# ─────────────────────────────────────────────
# B. dong_lookup — 동네 안전 조회
# ─────────────────────────────────────────────

DONG_TEMPLATES = [
    "{dong} 살기 안전한 동네야?",
    "{dong} 안전점수 알려줘",
    "천안 {dong} 어때? 자취하기 괜찮아?",
    "{dong} 전세가율이랑 안전등급 궁금해",
    "{dong}으로 이사 가려는데 치안이나 침수 위험은 어때?",
    "{dong} 동네 진단 좀 해줘",
    "{dong}이 다른 동네보다 위험한 편이야?",
    "{dong} 8축 안전점수 보여줘",
    "자취방 알아보는 중인데 {dong} 어떤지 평가해줘",
    "{dong} 최근 전세가율 추세도 같이 알려줘",
]


def compose_dong_answer(d: dict) -> str:
    icon = SIGNAL_ICON.get(d["신호등"], "⚪")
    lines = [
        f"**{d['dong']}** 종합 안전점수는 **{d['종합안전점수']:.1f}/100** ({icon} {d['신호등']})입니다.",
    ]
    if d.get("전세가율_평균") is not None:
        rate = d["전세가율_평균"]
        judge = "안전권" if rate < 0.6 else ("주의권" if rate < 0.8 else "위험권")
        lines.append(f"평균 전세가율은 {rate:.0%}로 {judge}입니다.")
    lines.append(f"강점은 {d['최강축']}({d['축별점수'][d['최강축']]:.2f}), "
                 f"약점은 {d['최약축']}({d['축별점수'][d['최약축']]:.2f})입니다.")
    if d.get("추세"):
        t = d["추세"]
        lines.append(f"최근 전세가율 {t['최근_전세가율']:.0%}, 6개월 추세 {t['6개월_추세']:+.1%} "
                     f"({t['추세_판정']})입니다.")
    grade_advice = {
        "빨강": "위험 등급 동네이므로 개별 매물 진단(위험도 시뮬레이터)을 꼭 거치세요.",
        "노랑": "동네 평균은 주의 수준이니, 계약 전 개별 매물 위험 진단을 권합니다.",
        "초록": "다만 안전한 동네에도 위험 매물은 있으니 개별 진단은 챙기세요.",
    }.get(d["신호등"], "")
    if grade_advice:
        lines.append(grade_advice)
    return "\n".join(lines)


def gen_dong(n: int) -> list[dict]:
    out = []
    for i in range(n):
        dong = rng.choice(DONGS)
        d = tool_dong_lookup(dong, df_safety, df_trends if rng.random() < 0.6 else None)
        if d is None:
            continue
        user = rng.choice(DONG_TEMPLATES).format(dong=dong)
        out.append(convo("dong_lookup", [
            {"role": "user", "content": user},
            tool_call_msg("dong_lookup", {"법정동명": dong}),
            tool_result_msg("dong_lookup", d),
            {"role": "assistant", "content": compose_dong_answer(d)},
        ]))
    return out


# ─────────────────────────────────────────────
# C. news_search — 뉴스/최근 이슈
# ─────────────────────────────────────────────

NEWS_TEMPLATES = [
    "요즘 천안 전세사기 뉴스 있어?",
    "최근 천안 부동산 이슈 알려줘",
    "천안에서 전세 관련해서 무슨 일 있었어?",
    "{dong} 쪽 최근 전세사기 사례 있었는지 궁금해",
    "요새 깡통전세 관련 기사 좀 찾아줘",
    "천안 전세시장 최근 동향 뉴스로 알려줘",
    "전세사기 최근 발생 사례 알려줘",
    "{dong} 근처 부동산 뉴스 검색해줘",
]

# 실제 통계·제도 기반 헤드라인 풀 (툴 출력 '형식' 학습용)
NEWS_POOL = [
    {"title": "천안 전세사기 피해 누적 288세대·145억원… 동남구 구도심 집중",
     "source": "충청투데이", "days_ago": 6},
    {"title": "천안시, 전세피해 청년에 최대 12개월 월세 지원 확대", "source": "연합뉴스", "days_ago": 12},
    {"title": "충남 깡통전세 경보… 신축 빌라 전세가율 90% 넘는 단지 속출", "source": "중도일보", "days_ago": 3},
    {"title": "HUG 반환보증 가입 문턱 '공시가 126%' 유지… 세입자 주의", "source": "한국경제", "days_ago": 20},
    {"title": "천안 두정동 일대 다세대 전세사기 의혹 수사 착수", "source": "대전MBC", "days_ago": 9},
    {"title": "국토부, 전세사기 특별단속 연장… 충남 서북부 집중 점검", "source": "뉴시스", "days_ago": 15},
    {"title": "'전세보증금 못 돌려받아'… 천안 20대 피해 상담 증가", "source": "KBS대전", "days_ago": 5},
    {"title": "천안시 안심전세 상담센터 운영… 계약 전 무료 진단", "source": "천안신문", "days_ago": 27},
    {"title": "전세가율 80% 넘으면 위험… 전문가가 말하는 계약 체크리스트", "source": "머니투데이", "days_ago": 18},
    {"title": "충남도, 청년 전세보증료 지원 사업 하반기 접수 시작", "source": "충남일보", "days_ago": 8},
]


def gen_news(n: int) -> list[dict]:
    out = []
    for i in range(n):
        dong = rng.choice(DONGS)
        tmpl = rng.choice(NEWS_TEMPLATES)
        user = tmpl.format(dong=dong)
        query = f"천안 {dong} 전세사기" if "{dong}" in tmpl else "천안 전세사기"
        items = rng.sample(NEWS_POOL, k=rng.choice([3, 4]))
        news = [{"title": it["title"], "source": it["source"],
                 "pubDate": f"{it['days_ago']}일 전"} for it in items]
        cites = []
        for j, it in enumerate(news[:3], 1):
            cites.append(f"- {it['title']} ({it['source']}) [{j}]")
        answer = (
            f"최근 관련 뉴스를 검색한 결과입니다.\n" + "\n".join(cites) +
            "\n\n요약하면, 천안·충남권에서 전세가율이 높은 신축 다세대 중심으로 깡통전세 경보가 이어지고 있고, "
            "시·정부 차원의 피해 지원과 단속이 진행 중입니다 [1][2]. "
            "계약 전에는 반드시 등기부등본과 전세가율을 확인하고, HUG 반환보증 가입 가능 여부를 점검하세요."
        )
        out.append(convo("news", [
            {"role": "user", "content": user},
            tool_call_msg("news_search", {"query": query}),
            tool_result_msg("news_search", {"items": news}),
            {"role": "assistant", "content": answer},
        ]))
    return out


# ─────────────────────────────────────────────
# D. recommend — 예산 기반 추천
# ─────────────────────────────────────────────

RECO_TEMPLATES = [
    "예산 {won}인데 천안에서 안전한 동네 추천해줘",
    "보증금 {won}으로 갈 만한 안전한 자취방 동네 어디야?",
    "{won} 예산으로 {priority} 좋은 동네 추천 부탁해",
    "천안에서 {won}짜리 전세 구하는데 어디가 제일 안전해?",
    "{gu}에서 예산 {won}으로 안전한 곳 추천해줘",
    "{won} 정도로 {area_min}~{area_max}㎡ 전세 안전한 데 알려줘",
]


def compose_reco_answer(res: dict, priority: str | None) -> str:
    if not res["dongs"]:
        return res.get("message", "조건에 맞는 동네를 찾지 못했습니다. 예산 범위를 조금 넓혀보세요.")
    lines = [f"조건에 맞는 최근 실거래 {res['n_candidates']:,}건을 분석해 안전 순으로 추천합니다."]
    for i, d in enumerate(res["dongs"][:3], 1):
        icon = SIGNAL_ICON.get(d["신호등"], "⚪")
        lines.append(
            f"{i}. **{d['법정동명']}** {icon} — 추천점수 {d['추천점수']:.0f}, "
            f"안전점수 {d['종합안전점수']:.0f}/100, 평균 위험확률 {d['평균_위험확률']:.0%}, "
            f"중위 보증금 {d['중위_보증금_만원']:,}만원 (거래 {d['거래수']}건)"
        )
    top = res["dongs"][0]
    if top["대표매물"]:
        m = top["대표매물"][0]
        lines.append(
            f"예컨대 {top['법정동명']} '{m['단지명']}'은 보증금 {m['보증금_만원']:,.0f}만원·"
            f"{m['전용면적_㎡']:.0f}㎡에 위험확률 {m['위험확률']:.0%}로 낮은 편입니다."
        )
    if priority:
        lines.append(f"{priority} 축을 우선 반영한 결과입니다.")
    lines.append("실제 계약 전에는 해당 매물로 개별 위험 진단을 한 번 더 받아보세요.")
    return "\n".join(lines)


def gen_recommend(n: int) -> list[dict]:
    out = []
    budgets = [3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 12000, 15000, 18000, 20000]
    print(f"  recommend 실호출 {n}건 실행 중...")
    for i in range(n):
        budget = rng.choice(budgets)
        priority = rng.choice([None, None, "교통", "치안", "편의시설", "건물노후", "금융안전"])
        gu = rng.choice([None, None, None, "동남구", "서북구"])
        area_min, area_max = rng.choice([(0, 999), (0, 999), (15, 40), (20, 60), (30, 85)])
        tmpl = rng.choice(RECO_TEMPLATES)
        user = tmpl.format(
            won=won_phrase(budget), priority=priority or "치안", gu=gu or "서북구",
            area_min=area_min, area_max=area_max,
        )
        args: dict = {"budget": budget}
        if "{priority}" in tmpl:
            args["priority"] = priority or "치안"
        if "{gu}" in tmpl:
            args["gu"] = gu or "서북구"
        if "{area_min}" in tmpl:
            args["area_min"], args["area_max"] = area_min, area_max
        try:
            res = reco_fn(**args, top_k=5)
        except Exception:
            continue
        # 툴 출력 축약: 상위 3개 동 + 대표매물 1개씩
        slim = {
            "n_candidates": res["n_candidates"],
            "dongs": [
                {**{k: v for k, v in d.items() if k != "대표매물"},
                 "대표매물": d["대표매물"][:1]}
                for d in res["dongs"][:3]
            ],
        }
        out.append(convo("recommend", [
            {"role": "user", "content": user},
            tool_call_msg("recommend", args),
            tool_result_msg("recommend", slim),
            {"role": "assistant", "content": compose_reco_answer(res, args.get("priority"))},
        ]))
    return out


# ─────────────────────────────────────────────
# E. KB QA — 툴 없이 직접 답변 (rag_chatbot KB 재사용)
# ─────────────────────────────────────────────

KB_QA = [
    ("깡통전세가 뭐야?",
     "깡통전세는 전세보증금이 집의 매매가에 근접하거나 초과하는 상태를 말합니다. "
     "임대인이 파산하거나 집이 경매로 넘어가면 보증금을 온전히 돌려받기 어렵습니다. "
     "통상 전세가율 80% 이상이면 위험, 90% 이상이면 심각 위험으로 봅니다. "
     "천안에서는 3년간 288세대, 145억원의 전세사기 피해가 발생했고 동남구 구도심에 집중됐습니다. "
     "계약 전 등기부등본 확인과 HUG 반환보증 가입이 핵심 예방책입니다."),
    ("전세가율이 뭔데?",
     "전세가율은 전세보증금을 매매가로 나눈 비율(%)입니다. "
     "60% 이하는 안전, 60~80%는 주의, 80~90%는 위험, 90% 이상은 심각 위험으로 분류합니다. "
     "100%를 넘으면 보증금이 집값보다 큰 '깡통전세'입니다. "
     "천안시 평균 전세가율은 약 77%로 전국 평균보다 다소 높은 편이라 매물별 확인이 중요합니다."),
    ("HUG 전세보증보험이 뭐야? 가입 조건은?",
     "HUG(주택도시보증공사) 전세보증금 반환보증은 임대인이 보증금을 돌려주지 못할 때 "
     "HUG가 대신 지급하는 제도입니다. 조건은 보증금이 수도권 7억 이하(그 외 5억 이하), "
     "선순위 채권이 주택가격의 60% 이내 등이며, 공시가격 × 126%를 넘는 보증금은 가입이 어려울 수 있습니다. "
     "천안시 청년은 보증료 지원 대상이 될 수 있으니 HUG 홈페이지나 위탁은행에서 확인하세요."),
    ("전입신고랑 확정일자는 왜 해야 해?",
     "전입신고를 하면 '대항력'이 생겨 집주인이 바뀌어도 세입자 지위를 유지할 수 있고, "
     "확정일자를 받으면 '우선변제권'이 생겨 경매 시 후순위 채권자보다 먼저 배당받습니다. "
     "이사 당일 정부24나 주민센터에서 두 가지를 반드시 처리하세요. "
     "이 조치가 없으면 HUG 보증보험도 효력을 발휘하기 어렵습니다."),
    ("천안 청년 월세 지원 받을 수 있어?",
     "천안시는 무주택 청년(19~34세)에게 월 최대 20만원, 최대 12개월 월세를 지원합니다. "
     "조건은 가구 소득 중위 100% 이하, 본인 소득 중위 60% 이하, "
     "보증금 5천만원 이하·월세 60만원 이하 주택 거주 등입니다. "
     "복지로(bokjiro.go.kr) 또는 천안시청 주거복지과(041-521-5252)로 신청하세요."),
    ("계약 전에 뭘 확인해야 해?",
     "핵심 체크리스트입니다.\n"
     "1) 등기부등본에서 근저당·가압류·소유주 확인 (계약 당일 재발급)\n"
     "2) 임대인 본인 확인, 대리인이면 위임장+인감증명서\n"
     "3) 전세가율 80% 이하인지 확인, 초과 시 HUG 보험 필수\n"
     "4) 계약 후 즉시 전입신고 + 확정일자\n"
     "5) 특약에 근저당 말소 조건 명시\n"
     "저에게 매물 정보(동네·보증금·면적)를 주시면 AI 위험 진단도 해드립니다."),
    ("등기부등본은 어디서 어떻게 봐?",
     "인터넷 등기소(iros.go.kr)에서 700원에 열람할 수 있습니다. "
     "'갑구'에서 소유권 변동·가압류를, '을구'에서 근저당권·전세권을 확인하세요. "
     "핵심은 근저당 채권최고액과 내 보증금의 합이 매매가의 80%를 넘지 않는지입니다. "
     "계약 당일 재발급해 최신 상태를 확인하는 것이 안전합니다."),
    ("전세사기 위험 신호 같은 게 있어?",
     "대표적 위험 신호는 이렇습니다: 시세보다 지나치게 높은 보증금, 계약을 서두르는 임대인, "
     "등기부등본 열람 회피, 신축 다세대에서 유사 계약 반복, 대리인만 내세우는 임대인, "
     "선순위 근저당이 매매가의 60% 초과. "
     "이 중 3개 이상 해당하면 계약을 재고하고 천안시 안심계약 도움서비스를 신청하세요."),
    ("동남구랑 서북구 중 어디가 더 안전해?",
     "평균적으로는 서북구(불당·성성 등 신도심)가 인프라·건물 상태 면에서 안전점수가 높고, "
     "동남구 구도심은 건물 노후율·전세가율이 높아 평균 점수가 낮습니다. "
     "다만 서북구 두정·성성 일부도 신축 다세대 깡통전세 이슈가 있고, "
     "동남구에도 양호한 동네가 있어 '구' 단위 일반화보다 동·매물 단위 진단이 중요합니다. "
     "궁금한 동네 이름을 알려주시면 8축 안전점수를 조회해드릴게요."),
    ("안심계약 도움서비스가 뭐야?",
     "천안시의 안심계약 도움서비스는 전세 계약 시 공인중개사·법률 전문가가 동석해 "
     "등기부등본 확인, 계약서 검토, 특약 조언을 무료로 제공하는 제도입니다. "
     "전세사기 예방 목적이며, 계약 체결 최소 3영업일 전에 신청해야 합니다."),
    ("이 서비스는 뭘 할 수 있어?",
     "저는 천안 청년 자취방 안전지도의 AI 상담원입니다. 할 수 있는 일은:\n"
     "1) 매물 위험 진단 — 동네·보증금·면적·건축년도를 주시면 AI가 깡통전세 위험확률을 계산\n"
     "2) 동네 안전 조회 — 65개 법정동의 8축 안전점수와 전세가율 추세\n"
     "3) 안전 매물 추천 — 예산에 맞는 안전한 동네와 실거래 매물\n"
     "4) 최신 뉴스 검색과 전세 정책·제도 안내\n"
     "편하게 물어보세요!"),
    ("공시가격 126%가 무슨 말이야?",
     "HUG가 반환보증 가입 심사에서 쓰는 기준으로, 주택 공시가격 × 126%를 그 집의 가격으로 간주합니다. "
     "전세보증금이 이 금액을 넘으면 보증 가입이 어렵습니다. "
     "즉 보증금이 '공시가 × 1.26'보다 크면 깡통 위험 신호로 보셔야 합니다. "
     "본 서비스의 AI 진단도 이 규칙을 위험 판단에 반영합니다."),
]

KB_PARAPHRASE = [
    "{q}", "{q} 자세히 알려줘", "궁금한 게 있는데, {q}", "초보 질문인데 {q}", "{q} 간단히 설명해줘",
]


def gen_kb(n: int) -> list[dict]:
    out = []
    for i in range(n):
        q, a = KB_QA[i % len(KB_QA)]
        user = rng.choice(KB_PARAPHRASE).format(q=q)
        out.append(convo("kb_qa", [
            {"role": "user", "content": user},
            {"role": "assistant", "content": a},
        ]))
    return out


# ─────────────────────────────────────────────
# F. multi_tool — 동네 조회 + 뉴스 (순차)
# ─────────────────────────────────────────────

MULTI_TEMPLATES = [
    "{dong} 안전한지 알려주고, 최근 그 동네 이슈도 검색해줘",
    "{dong}으로 이사 갈까 하는데 안전점수랑 요즘 뉴스 둘 다 알려줘",
    "{dong} 진단해주고 최근 전세사기 사례 있었는지도 봐줘",
]


def gen_multi(n: int) -> list[dict]:
    out = []
    for i in range(n):
        dong = rng.choice(DONGS)
        d = tool_dong_lookup(dong, df_safety, df_trends)
        if d is None:
            continue
        items = rng.sample(NEWS_POOL, k=3)
        news = [{"title": it["title"], "source": it["source"],
                 "pubDate": f"{it['days_ago']}일 전"} for it in items]
        user = rng.choice(MULTI_TEMPLATES).format(dong=dong)
        icon = SIGNAL_ICON.get(d["신호등"], "⚪")
        answer = (
            f"**{dong}** 종합 안전점수는 {d['종합안전점수']:.1f}/100 ({icon} {d['신호등']})이고, "
            f"강점은 {d['최강축']}, 약점은 {d['최약축']}입니다.\n\n"
            f"최근 뉴스로는 '{news[0]['title']}' ({news[0]['source']}) [1], "
            f"'{news[1]['title']}' ({news[1]['source']}) [2] 등이 확인됩니다. "
            "천안·충남권 전반에 깡통전세 주의보가 이어지는 만큼, "
            "이 동네에서도 개별 매물 위험 진단을 꼭 거치시길 권합니다."
        )
        out.append(convo("multi_tool", [
            {"role": "user", "content": user},
            tool_call_msg("dong_lookup", {"법정동명": dong}),
            tool_result_msg("dong_lookup", d),
            tool_call_msg("news_search", {"query": f"천안 {dong} 전세사기"}),
            tool_result_msg("news_search", {"items": news}),
            {"role": "assistant", "content": answer},
        ]))
    return out


# ─────────────────────────────────────────────
# G. clarify — 정보 부족 → 되묻기
# ─────────────────────────────────────────────

CLARIFY_CASES = [
    ("전세 위험한지 봐줘",
     "어떤 매물인지 알려주시면 AI 위험 진단을 해드릴게요. "
     "**동네 이름과 보증금**은 꼭 필요하고, 전용면적·건축년도까지 주시면 더 정확해집니다. "
     "예: '불당동 8000만원, 33㎡, 2015년식'"),
    ("이 매물 깡통이야?",
     "매물 정보를 아직 받지 못했어요. 법정동명(예: 두정동)과 보증금(만원)을 알려주시겠어요? "
     "면적과 건축년도도 함께 주시면 진단 정확도가 올라갑니다."),
    ("위험도 진단해줘",
     "진단하려면 최소한 **동네 이름과 보증금**이 필요합니다. "
     "예를 들어 '성정동 6천만원 원룸'처럼 알려주세요."),
    ("안전점수 알려줘",
     "어느 동네의 안전점수가 궁금하신가요? 천안시 65개 법정동을 조회할 수 있어요. "
     "예: 불당동, 두정동, 안서동, 원성동…"),
    ("추천해줘",
     "안전한 동네를 추천해드릴게요! 우선 **보증금 예산**(만원)을 알려주세요. "
     "희망 면적이나 우선순위(치안·교통·편의시설 등), 선호하는 구(동남구/서북구)가 있으면 함께 알려주세요."),
    ("보증금 5000인데 어때?",
     "보증금 5,000만원 매물이군요. 어느 동네(법정동)인지 알려주시면 위험 진단을 바로 해드릴게요. "
     "동네를 아직 못 정하셨다면, 예산 기반 안전 동네 추천도 가능합니다 — '추천해줘'라고 말씀해주세요."),
    ("괜찮은 동네야?",
     "어느 동네를 말씀하시는지 알려주시면 8축 안전점수로 진단해드릴게요. "
     "천안시 법정동 이름(예: 쌍용동, 백석동)으로 물어봐주세요."),
]


def gen_clarify(n: int) -> list[dict]:
    out = []
    for i in range(n):
        q, a = CLARIFY_CASES[i % len(CLARIFY_CASES)]
        out.append(convo("clarify", [
            {"role": "user", "content": q},
            {"role": "assistant", "content": a},
        ]))
    return out


# ─────────────────────────────────────────────
# H. out_of_scope — 범위 밖 거절
# ─────────────────────────────────────────────

OOS_CASES = [
    ("비트코인 지금 사도 돼?",
     "죄송하지만 투자 상담은 제 전문 범위가 아니에요. 저는 천안시 전세 위험 진단과 "
     "주거 안전 상담을 전문으로 합니다. 자취방 계약이나 동네 안전이 궁금하시면 도와드릴게요!"),
    ("서울 강남 전세 시세 알려줘",
     "저는 **천안시** 전세 데이터에 특화된 상담원이라 서울 시세는 정확히 안내하기 어렵습니다. "
     "천안시 65개 법정동의 안전점수·전세가율·매물 위험 진단은 자신 있게 도와드릴 수 있어요."),
    ("오늘 저녁 뭐 먹을까?",
     "메뉴 고민은 도와드리기 어렵지만, 자취방 걱정은 확실히 덜어드릴 수 있어요. "
     "전세 계약이나 동네 안전 관련 질문이 있으시면 말씀해주세요!"),
    ("주식 종목 추천해줘",
     "투자 종목 추천은 제 역할이 아니에요. 대신 전세보증금을 지키는 일이라면 전문입니다. "
     "계약 전 위험 진단, 안전 동네 추천, HUG 보증 안내가 필요하시면 알려주세요."),
    ("파이썬 코딩 알려줘",
     "코딩 교육은 제 전문이 아니지만, 천안 자취방 안전은 데이터로 확실히 진단해드립니다. "
     "전세 계약 관련 궁금증이 있으시면 언제든 물어보세요!"),
]


def gen_oos(n: int) -> list[dict]:
    out = []
    for i in range(n):
        q, a = OOS_CASES[i % len(OOS_CASES)]
        out.append(convo("out_of_scope", [
            {"role": "user", "content": q},
            {"role": "assistant", "content": a},
        ]))
    return out


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────

def main():
    all_convos: list[dict] = []
    print("A. simulator 생성...")
    all_convos += gen_simulator(N_SIM)
    print("B. dong_lookup 생성...")
    all_convos += gen_dong(N_DONG)
    print("C. news 생성...")
    all_convos += gen_news(N_NEWS)
    print("D. recommend 생성...")
    all_convos += gen_recommend(N_RECO)
    print("E. kb_qa 생성...")
    all_convos += gen_kb(N_KB)
    print("F. multi_tool 생성...")
    all_convos += gen_multi(N_MULTI)
    print("G. clarify 생성...")
    all_convos += gen_clarify(N_CLARIFY)
    print("H. out_of_scope 생성...")
    all_convos += gen_oos(N_OOS)

    # intent별 층화 분할
    rng.shuffle(all_convos)
    by_intent: dict[str, list] = {}
    for c in all_convos:
        by_intent.setdefault(c["intent"], []).append(c)

    train, evals = [], []
    for intent, items in by_intent.items():
        k = max(1, int(len(items) * EVAL_RATIO))
        evals += items[:k]
        train += items[k:]
    rng.shuffle(train)
    rng.shuffle(evals)

    for name, data in [("train", train), ("eval", evals)]:
        path = DATA_DIR / f"{name}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for c in data:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        print(f"✓ {name}: {len(data):,}건 → {path}")

    stats = {intent: len(items) for intent, items in by_intent.items()}
    with open(DATA_DIR / "dataset_stats.json", "w", encoding="utf-8") as f:
        json.dump({"total": len(all_convos), "by_intent": stats,
                   "train": len(train), "eval": len(evals)}, f, ensure_ascii=False, indent=2)
    print(f"\n총 {len(all_convos):,}건 — intent 분포: {stats}")


if __name__ == "__main__":
    main()
