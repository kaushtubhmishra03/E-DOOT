import json
from pathlib import Path
from typing import Dict, Any

LOCALES_DIR = Path(__file__).resolve().parent.parent / "static" / "locales"
_TRANSLATIONS: Dict[str, Dict[str, str]] = {}


def load_translations() -> None:
    """Load JSON translation dictionaries into memory."""
    global _TRANSLATIONS
    for lang in ["en", "hi", "mr"]:
        file_path = LOCALES_DIR / f"{lang}.json"
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    _TRANSLATIONS[lang] = json.load(f)
            except Exception as e:
                print(f"[i18n] Error loading {lang}.json: {e}")
                _TRANSLATIONS[lang] = {}
        else:
            _TRANSLATIONS[lang] = {}


def t(key: str, lang: str = "en", default: str = "") -> str:
    """Retrieve translated string for a key in the given language with fallback to English."""
    if not _TRANSLATIONS:
        load_translations()
    lang_dict = _TRANSLATIONS.get(lang, {})
    if key in lang_dict:
        return lang_dict[key]
    en_dict = _TRANSLATIONS.get("en", {})
    return en_dict.get(key, default or key)
