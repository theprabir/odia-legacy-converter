from .sreelipi_reorder import unicode_to_sreelipi


def convert_text_sreelipi(text: str):

    if not isinstance(text, str):
        raise TypeError(f"convert_text_sreelipi() expects str, got {type(text).__name__}")

    return unicode_to_sreelipi(text)
