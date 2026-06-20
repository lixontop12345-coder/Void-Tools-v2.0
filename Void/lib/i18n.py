"""Void-Tools — FR/EN helpers."""
from .config import get_settings


def is_fr() -> bool:
    return get_settings().lang == "fr"


def t(fr: str, en: str) -> str:
    return fr if is_fr() else en


def reload_settings() -> None:
    get_settings().reload()
