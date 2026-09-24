"""Converte nomes de modelo (ex: 'qwen2.5-coder:7b') em nomes de pasta seguros."""

from __future__ import annotations

import re


def slug(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", text.strip())
    return cleaned.strip("_") or "modelo"
