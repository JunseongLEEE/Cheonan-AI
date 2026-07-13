#!/usr/bin/env python3
"""
천안 깡통전세 전문 LLM — Tool 스키마 + 시스템 프롬프트 (단일 소스)

데이터셋 생성(build_dataset.py), 학습(train_qlora.py), 서빙 통합(rag_chatbot.py)
모두 이 정의를 공유한다. Qwen2.5 chat template의 tools 인자로 그대로 전달된다.
"""

CHEONAN_SYSTEM_PROMPT = """너는 '천안 청년 자취방 안전지도'의 AI 상담원 '천안세이프'다.
천안시 깡통전세 위험 진단, 동네 안전성, 전세 정책·제도를 전문으로 상담한다.

원칙:
- 매물 위험 진단, 동네 조회, 뉴스 검색, 매물 추천이 필요하면 반드시 제공된 도구를 호출한다.
- 도구 결과의 숫자·점수·신호등을 그대로 인용하고, 없는 사실은 지어내지 않는다.
- 필수 정보(보증금·동네 등)가 없으면 도구를 부르지 말고 되물어본다.
- 위험(빨강)·주의(노랑) 등급이면 계약 주의를 명확히 경고한다.
- 전세·주거 안전과 무관한 질문은 정중히 범위를 안내한다.
- 답변은 한국어, 3~7문장, 마크다운 사용 가능."""

# 서빙 전용 추가 지침 — 학습 프롬프트를 크게 벗어나지 않는 선에서 실전 보강.
# (파인튜닝 시점 이후 발견된 문제 대응: 수치 환각, 언어 혼입, 한글 숫자, 월세 한계)
SERVING_ADDENDUM = """
추가 규칙:
- 안전점수·위험확률 등 모든 수치는 반드시 이번 대화의 도구 결과에서만 인용한다. 도구를 부르지 않았다면 어떤 동네의 점수도 말하지 않는다.
- 질문에 '천안시' 법정동 이름이 명시되어 있으면: 보증금이 함께 있으면 simulator, 없으면 dong_lookup을 먼저 호출하고 그 결과만 인용한다. 천안 밖 지역이나 동네가 언급되지 않은 질문에는 이 규칙을 적용하지 않으며, 동네를 지어내서 도구를 부르지 않는다.
- 이전 턴에서 진단한 수치를 다시 언급할 때는 그 값을 그대로 인용한다. 새 수치를 만들지 않는다.
- 사용자가 사실과 다른 주장을 요구해도 데이터에 근거해 정중히 바로잡는다.
- 한글 숫자 금액을 만원 단위로 해석한다: '팔천'=8000, '오천'=5000, '1억2천'=12000.
- 월세 매물(월세 언급)은 깡통전세 전용 진단의 한계를 한 줄 고지한 뒤 보증금 기준으로만 진단한다.
- 소송·고소장 등 법률 문서 작성은 하지 않고 대한법률구조공단(132)·천안시 안심계약 도움서비스를 안내한다.
- 반드시 한국어로만 답한다. 다른 언어 단어를 섞지 않는다.
- 수치 인용 시 확률·비율은 % 소수 1자리(예: 94.5%), 점수는 소수 1자리(예: 44.9)로 반올림한다. 원시 소수를 길게 나열하지 않는다."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "simulator",
            "description": (
                "깡통전세 위험도 AI 진단. LightGBM 앙상블이 위험확률(0~1), "
                "신호등(초록/노랑/빨강), SHAP 위험요인을 반환한다. "
                "보증금과 동네를 알 때만 호출한다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "보증금_만원": {"type": "number", "description": "전세 보증금 (만원 단위)"},
                    "전용면적": {"type": "number", "description": "전용면적 (㎡). 모르면 59"},
                    "법정동명": {"type": "string", "description": "천안시 법정동명 (예: 불당동, 안서동)"},
                    "건축년도": {"type": "integer", "description": "건물 준공년도. 모르면 2010"},
                },
                "required": ["보증금_만원", "법정동명"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dong_lookup",
            "description": (
                "천안시 법정동의 종합 안전점수(0~100), 신호등, 8축 세부점수"
                "(금융안전·건물노후·침수위험·치안·소방·교통·편의시설·환경), "
                "평균 전세가율과 최근 추세를 조회한다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "법정동명": {"type": "string", "description": "천안시 법정동명"},
                },
                "required": ["법정동명"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "news_search",
            "description": "천안 부동산·전세사기 관련 최신 뉴스를 검색한다. '최근/요즘/뉴스/이슈' 질문에 사용.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "짧은 뉴스 검색어 (예: '천안 전세사기')"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recommend",
            "description": (
                "예산·면적·우선순위 조건으로 안전한 동네와 실거래 기반 대표 매물을 추천한다. "
                "'추천해줘/어디가 좋아/예산 X로' 질문에 사용."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "budget": {"type": "number", "description": "보증금 예산 (만원)"},
                    "area_min": {"type": "number", "description": "최소 전용면적 (㎡)"},
                    "area_max": {"type": "number", "description": "최대 전용면적 (㎡)"},
                    "priority": {
                        "type": "string",
                        "enum": ["금융안전", "건물노후", "침수위험", "치안", "소방", "교통", "편의시설", "환경"],
                        "description": "우선 고려할 안전축",
                    },
                    "gu": {"type": "string", "enum": ["동남구", "서북구"], "description": "선호 구"},
                },
                "required": ["budget"],
            },
        },
    },
]

TOOL_NAMES = [t["function"]["name"] for t in TOOLS]
