import json
import re
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

with open(BASE_DIR / "unicode_to_akruti.json", encoding="utf-8") as f:
    UNICODE_TO_AKRUTI = json.load(f)

# ------------------------------------------------------------------
# Normalization
# ------------------------------------------------------------------

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)

    text = (
        text
        .replace("ଡ଼", "ଡ଼")
        .replace("ଢ଼", "ଢ଼")
    )

    return text


# ------------------------------------------------------------------
# Pre-base matras
# ------------------------------------------------------------------

PREBASE = {
    "େ": "ù",
}

POSTBASE = {
    "ୈ": "÷",
    "ୋ": "û",
    "ୌ": "ø",
}

# କ-ହ covers U+0B15–U+0B39 (including ଯ ର ଲ ଳ ଵ). ଡ଼ ଢ଼ ୟ ୱ ଡ଼ ଢ଼
# (U+0B5C/0B5D/0B5F/0B71) sit outside that range and must be listed
# explicitly — ୱ especially, since ଦ୍ୱ ସ୍ୱ ହ୍ୱ etc. are common conjuncts
# and a prebase matra (େ ୈ ୋ ୌ) after them must still move to the front
# of the cluster (previously it leaked through unconverted, e.g.
# ଦ୍ୱେଷ → "\çେh" instead of "ù\çh").
BASE = r"[କ-ହଡ଼ଢ଼ୟରଲଳଵୱଡ଼ଢ଼]"

CLUSTER = (
    BASE +
    r"(?:୍[କ-ହଡ଼ଢ଼ୟରଲଳଵୱଡ଼ଢ଼])*"
)

# Pre-compile regexes at module load (major speedup)
_RE_PREBASE_E = re.compile(rf"({CLUSTER})େ")
_RE_PREBASE_AI = re.compile(rf"({CLUSTER})ୈ")
_RE_PREBASE_O = re.compile(rf"({CLUSTER})ୋ")
_RE_PREBASE_AU = re.compile(rf"({CLUSTER})ୌ")
_RE_REPH = re.compile(rf"(?<!୍)ର୍({CLUSTER})([ାିୀୁୂୃ]*)(େ|ୈ|ୋ|ୌ)?")


def move_prebase_matras(text):
    text = _RE_PREBASE_E.sub(r"ù\1", text)
    text = _RE_PREBASE_AI.sub(r"ù\1÷", text)
    text = _RE_PREBASE_O.sub(r"ù\1û", text)
    text = _RE_PREBASE_AU.sub(r"ù\1ø", text)
    return text


# ------------------------------------------------------------------
# Reph
# ------------------------------------------------------------------

def move_reph(text):
    # A reph'd cluster can be immediately followed by a PREBASE matra
    # (େ/ୈ/ୋ/ୌ). Those matras need the "ù" prebase marker placed BEFORE
    # the cluster, which move_prebase_matras() (running after this) can
    # no longer do once "ð" has been inserted right after the cluster —
    # it would sit between the cluster and the matra, breaking the
    # adjacency move_prebase_matras() depends on. So handle that case
    # here directly, while cluster and matra are still adjacent.
    def _replacer(m):
        cluster = m.group(1)
        postbase_matras = m.group(2) or ""
        prebase_matra = m.group(3)

        if prebase_matra == "େ":
            return f"ù{cluster}{postbase_matras}ð"
        if prebase_matra == "ୈ":
            return f"ù{cluster}{postbase_matras}÷ð"
        if prebase_matra == "ୋ":
            return f"ù{cluster}{postbase_matras}ûð"
        if prebase_matra == "ୌ":
            return f"ù{cluster}{postbase_matras}øð"

        return f"{cluster}ð{postbase_matras}"

    return _RE_REPH.sub(_replacer, text)


# ------------------------------------------------------------------
# Optimized longest-match substitution
# ------------------------------------------------------------------
#
# Strategy: split keys into single-char (dict lookup, O(1)) and
# multi-char (trie walk).  Most characters hit the fast dict path.

# Single-char mapping: direct dict lookup
_SINGLE_CHAR = {k: v for k, v in UNICODE_TO_AKRUTI.items() if len(k) == 1}

# Multi-char trie

class _TrieNode:
    __slots__ = ("children", "value")

    def __init__(self):
        self.children: dict[str, "_TrieNode"] = {}
        self.value: str | None = None


class _Trie:
    __slots__ = ("root",)

    def __init__(self, mapping: dict[str, str]):
        self.root = _TrieNode()
        for key, val in mapping.items():
            if len(key) <= 1:
                continue  # handled by _SINGLE_CHAR
            node = self.root
            for ch in key:
                if ch not in node.children:
                    node.children[ch] = _TrieNode()
                node = node.children[ch]
            node.value = val

    def replace(self, text: str, out: list) -> None:
        i = 0
        n = len(text)
        root = self.root

        while i < n:
            node = root
            last_val = None
            last_end = i
            j = i

            while j < n and text[j] in node.children:
                node = node.children[text[j]]
                j += 1
                if node.value is not None:
                    last_val = node.value
                    last_end = j

            if last_val is not None:
                out.append(last_val)
                i = last_end
            else:
                out.append(text[i])
                i += 1


_MULTI_TRIE = _Trie(UNICODE_TO_AKRUTI)


def substitute(text):
    # Always prefer the longest match (trie first, then single-char).
    # The trie handles multi-char keys; single-char is the fallback.
    sc = _SINGLE_CHAR
    out = []
    i = 0
    n = len(text)
    root = _MULTI_TRIE.root

    while i < n:
        # Try multi-char trie first (longest match wins)
        node = root
        last_val = None
        last_end = i
        j = i

        while j < n:
            child = node.children.get(text[j])
            if child is None:
                break
            node = child
            j += 1
            if node.value is not None:
                last_val = node.value
                last_end = j

        if last_val is not None:
            out.append(last_val)
            i = last_end
        else:
            # No multi-char match: try single-char
            ch = text[i]
            val = sc.get(ch)
            if val is not None:
                out.append(val)
            else:
                out.append(ch)
            i += 1

    return "".join(out)


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def unicode_to_akruti(text):

    if text is None:
        return ""

    if not isinstance(text, str):
        raise TypeError(f"unicode_to_akruti() expects str, got {type(text).__name__}")

    text = normalize(text)

    text = move_reph(text)

    text = move_prebase_matras(text)

    text = substitute(text)

    return text
