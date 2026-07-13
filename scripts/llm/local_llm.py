#!/usr/bin/env python3
"""
천안세이프 로컬 LLM 클라이언트 — vLLM OpenAI-호환 서버 + Tool-Calling 에이전트 루프

서버: scripts/llm/serve.sh (vLLM, hermes tool parser, port 8008)
모델: cheonan-safeguard-7b (Qwen2.5-7B-Instruct + 깡통전세 QLoRA)

기존 gpt-5-mini 자리를 대체한다. rag_chatbot.answer()가 이 모듈을 최우선 시도하고,
서버 미기동 시 기존 OpenAI/rule-based 경로로 자동 폴백한다.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

# 직접 실행/외부 임포트 모두에서 scripts.* 해석 가능하도록
_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

LOCAL_LLM_BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:8008/v1")
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "cheonan-safeguard-7b")
OPENAI_AGENT_MODEL = os.getenv("OPENAI_AGENT_MODEL", "gpt-5-mini")
MAX_TOOL_ROUNDS = 5  # 툴 2회 + 그라운딩 가드 재작성 여유

_client = None
_openai_client = None


def _get_client():
    """로컬 vLLM 클라이언트."""
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(base_url=LOCAL_LLM_BASE_URL, api_key="EMPTY", timeout=60)
    return _client


def _get_openai_client():
    from openai import OpenAI
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(timeout=90)
    return _openai_client


def is_available() -> bool:
    """vLLM 서버 헬스체크 (모델 목록 조회)."""
    try:
        models = _get_client().models.list()
        return any(m.id == LOCAL_LLM_MODEL for m in models.data)
    except Exception:
        return False


def pick_backend() -> tuple[str, object, str] | None:
    """(backend_tag, client, model) — 로컬 우선, 없으면 GPT API (동일 에이전트 기능).

    GPU 서버가 없는 시연 환경에서는 OPENAI_API_KEY만 있으면 같은 툴·가드로 동작한다.
    """
    if is_available():
        return ("local", _get_client(), LOCAL_LLM_MODEL)
    if os.getenv("OPENAI_API_KEY"):
        return ("openai", _get_openai_client(), OPENAI_AGENT_MODEL)
    return None


def _first_dong_in(text: str, dong_list: list[str]) -> str | None:
    """텍스트에 등장하는 첫 법정동명 (긴 이름 우선)."""
    for dong in sorted(dong_list, key=len, reverse=True):
        if dong in text:
            return dong
    return None


def _grounding_ok(query: str, answer: str, dong_list: list[str]) -> bool:
    """툴 없이 생성된 답변의 수치 그라운딩 검사.

    질문에 실제 동네 이름이 있고, 답변이 점수/확률/전세가율 수치를 주장하면 False.
    """
    import re

    if _first_dong_in(query, dong_list) is None:
        return True
    claims_number = re.search(r"\d+(\.\d+)?\s*(/\s*100|점|%)", answer)
    mentions_metric = re.search(r"안전점수|위험확률|전세가율", answer)
    return not (claims_number and mentions_metric)


# KB 상수 등 대화 이력 없이도 인용 가능한 수치 (천안 평균 77%, 위험 구간 경계 등)
_KNOWN_NUMBERS = {"60", "70", "77", "80", "90", "95", "100", "126", "20", "12", "132", "5", "7"}


def _numbers_grounded(answer: str, context_text: str) -> bool:
    """답변 속 지표 수치(%, /100, 점)가 대화 이력·툴 결과에 실재하는지 검사."""
    import re

    nums = re.findall(r"(\d+(?:\.\d+)?)\s*(?:%|점|/\s*100)", answer)
    for n in nums:
        if n in _KNOWN_NUMBERS:
            continue
        base = n.rstrip("0").rstrip(".") if "." in n else n
        if n not in context_text and base not in context_text:
            return False
    return True


def _kb_retrieve(query: str, k: int = 2, min_score: int = 6) -> list[dict]:
    """문자 bigram 빈도 기반 KB 검색 — '보증보험'↔'반환보증' 같은 표기 차이에 강함."""
    import re

    from scripts.rag_chatbot import KB_DOCS

    tokens = re.findall(r"[가-힣a-zA-Z0-9]{2,}", query.lower())
    grams: set[str] = set()
    for t in tokens:
        if re.match(r"[가-힣]", t):
            grams.update(t[i:i + 2] for i in range(len(t) - 1))
        else:
            grams.add(t)
    # 불용 bigram (일상어) 제거
    grams -= {"하려", "려면", "인데", "어요", "해줘", "알려", "받을", "있어", "뭐야", "니다"}

    scored = []
    for d in KB_DOCS:
        text = (d["title"] + " " + d["text"]).lower()
        score = sum(text.count(g) for g in grams)
        scored.append((score, d))
    scored.sort(key=lambda x: -x[0])
    return [d for s, d in scored[:k] if s >= min_score]


# ─────────────────────────────────────────────
# Tool 실행기 — rag_chatbot의 실제 툴 함수에 위임
# ─────────────────────────────────────────────

def _resolve_dong(name: str, dong_list: list[str]) -> tuple[str | None, str | None, list[str]]:
    """법정동명 검증/교정.

    Returns (확정 동명, 교정 전 이름 or None, 후보 리스트).
    - 정확 일치 → 그대로
    - 오타 → difflib 유사 동으로 교정
    - 읍/면 상위 단위 → 하위 리 후보 반환 (확정 불가)
    """
    import difflib

    name = (name or "").strip()
    if name in dong_list:
        return name, None, []
    # 읍/면 상위 단위: "병천면" → "병천면 ○○리" 후보들
    prefix_hits = [d for d in dong_list if d.startswith(name + " ") or d.startswith(name)]
    if name.endswith(("읍", "면")) and prefix_hits:
        return None, None, prefix_hits[:5]
    close = difflib.get_close_matches(name, dong_list, n=3, cutoff=0.6)
    if close:
        return close[0], name, close
    return None, None, prefix_hits[:5]


def _make_executors(df_safety, df_trends, dongnam_dongs) -> dict[str, Callable]:
    from scripts import rag_chatbot as rc

    dong_list = df_safety["법정동명"].dropna().unique().tolist()

    def run_simulator(args: dict):
        raw_dong = str(args.get("법정동명", ""))
        dong, corrected_from, candidates = _resolve_dong(raw_dong, dong_list)
        if dong is None:
            return {"error": f"'{raw_dong}'은(는) 천안시 법정동 목록에 없습니다.",
                    "안내": "정확한 동/리 이름이 필요합니다.",
                    "후보": candidates or ["예: 불당동, 두정동, 안서동"]}
        gu = rc._auto_gu(dong, dongnam_dongs or set())
        res = rc.tool_simulator(
            deposit=float(args["보증금_만원"]),
            area=float(args.get("전용면적") or 59.0),
            dong=dong,
            build_year=int(args.get("건축년도") or 2010),
            gu=gu,
        )
        if res is None:
            return {"error": "해당 조건으로 진단할 수 없습니다. 동네 이름을 확인해주세요."}
        out = {
            "risk_prob": res["risk_prob"], "signal": res["signal"],
            "signal_label": res["signal_label"], "safety_score": res.get("safety_score"),
            "shap_top5": [
                {"feature": x["feature"], "shap_value": round(float(x["shap_value"]), 3)}
                for x in res["shap_top5"][:5]
            ],
            "input": res["input"],
        }
        if corrected_from:
            out["동명_교정"] = f"'{corrected_from}'을(를) '{dong}'으로 해석해 진단함 — 사용자에게 알릴 것"
        return out

    def run_dong_lookup(args: dict):
        raw_dong = str(args.get("법정동명", ""))
        dong, corrected_from, candidates = _resolve_dong(raw_dong, dong_list)
        if dong is None:
            return {"error": f"'{raw_dong}'은(는) 천안시 법정동 목록에 없습니다.",
                    "후보": candidates or ["예: 불당동, 두정동, 안서동"]}
        res = rc.tool_dong_lookup(dong, df_safety, df_trends)
        if res is None:
            return {"error": f"'{dong}'을 찾지 못했습니다. 천안시 법정동명인지 확인해주세요."}
        if corrected_from:
            res = dict(res)
            res["동명_교정"] = f"'{corrected_from}'을(를) '{dong}'으로 해석함 — 사용자에게 알릴 것"
        return res

    def run_news(args: dict):
        items = rc.tool_news_search(str(args.get("query") or "천안 전세사기"), k=4)
        return {"items": items or [], "note": "" if items else "검색 결과 없음"}

    def run_recommend(args: dict):
        from scripts.recommender import recommend
        kwargs: dict[str, Any] = {"budget": float(args["budget"]), "top_k": 5}
        for key in ("area_min", "area_max"):
            if args.get(key) is not None:
                kwargs[key] = float(args[key])
        for key in ("priority", "gu"):
            if args.get(key):
                kwargs[key] = str(args[key])
        res = recommend(**kwargs)
        return {
            "n_candidates": res["n_candidates"],
            "dongs": [
                {**{k: v for k, v in d.items() if k != "대표매물"},
                 "대표매물": d["대표매물"][:1]}
                for d in res["dongs"][:3]
            ],
        } if res["dongs"] else res

    return {
        "simulator": run_simulator,
        "dong_lookup": run_dong_lookup,
        "news_search": run_news,
        "recommend": run_recommend,
    }


# ─────────────────────────────────────────────
# 에이전트 루프
# ─────────────────────────────────────────────

def chat(
    query: str,
    df_safety,
    df_trends=None,
    history: list[dict] | None = None,
    dongnam_dongs: set | None = None,
) -> dict | None:
    """
    로컬 LLM tool-calling 에이전트.

    Returns (성공 시):
        {"text", "tool_used", "tool_results", "radar_data", "news", "llm": "local"}
    실패/서버 미기동 시 None → 호출측 폴백.
    """
    from scripts.llm.tools_schema import CHEONAN_SYSTEM_PROMPT, SERVING_ADDENDUM, TOOLS

    _backend = pick_backend()
    if _backend is None:
        return None
    backend_tag, client, model_name = _backend
    executors = _make_executors(df_safety, df_trends, dongnam_dongs)
    dong_list = df_safety["법정동명"].dropna().unique().tolist()

    # KB 컨텍스트 주입 — 정책·제도 세부사항 환각 방지 (문자 bigram 검색, 키 불필요)
    kb_block = ""
    try:
        kb_docs = _kb_retrieve(query, k=2)
        if kb_docs:
            kb_block = (
                "\n\n[참고 지식 — 정책·제도·개념 질문은 반드시 아래 내용만 근거로 답하고, "
                "여기에 없는 조건·금액·기관명은 언급하지 않는다]\n"
                + "\n".join(f"- {d['title']}: {d['text']}" for d in kb_docs)
            )
    except Exception:
        pass

    system_content = CHEONAN_SYSTEM_PROMPT + SERVING_ADDENDUM + kb_block
    messages: list[dict] = [{"role": "system", "content": system_content}]
    for h in (history or [])[-8:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"],
                             "content": h["content"].replace("---RADAR---", "").strip()})
    messages.append({"role": "user", "content": query})

    tool_used: list[str] = []
    tool_results: dict[str, Any] = {}
    _number_retry_done = False

    try:
        for _ in range(MAX_TOOL_ROUNDS):
            _kw = dict(model=model_name, messages=messages, tools=TOOLS)
            if model_name.startswith(("gpt-5", "o1", "o3")):
                _kw["max_completion_tokens"] = 2500  # reasoning 토큰 여유
            else:
                _kw.update(temperature=0.0, max_tokens=700)
            resp = client.chat.completions.create(**_kw)
            msg = resp.choices[0].message

            if not msg.tool_calls:
                text = (msg.content or "").strip()
                if not text:
                    return None
                # ── 그라운딩 가드 1: 동네가 언급됐는데 툴 없이 수치를 말하면 강제 조회 후 재작성 ──
                if not tool_used and not _grounding_ok(query, text, dong_list):
                    dong = _first_dong_in(query, dong_list)
                    result = executors["dong_lookup"]({"법정동명": dong})
                    tool_used.append("dong_lookup")
                    tool_results["dong_lookup"] = result
                    messages.append({"role": "assistant", "content": text})
                    messages.append({
                        "role": "user",
                        "content": (
                            "[시스템 검증] 방금 답변의 수치는 도구로 확인되지 않았습니다. "
                            f"아래 {dong} 실제 조회 결과만 근거로 답변을 다시 작성하세요.\n"
                            + json.dumps(result, ensure_ascii=False, default=str)
                        ),
                    })
                    continue

                # ── 그라운딩 가드 2: 툴 없는 턴이 이력에 없는 지표 수치를 만들면 1회 재작성 ──
                if not tool_used and not _number_retry_done:
                    context_text = json.dumps(messages, ensure_ascii=False, default=str) \
                        + json.dumps(tool_results, ensure_ascii=False, default=str)
                    if not _numbers_grounded(text, context_text):
                        _number_retry_done = True
                        messages.append({"role": "assistant", "content": text})
                        messages.append({
                            "role": "user",
                            "content": (
                                "[시스템 검증] 방금 답변에 이전 대화·도구 결과에 없는 수치가 있습니다. "
                                "수치는 이전 대화에 등장한 값만 그대로 인용해 다시 답하세요. "
                                "인용할 수치가 없으면 수치 없이 답하세요."
                            ),
                        })
                        continue
                radar_data = None
                if tool_results.get("dong_lookup") and "축별점수" in tool_results["dong_lookup"]:
                    d = tool_results["dong_lookup"]
                    radar_data = {"dong": d["dong"],
                                  "axes": list(d["축별점수"].keys()),
                                  "values": list(d["축별점수"].values())}
                return {
                    "text": text,
                    "tool_used": tool_used,
                    "tool_results": tool_results,
                    "radar_data": radar_data,
                    "news": (tool_results.get("news_search") or {}).get("items", []),
                    "llm": backend_tag,
                }

            # 툴 실행 후 결과를 대화에 추가
            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
            })
            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except Exception:
                    args = {}
                fn = executors.get(name)
                result = fn(args) if fn else {"error": f"unknown tool: {name}"}
                tool_used.append(name)
                tool_results[name] = result
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })
        return None  # 루프 초과
    except Exception:
        return None


if __name__ == "__main__":
    import pandas as pd
    root = Path(__file__).resolve().parent.parent.parent
    df_s = pd.read_parquet(root / "data" / "processed" / "dong_safety_score.parquet")
    df_t = pd.read_parquet(root / "data" / "processed" / "dong_jeonse_trends.parquet")
    print("서버 상태:", is_available())
    for q in ["불당동에 보증금 8000만원 33㎡ 2015년식 전세 위험해?",
              "원성동 안전해?",
              "깡통전세가 뭐야?"]:
        out = chat(q, df_s, df_t)
        print("\nQ:", q)
        print("A:", (out or {}).get("text", "(실패)")[:400])
        print("tools:", (out or {}).get("tool_used"))
