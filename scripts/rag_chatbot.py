#!/usr/bin/env python3
"""
RAG 챗봇 — 천안 청년 자취방 안전지도

Architecture
────────────
    User Query
        │
        ▼
  ┌─────────────────────────────────────────┐
  │ 1. Intent Router                         │
  │    - 매물 파라미터 감지 → simulator tool  │
  │    - 동네명 감지 → dong_lookup tool       │
  │    - 그 외 → 일반 RAG                    │
  └─────────────────────────────────────────┘
        │
        ▼
  ┌─────────────────────────────────────────┐
  │ 2. Retrieval                             │
  │    - KB(정책·개념·체크리스트) 임베딩       │
  │    - OpenAI text-embedding-3-small       │
  │    - 코사인 유사도 top-k 검색             │
  │    - 임베딩 실패 시 키워드 매칭 fallback   │
  └─────────────────────────────────────────┘
        │
        ▼
  ┌─────────────────────────────────────────┐
  │ 3. Tool Execution                        │
  │    - LightGBM predict() + SHAP           │
  │    - 동별 안전점수/추세 조회               │
  └─────────────────────────────────────────┘
        │
        ▼
  ┌─────────────────────────────────────────┐
  │ 4. LLM Generation                        │
  │    - OpenAI gpt-4o-mini (context 주입)   │
  │    - 없으면 rule-based composer fallback │
  └─────────────────────────────────────────┘
        │
        ▼
    Response (+ tool result markers)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ─── API 키 로드: (1) 로컬 .env → (2) 시스템 env → (3) Streamlit secrets ───
try:
    from dotenv import load_dotenv
    _ENV_CANDIDATES = [
        Path(__file__).resolve().parent.parent / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
    ]
    for _p in _ENV_CANDIDATES:
        if _p.exists():
            load_dotenv(_p)
            break
except ImportError:
    pass

# Streamlit Cloud 배포 시: st.secrets → 환경변수로 승격
def _load_from_streamlit_secrets():
    try:
        import streamlit as st
        # st.secrets 접근은 앱 컨텍스트가 있을 때만 유효
        if hasattr(st, "secrets") and "OPENAI_API_KEY" in st.secrets:
            if not os.environ.get("OPENAI_API_KEY"):
                os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass

_load_from_streamlit_secrets()


# ═════════════════════════════════════════════
# 1. Knowledge Base
# ═════════════════════════════════════════════

KB_DOCS: list[dict[str, str]] = [
    {
        "id": "concept_jeonse_rate",
        "title": "전세가율의 의미와 위험 구간",
        "text": (
            "전세가율은 전세보증금을 매매가로 나눈 비율(%)이다. "
            "60% 이하는 안전, 60~80%는 주의, 80~90%는 위험, 90% 이상은 심각 위험이며, "
            "100% 이상이면 매매가보다 보증금이 높은 '깡통전세' 상태다. "
            "천안시 평균 전세가율은 약 77%로 전국 평균보다 다소 높다. "
            "HUG 안심전세는 공시가격 × 126% 규정을 사용하며, 이를 초과하는 보증금은 반환보증 가입이 어려울 수 있다."
        ),
    },
    {
        "id": "concept_gangton",
        "title": "깡통전세 정의와 천안시 피해 현황",
        "text": (
            "깡통전세는 전세보증금이 매매가에 근접하거나 초과하는 상태로, 임대인이 파산하거나 "
            "경매에 부쳐질 경우 세입자가 보증금을 돌려받지 못할 위험이 크다. "
            "천안시 전세사기 피해는 288세대, 피해액 145억원으로 집계되며, 특히 동남구 구도심에 집중된다. "
            "예방 수단: 등기부등본 열람, HUG 전세보증보험 가입, 공인중개사 통한 거래, 계약 전 시세 확인."
        ),
    },
    {
        "id": "policy_hug",
        "title": "HUG 전세보증금 반환보증",
        "text": (
            "HUG(주택도시보증공사) 전세보증금 반환보증은 임대인이 계약 종료 후 보증금을 반환하지 못할 때 "
            "HUG가 대신 지급하는 제도다. 가입 조건: 전세보증금이 수도권 7억원 이하, 그 외 5억원 이하, "
            "선순위 채권 합계가 주택가격의 60% 이내 등. 보증료는 보증금·기간에 따라 다르며, "
            "천안시 청년의 경우 일부 보증료 지원 대상이 될 수 있다. 신청: HUG 홈페이지 또는 위탁은행."
        ),
    },
    {
        "id": "policy_youth_rent",
        "title": "청년 월세 지원 (천안시)",
        "text": (
            "천안시는 무주택 청년(19~34세)에게 월 최대 20만원, 최대 12개월간 월세를 지원한다. "
            "조건: 부모 포함 가구 소득 중위 100% 이하, 청년 본인 소득 중위 60% 이하, "
            "임차보증금 5천만원 이하 및 월세 60만원 이하 주택 거주 등. "
            "신청은 복지로(bokjiro.go.kr) 또는 천안시청 주거복지과(041-521-5252)."
        ),
    },
    {
        "id": "policy_anshim",
        "title": "안심계약 도움서비스",
        "text": (
            "안심계약 도움서비스는 전세 계약 시 전문가(공인중개사·법률 자문 등)가 동석하여 "
            "등기부등본 확인, 계약서 검토, 특약 조언을 무료 제공하는 제도다. "
            "천안시는 전세사기 예방을 위해 이 서비스 신청을 권장하며, 계약 체결 전 최소 3영업일 전에 신청해야 한다."
        ),
    },
    {
        "id": "checklist_contract",
        "title": "전세 계약 전 필수 체크리스트",
        "text": (
            "1) 등기부등본에서 근저당·가압류·소유주 확인 (계약 당일 재발급 권장). "
            "2) 임대인 본인 확인 — 신분증 대조, 대리인이면 위임장·인감증명서 필수. "
            "3) 전세가율 80% 이하가 안전, 그 이상이면 HUG 보험 필수. "
            "4) HUG 전세보증금 반환보증 가입 (보증료 지원 대상 확인). "
            "5) 계약 후 즉시 전입신고 + 확정일자 (대항력·우선변제권 확보). "
            "6) 특약: 근저당 말소 조건, 원상복구 범위, 하자 처리 등 명시."
        ),
    },
    {
        "id": "checklist_warning",
        "title": "전세 계약 시 위험 신호 리스트",
        "text": (
            "시세 대비 지나치게 높은 보증금, 계약 서두르는 임대인, 등기부등본 열람 회피, "
            "다수 세대 소유의 신축 다세대(빌라)에서 유사 계약 반복, 임대인이 대리인만 내세우는 경우, "
            "선순위 근저당이 매매가의 60%를 넘는 경우 — 모두 전세사기 위험 신호다. "
            "이런 신호가 3개 이상이면 계약을 재고하고 안심계약 도움서비스를 반드시 신청하라."
        ),
    },
    {
        "id": "concept_lightgbm_ai",
        "title": "AI 위험도 진단 모델(LightGBM)의 원리",
        "text": (
            "본 서비스의 깡통전세 위험도 진단은 LightGBM 분류기로 예측한다. "
            "입력: 보증금, 전용면적, 법정동, 건축년도, 구. "
            "피처 26종: ㎡당 보증금, 동 평균 대비 비율, 건물연령, 노후비율, 내진비율, 세대수 등. "
            "SHAP으로 상위 5개 기여 피처를 설명하여 '왜 위험한지' 근거를 제시한다. "
            "AUC 0.989로 검증되었으며, 위험확률 0.7 이상은 빨강(위험), 0.3~0.7은 노랑(주의), 그 미만은 초록(안전)이다."
        ),
    },
    {
        "id": "concept_safety_score",
        "title": "8축 종합 안전점수 산출 방식",
        "text": (
            "동네 종합 안전점수(0~100)는 8개 축의 가중합이다: 금융안전(전세가율 역수), "
            "건물노후(연령·내진), 침수위험(재해구역), 치안(범죄율·CCTV), 소방(소방서 접근), "
            "교통(대중교통 접근), 편의시설(마트·병원 밀도), 환경(대기·녹지). "
            "신호등: 60점 이상 초록(안전), 40~60점 노랑(주의), 40점 미만 빨강(위험). "
            "구도심(동남구)은 구조적으로 노후·침수 축이 낮아 평균 안전점수가 서북구보다 낮다."
        ),
    },
    {
        "id": "concept_registry",
        "title": "등기부등본 확인 포인트",
        "text": (
            "등기부등본(부동산등기)의 '을구'에서 근저당권·전세권 등 담보권을, "
            "'갑구'에서 소유권 변동·가압류를 확인한다. "
            "핵심 확인 사항: 근저당 채권최고액 + 예상 전세금이 매매가의 80%를 넘지 않는지, "
            "임대인 이름과 계약서상 이름이 일치하는지, 최근 소유권 변동이 없었는지. "
            "인터넷 등기소(iros.go.kr)에서 700원으로 열람 가능하며, 계약 당일 재발급을 권장한다."
        ),
    },
    {
        "id": "concept_ipsingogo",
        "title": "전입신고와 확정일자의 법적 효과",
        "text": (
            "전입신고를 하면 '대항력'이 발생해 임대인이 바뀌어도 세입자 지위를 유지할 수 있다. "
            "확정일자를 받으면 '우선변제권'이 생겨 경매·공매 시 후순위 채권자보다 먼저 배당받는다. "
            "두 절차 모두 계약 즉시(늦어도 이사 당일) 완료해야 하며, "
            "정부24 또는 주민센터에서 처리한다. 이 두 조치 없이는 HUG 보험도 무의미하다."
        ),
    },
    {
        "id": "context_gu_gap",
        "title": "천안시 구도심-신도심 격차",
        "text": (
            "동남구는 원도심으로 건물 노후율·전세가율이 높고 침수 위험 지역이 다수 포함되어 있다. "
            "서북구는 불당·성성 등 신도심으로 인프라·안전점수가 상대적으로 높다. "
            "다만 서북구도 두정·성성 일부는 신축 다세대의 깡통전세 이슈가 있으니 방심하지 말고, "
            "동남구에도 문성·다가 등 상대적으로 양호한 지역이 있다. 개별 매물 진단이 필수."
        ),
    },
    {
        "id": "context_youth",
        "title": "천안시 청년 주거 현실",
        "text": (
            "천안시 18~39세 청년은 19.7만명, 그중 86%가 무주택이다. "
            "대학·산업단지가 집중되어 청년 유입은 많지만, 전세사기 피해가 계속 늘고 있어 "
            "청년 주거안전은 지역균형발전의 핵심 과제다. "
            "본 서비스는 계약 전 위험을 미리 진단해 이러한 격차와 피해를 예방한다."
        ),
    },
    {
        "id": "guide_use_service",
        "title": "본 서비스 사용법",
        "text": (
            "1) '내 매물 체크' 탭: 보증금·면적·동·건축년도 입력 → AI가 위험확률과 SHAP 설명 제공. "
            "2) '안전지도' 탭: 65개 동 신호등 지도 + Google Roadmap으로 실제 위치 확인. "
            "3) '예산별 추천' 탭: 예산에 맞는 안전 동네 추천. "
            "4) '계약 가이드' 탭: 단계별 체크리스트. "
            "5) 'AI 상담' 탭: 자연어로 질문 → 이 챗봇이 답변."
        ),
    },
]


# ═════════════════════════════════════════════
# 2. Embedding + Vector Index
# ═════════════════════════════════════════════

_kb_matrix: np.ndarray | None = None
EMBED_MODEL_NAME = "text-embedding-3-small"  # 1536-dim, 저렴, 한국어 우수


def _embed_texts(texts: list[str]) -> np.ndarray | None:
    """OpenAI Embeddings API로 문서 벡터화 후 L2 정규화."""
    try:
        from openai import OpenAI
        client = OpenAI()
        resp = client.embeddings.create(model=EMBED_MODEL_NAME, input=texts)
        vecs = np.array([d.embedding for d in resp.data], dtype=np.float32)
        # 정규화 → dot product == cosine sim
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vecs / norms
    except Exception:
        return None


def _build_kb_index() -> np.ndarray | None:
    """KB 문서 임베딩 행렬 구축 (한 번만 호출; 캐시)."""
    global _kb_matrix
    if _kb_matrix is None:
        texts = [f"{d['title']} — {d['text']}" for d in KB_DOCS]
        _kb_matrix = _embed_texts(texts)
    return _kb_matrix


def retrieve(query: str, k: int = 3) -> list[dict]:
    """쿼리와 가장 유사한 KB 문서 top-k 반환. 임베딩 실패 시 키워드 fallback."""
    matrix = _build_kb_index()
    if matrix is None:
        return _keyword_retrieve(query, k)

    q_vec_batch = _embed_texts([query])
    if q_vec_batch is None:
        return _keyword_retrieve(query, k)

    q_vec = q_vec_batch[0]
    sims = matrix @ q_vec  # cosine sim (정규화됨)
    top_idx = np.argsort(-sims)[:k]
    return [
        {**KB_DOCS[i], "score": float(sims[i])}
        for i in top_idx
    ]


def _keyword_retrieve(query: str, k: int) -> list[dict]:
    """임베딩 없이 키워드 매칭 fallback."""
    q_terms = set(re.findall(r"\w+", query.lower()))
    scored = []
    for d in KB_DOCS:
        text = (d["title"] + " " + d["text"]).lower()
        score = sum(1 for t in q_terms if t in text)
        scored.append({**d, "score": score})
    scored.sort(key=lambda x: -x["score"])
    return scored[:k]


# ═════════════════════════════════════════════
# 3. Tools (LightGBM 시뮬레이터 + 동 조회)
# ═════════════════════════════════════════════

@dataclass
class ExtractedParams:
    deposit: float | None = None    # 만원
    area: float | None = None       # ㎡
    build_year: int | None = None
    dong: str | None = None


def extract_property_params(query: str, dong_list: list[str]) -> ExtractedParams:
    """자연어에서 매물 파라미터 추출."""
    params = ExtractedParams()

    # 보증금: 5000만원, 3천만, 1억, 1억5천 등
    m_eok_man = re.search(r"(\d+)\s*억\s*(\d+)\s*(?:천만|천)", query)
    m_eok = re.search(r"(\d+(?:\.\d+)?)\s*억", query)
    m_man = re.search(r"(\d+(?:\.\d+)?)\s*(?:천만|만원|만)", query)

    if m_eok_man:
        params.deposit = float(m_eok_man.group(1)) * 10000 + float(m_eok_man.group(2)) * 1000
    elif m_eok:
        params.deposit = float(m_eok.group(1)) * 10000
    elif m_man:
        val = float(m_man.group(1))
        # "3천" 표기 처리
        if "천" in query and val < 100:
            val *= 1000
        params.deposit = val

    # 면적: 33㎡, 25평
    m_area = re.search(r"(\d+(?:\.\d+)?)\s*(?:㎡|제곱미터)", query)
    m_pyeong = re.search(r"(\d+(?:\.\d+)?)\s*평", query)
    if m_area:
        params.area = float(m_area.group(1))
    elif m_pyeong:
        params.area = float(m_pyeong.group(1)) * 3.3058

    # 건축년도: 1990년, 2010년식
    m_year = re.search(r"(19[7-9]\d|20[0-2]\d)\s*(?:년|년식|년도)?", query)
    if m_year:
        params.build_year = int(m_year.group(1))

    # 동 매칭 (긴 이름 우선)
    for dong in sorted(dong_list, key=len, reverse=True):
        if dong in query:
            params.dong = dong
            break

    return params


def tool_simulator(deposit: float, area: float, dong: str, build_year: int, gu: str) -> dict | None:
    """LightGBM 위험도 시뮬레이터 호출."""
    try:
        from scripts.simulator import predict
        return predict(
            보증금_만원=deposit,
            전용면적=area,
            법정동명=dong,
            건축년도=build_year,
            구=gu,
        )
    except Exception as e:
        return None


def tool_dong_lookup(dong: str, df_safety: pd.DataFrame, df_trends: pd.DataFrame | None = None) -> dict | None:
    """동별 안전점수·8축·추세 조회."""
    row = df_safety[df_safety["법정동명"] == dong]
    if len(row) == 0:
        return None
    r = row.iloc[0]

    axes = ["금융안전", "건물노후", "침수위험", "치안", "소방", "교통", "편의시설", "환경"]
    axes_vals = {a: float(r.get(f"{a}_점수", 0.5)) for a in axes}

    result = {
        "dong": dong,
        "종합안전점수": float(r["종합안전점수"]),
        "신호등": str(r["신호등"]),
        "전세가율_평균": float(r["전세가율_평균"]) if pd.notna(r.get("전세가율_평균")) else None,
        "전세거래수": int(r["전세거래수"]) if pd.notna(r.get("전세거래수")) else None,
        "축별점수": axes_vals,
        "최강축": max(axes_vals, key=axes_vals.get),
        "최약축": min(axes_vals, key=axes_vals.get),
    }

    if df_trends is not None:
        t_row = df_trends[df_trends["법정동명"] == dong]
        if len(t_row) > 0:
            tr = t_row.iloc[0]
            result["추세"] = {
                "최근_전세가율": float(tr["최근_전세가율"]),
                "6개월_추세": float(tr["6개월_추세"]),
                "추세_판정": str(tr["추세_판정"]),
            }
    return result


# ═════════════════════════════════════════════
# 4. LLM Generation (OpenAI + fallback)
# ═════════════════════════════════════════════

SYSTEM_PROMPT = """너는 '천안 청년 자취방 안전지도' 서비스의 AI 상담 어시스턴트다.
청년 세입자에게 전세 계약 위험, 동네 안전성, 정책·제도를 안내한다.

