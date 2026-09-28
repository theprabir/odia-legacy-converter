from .reorder import unicode_to_akruti
from .special_chars import fix_special_characters


def convert_text(text: str, fix_special_chars: bool = False):

    if not isinstance(text, str):
        raise TypeError(f"convert_text() expects str, got {type(text).__name__}")

    converted = unicode_to_akruti(text)

    if fix_special_chars:
        converted = fix_special_characters(converted)

    return converted