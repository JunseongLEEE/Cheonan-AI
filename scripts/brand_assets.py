#!/usr/bin/env python3
"""천안시 공식 브랜드 에셋 로더 — 나랑이 마스코트·심벌마크.

원본 위치(사용자 배치): /root/Cheonan-AI/심벌마크, /root/Cheonan-AI/애국소녀 나랑이(2D, 이모티콘)
파일이 존재하면 base64 data URI로 반환(오프라인 시연 철칙), 없으면 None → 화면은 조용히 생략.
"""

from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MASCOT_DIRS = [ROOT / "애국소녀 나랑이(2D, 이모티콘)", ROOT / "presentation" / "assets" / "brand"]
SYMBOL_DIRS = [ROOT / "심벌마크", ROOT / "presentation" / "assets" / "brand"]
EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif")


def _first_image(dirs: list[Path], prefer_keywords: tuple[str, ...] = ()) -> Path | None:
    candidates: list[Path] = []
    for d in dirs:
        if d.is_dir():
            candidates += sorted(p for p in d.iterdir() if p.suffix.lower() in EXTS)
    if not candidates:
        return None
    for kw in prefer_keywords:
        for p in candidates:
            if kw in p.name:
                return p
    return candidates[0]


def _to_data_uri(p: Path) -> str:
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "webp": "image/webp", "gif": "image/gif"}[p.suffix.lower().lstrip(".")]
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


@lru_cache(maxsize=8)
def mascot_uri(pose: str = "기본") -> str | None:
    """나랑이 이미지 data URI. pose 키워드(파일명 매칭)로 포즈 선택."""
    prefer = {
        "기본": ("3D_엄지척", "엄지", "3D"),      # 히어로 — 3D 엄지척
        "안내": ("2D_기본", "2D"),               # 아바타 — 2D 단일 컷
        "놀람": ("놀", "깜짝"),
        "응원": ("화이팅", "응원"),
    }.get(pose, (pose,))
    p = _first_image(MASCOT_DIRS, prefer)
    return _to_data_uri(p) if p else None


@lru_cache(maxsize=2)
def symbol_uri() -> str | None:
    """천안시 심벌마크 data URI."""
    p = _first_image(SYMBOL_DIRS, ("심벌", "symbol", "CI", "ci", "마크"))
    return _to_data_uri(p) if p else None
