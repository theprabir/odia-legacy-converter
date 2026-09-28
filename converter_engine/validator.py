"""
validator.py

Detects Unicode characters that escaped conversion.
"""

ODIA_START = 0x0B00
ODIA_END = 0x0B7F


def find_remaining_unicode(text: str):
    """
    Returns all remaining Odia Unicode characters.
    """

    remaining = []

    for ch in text:
        cp = ord(ch)

        if ODIA_START <= cp <= ODIA_END:
            remaining.append(ch)

    return remaining