"""
read_akruti.py

Read Akruti-encoded text files with proper encoding detection.

Akruti text uses latin-1 byte encoding. However, many text editors
(Notepad, VS Code, etc.) save files as UTF-8 by default. When an
Akruti file is saved as UTF-8, special bytes like 0xF0 (ð, the reph
marker) become 2-byte UTF-8 sequences (0xC3 0xB0). Reading such a
file as latin-1 corrupts these characters.

This module detects the correct encoding and reads Akruti files
reliably.
"""


def read_akruti_file(file_path) -> str:
    """
    Read an Akruti-encoded text file, detecting whether it was
    saved as UTF-8 or latin-1.

    Strategy:
        1. Read raw bytes.
        2. Try to decode as UTF-8 (strict).
        3. If successful, verify it's actually Akruti (not Unicode Odia)
           by checking for Akruti-specific characters.
        4. If UTF-8 fails, decode as latin-1.

    Returns:
        The file content as a Python string.

    Raises:
        OSError: If the file cannot be read.
    """
    raw = file_path.read_bytes()

    # Try UTF-8 first
    try:
        text = raw.decode("utf-8")

        # Verify this looks like Akruti, not Unicode Odia.
        # Akruti text should NOT contain Odia codepoints (U+0B00-U+0B7F).
        has_odia = any(0x0B00 <= ord(c) <= 0x0B7F for c in text)

        if not has_odia:
            # Looks like Akruti saved as UTF-8 — use it.
            return text

        # Contains Odia codepoints — this is likely a Unicode file
        # that the caller mistakenly sent to the Akruti converter.
        # Still return it as UTF-8 (best effort).
        return text

    except (UnicodeDecodeError, ValueError):
        pass

    # Fall back to latin-1 (always succeeds)
    return raw.decode("latin-1")