원칙:
- 반드시 제공된 [Context]와 [Tool Result]에 근거해 답하고, 없는 사실은 지어내지 않는다.
- 숫자·점수·신호등은 Tool Result의 값을 그대로 사용한다.
- 위험도가 노랑/빨강이면 계약 주의를 명확히 경고한다.
- 답변은 한국어로, 마크다운 사용 가능. 3~7문장 내로 간결히.
- 마지막에 "**내 매물 체크** / **안전지도** / **계약 가이드**" 탭 중 관련 탭을 안내.
"""


def _has_openai_key() -> bool:
    # 매 호출마다 secrets 재로드 시도 (import 타이밍 문제 회피)
    _load_from_streamlit_secrets()
    return bool(os.getenv("OPENAI_API_KEY"))


def diagnose() -> dict:
    """배포 진단용 — Streamlit Cloud에서 OpenAI 연결 상태 확인."""
    _load_from_streamlit_secrets()
    info = {
        "openai_key_present": bool(os.getenv("OPENAI_API_KEY")),
        "openai_key_prefix": (os.getenv("OPENAI_API_KEY") or "")[:10] + "..." if os.getenv("OPENAI_API_KEY") else None,
        "openai_reachable": False,
        "error": None,
    }
    if info["openai_key_present"]:
        try:
            from openai import OpenAI
            client = OpenAI()
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            info["openai_reachable"] = bool(resp.choices)
        except Exception as e:
            info["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    return info


def _call_openai(query: str, context: str, history: list[dict]) -> str | None:
    """OpenAI chat.completions 호출."""
    try:
        from openai import OpenAI
        client = OpenAI()

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # 최근 4턴만 유지
        for h in history[-8:]:
            if h.get("role") in ("user", "assistant") and h.get("content"):
                # RADAR 마커 등 제거
                content = h["content"].replace("---RADAR---", "").strip()
                messages.append({"role": h["role"], "content": content})

        user_content = f"[Context 및 Tool Result]\n{context}\n\n[User Question]\n{query}"
        messages.append({"role": "user", "content": user_content})

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.3,
            max_tokens=600,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return None


# ═════════════════════════════════════════════
# 5. Orchestrator (핵심 진입점)
# ═════════════════════════════════════════════

def _auto_gu(dong: str, dongnam_dongs: set[str]) -> str:
    if dong in dongnam_dongs:
        return "동남구"
    if any(k in dong for k in ["목천", "병천", "북면", "풍세", "성남", "수신", "동면", "광덕", "성거", "직산", "입장"]):
        return "동남구" if any(k in dong for k in ["목천", "병천", "북면", "풍세", "성남", "수신", "동면", "광덕"]) else "서북구"
    return "서북구"


def _build_context(query: str, retrieved: list[dict], tool_results: dict) -> str:
    """검색 결과 + Tool 결과를 LLM용 컨텍스트로 조립."""
    parts = []

    # 1. 검색된 KB 문서
    if retrieved:
        parts.append("## 관련 문서 (KB Retrieval)")
        for i, d in enumerate(retrieved, 1):
            parts.append(f"[{i}] {d['title']}\n{d['text']}")

    # 2. Tool 결과
    if tool_results.get("simulator"):
        s = tool_results["simulator"]
        parts.append("## LightGBM 시뮬레이터 결과")
        parts.append(
            f"- 입력: 보증금 {s['input']['보증금_만원']:,}만원, 면적 {s['input']['전용면적']}㎡, "
            f"{s['input']['법정동명']}, 건축 {s['input']['건축년도']}년"
        )
        parts.append(f"- 위험확률: {s['risk_prob']:.1%}")
        parts.append(f"- 신호등: {s['signal']} ({s['signal_label']})")
        if s.get("safety_score"):
            parts.append(f"- 동 안전점수: {s['safety_score']:.1f}/100")
        shap_lines = []
        for sh in s["shap_top5"][:5]:
            direction = "위험 증가" if sh["shap_value"] > 0 else "위험 감소"
            shap_lines.append(f"  · {sh['feature']}: SHAP {sh['shap_value']:+.3f} ({direction})")
        parts.append("- SHAP 상위 5개 기여 피처:\n" + "\n".join(shap_lines))

    if tool_results.get("dong"):
        d = tool_results["dong"]
        parts.append(f"## 동네 조회 결과 — {d['dong']}")
        parts.append(f"- 종합 안전점수: {d['종합안전점수']:.1f}/100 ({d['신호등']})")
        if d.get("전세가율_평균") is not None:
            parts.append(f"- 평균 전세가율: {d['전세가율_평균']:.0%}")
        if d.get("전세거래수") is not None:
            parts.append(f"- 전세 거래수: {d['전세거래수']:,}건")
        parts.append(f"- 최강 축: {d['최강축']} ({d['축별점수'][d['최강축']]:.2f})")
        parts.append(f"- 최약 축: {d['최약축']} ({d['축별점수'][d['최약축']]:.2f})")
        if d.get("추세"):
            t = d["추세"]
            parts.append(f"- 최근 전세가율: {t['최근_전세가율']:.0%}, 6개월 추세: {t['6개월_추세']:+.1%} ({t['추세_판정']})")

    return "\n\n".join(parts) if parts else "관련 문서를 찾지 못했습니다."


def _fallback_compose(query: str, retrieved: list[dict], tool_results: dict) -> str:
    """OpenAI 실패 시 rule-based로 답변 조립."""
    out = []

    if tool_results.get("simulator"):
        s = tool_results["simulator"]
        icon = {"빨강": "🔴", "노랑": "🟡", "초록": "🟢"}[s["signal"]]
        out.append(f"**AI 위험도 진단 — {s['input']['법정동명']}**")
        out.append(f"- 보증금 {s['input']['보증금_만원']:,.0f}만원 · 면적 {s['input']['전용면적']:.0f}㎡ · 건축 {s['input']['건축년도']}년")
        out.append(f"- {icon} **{s['signal_label']}** (위험확률 {s['risk_prob']:.1%})")
        if s.get("safety_score"):
            out.append(f"- 동네 안전점수: {s['safety_score']:.1f}/100")
        out.append("\n**주요 위험 요인 (SHAP):**")
        for sh in s["shap_top5"][:3]:
            d = "↑위험" if sh["shap_value"] > 0 else "↓안전"
            out.append(f"  - {sh['feature']}: {sh['shap_value']:+.3f} ({d})")

    if tool_results.get("dong"):
        d = tool_results["dong"]
        icon = {"빨강": "🔴", "노랑": "🟡", "초록": "🟢"}.get(d["신호등"], "⚪")
        out.append(f"\n**{d['dong']} 종합 진단**")
        out.append(f"- {icon} 안전점수 {d['종합안전점수']:.1f}/100 ({d['신호등']})")
        if d.get("전세가율_평균") is not None:
            out.append(f"- 평균 전세가율 {d['전세가율_평균']:.0%}")
        out.append(f"- 강점: {d['최강축']} / 약점: {d['최약축']}")

    if retrieved and not tool_results:
        out.append("**관련 정보:**")
        for d in retrieved[:2]:
            out.append(f"- {d['title']}: {d['text'][:150]}...")

    if not out:
        out.append("궁금한 점을 좀 더 구체적으로 알려주세요. 동네명, 보증금 금액, 정책 이름 등을 포함하면 도움이 됩니다.")

    out.append("\n💡 자세한 진단은 **내 매물 체크** 탭, 동네 비교는 **안전지도** 탭을 활용하세요.")
    return "\n".join(out)


def answer(
    query: str,
    df_safety: pd.DataFrame,
    df_trends: pd.DataFrame | None = None,
    history: list[dict] | None = None,
    dongnam_dongs: set[str] | None = None,
) -> dict:
    """
    RAG 챗봇 진입점.

    Returns:
        {
            "text": str,             # 최종 답변
            "radar_data": dict|None, # 8축 레이더 차트 데이터 (있으면)
            "tool_used": list[str],  # 호출된 툴 이름들
            "retrieved": list[dict], # 참조 문서 (근거 표시용)
            "llm": "openai"|"fallback",
        }
    """
    history = history or []
    dongnam_dongs = dongnam_dongs or set()
    dong_list = df_safety["법정동명"].dropna().unique().tolist()

    # 1) Intent Routing — 파라미터 추출
    params = extract_property_params(query, dong_list)

    # 2) Retrieval — KB 검색
    retrieved = retrieve(query, k=3)

    # 3) Tool 실행
    tool_results: dict[str, Any] = {}
    tool_used = []
    radar_data = None

    if params.dong and params.deposit is not None:
        # 매물 시뮬레이션
        gu = _auto_gu(params.dong, dongnam_dongs)
        sim_result = tool_simulator(
            deposit=params.deposit,
            area=params.area or 59.0,
            dong=params.dong,
            build_year=params.build_year or 2010,
            gu=gu,
        )
        if sim_result:
            tool_results["simulator"] = sim_result
            tool_used.append("simulator")

    if params.dong and "simulator" not in tool_used:
        # 동네 조회만
        dong_info = tool_dong_lookup(params.dong, df_safety, df_trends)
        if dong_info:
            tool_results["dong"] = dong_info
            tool_used.append("dong_lookup")
            radar_data = {
                "dong": dong_info["dong"],
                "axes": list(dong_info["축별점수"].keys()),
                "values": list(dong_info["축별점수"].values()),
            }

    # 4) LLM 생성
    context = _build_context(query, retrieved, tool_results)
    llm_source = "fallback"
    text = None

    if _has_openai_key():
        text = _call_openai(query, context, history)
        if text:
            llm_source = "openai"

    if not text:
        text = _fallback_compose(query, retrieved, tool_results)

    return {
        "text": text,
        "radar_data": radar_data,
        "tool_used": tool_used,
        "retrieved": retrieved,
        "llm": llm_source,
    }


if __name__ == "__main__":
    # 스모크 테스트
    import sys
    print("KB 문서 수:", len(KB_DOCS))
    print("OpenAI 키 감지:", _has_openai_key())
    print("\n--- Retrieval 테스트 ---")
    for d in retrieve("깡통전세가 뭐야", k=2):
        print(f"  [{d['score']:.3f}] {d['title']}")
    print("\n--- 파라미터 추출 테스트 ---")
    p = extract_property_params("안서동 5000만원 33㎡ 1990년", ["안서동", "불당동"])
    print(f"  deposit={p.deposit}, area={p.area}, year={p.build_year}, dong={p.dong}")
