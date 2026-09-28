"""
Unicode Odia -> Sreelipi reordering + substitution.

Sreelipi's encoding is structurally different from Akruti's:

- Prebase e/ai/o/au matras are typed as a *marker byte* "{" placed
  BEFORE the base consonant cluster, optionally followed by an "extra"
  byte right after the cluster to distinguish ai/o/au from plain e:
      e:   "{" + cluster
      ai:  "{" + cluster + "ð"
      o:   "{" + cluster + "æ"   (æ is literally the aa-matra byte)
      au:  "{" + cluster + "ò"
  (Verified against the OdiaWikimedia Shreelipi->Unicode converter's own
  reorder regexes, which move "{" from before the cluster to after it --
  i.e. confirming "{" + cluster is the authentic raw typed order.)

- Reph ("ର୍" + cluster) is typed *after* the whole cluster+matras, using
  a dedicated byte "ö" placed at the very end of the syllable:
      cluster + matras + "ö"

Most other conjuncts/consonants are single, atomic Sreelipi bytes (no
cluster-building needed the way Akruti requires), so forward conversion
is mostly a straight substitution once prebase/reph are handled.
"""

import json
import re
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

with open(BASE_DIR / "unicode_to_sreelipi.json", encoding="utf-8") as f:
    UNICODE_TO_SREELIPI = json.load(f)


# ------------------------------------------------------------------
# Normalization
# ------------------------------------------------------------------

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("ଡ଼", "ଡ଼").replace("ଢ଼", "ଢ଼")
    return text


# ------------------------------------------------------------------
# Pre-base matras + reph
# ------------------------------------------------------------------

PREBASE_MARK = "{"
AI_EXTRA = "ð"
O_EXTRA = "æ"   # reuses the aa-matra byte, matching the real font
AU_EXTRA = "ò"
REPH_MARK = "ö"

BASE = r"[କ-ହଡ଼ଢ଼ୟରଲଳଵୱଡ଼ଢ଼]"
CLUSTER = BASE + r"(?:୍[କ-ହଡ଼ଢ଼ୟରଲଳଵୱଡ଼ଢ଼])*"  # includes ୱ ଡ଼ ଢ଼ (U+0B71/0B5C/0B5D, outside କ-ହ)

_RE_PREBASE_AI = re.compile(rf"({CLUSTER})ୈ")
_RE_PREBASE_O = re.compile(rf"({CLUSTER})ୋ")
_RE_PREBASE_AU = re.compile(rf"({CLUSTER})ୌ")
_RE_PREBASE_E = re.compile(rf"({CLUSTER})େ")
_RE_REPH = re.compile(rf"(?<!୍)ର୍({CLUSTER})([ାିୀୁୂୃେୈୋୌଂଁ]*)")


def move_prebase_matras(text: str) -> str:
    # Longer/composite matras first so a bare େ regex doesn't pre-empt them.
    text = _RE_PREBASE_AI.sub(rf"{PREBASE_MARK}\1{AI_EXTRA}", text)
    text = _RE_PREBASE_O.sub(rf"{PREBASE_MARK}\1{O_EXTRA}", text)
    text = _RE_PREBASE_AU.sub(rf"{PREBASE_MARK}\1{AU_EXTRA}", text)
    text = _RE_PREBASE_E.sub(rf"{PREBASE_MARK}\1", text)
    return text


def move_reph(text: str) -> str:
    return _RE_REPH.sub(rf"\1\2{REPH_MARK}", text)


# ------------------------------------------------------------------
# Longest-match substitution (dict + trie, mirrors the Akruti converter)
# ------------------------------------------------------------------

_SINGLE_CHAR = {k: v for k, v in UNICODE_TO_SREELIPI.items() if len(k) == 1}


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
                continue
            node = self.root
            for ch in key:
                node = node.children.setdefault(ch, _TrieNode())
            node.value = val


_MULTI_TRIE = _Trie(UNICODE_TO_SREELIPI)


def substitute(text: str) -> str:
    sc = _SINGLE_CHAR
    out = []
    i = 0
    n = len(text)
    root = _MULTI_TRIE.root

    while i < n:
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
            ch = text[i]
            val = sc.get(ch)
            out.append(val if val is not None else ch)
            i += 1

    return "".join(out)


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def unicode_to_sreelipi(text):
    if text is None:
        return ""

    if not isinstance(text, str):
        raise TypeError(f"unicode_to_sreelipi() expects str, got {type(text).__name__}")

    text = normalize(text)
    text = move_reph(text)
    text = move_prebase_matras(text)
    text = substitute(text)

    return text
