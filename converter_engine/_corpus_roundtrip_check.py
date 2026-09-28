"""
Round-trip the 372,929-char Odia test corpus through Sreelipi:

    Unicode -> Sreelipi -> Unicode

and report exactly what fails: remaining Odia Unicode chars in the
intermediate (forward) output, and byte-level diffs between the input
and the round-tripped output.
"""
import io
import sys
from collections import Counter

from converter_engine.sreelipi_reorder import unicode_to_sreelipi
from converter_engine.sreelipi_reverse_converter import convert_sreelipi_to_unicode
from converter_engine.validator import find_remaining_unicode

CORPUS = r"C:/Users/ADMIN/Downloads/odia_50k_test_corpus.txt"


def main():
    with io.open(CORPUS, encoding="utf-8") as f:
        text = f.read()

    print(f"corpus chars: {len(text)}")

    # ---- forward: Unicode -> Sreelipi ----
    fwd = unicode_to_sreelipi(text)
    leaked = find_remaining_unicode(fwd)
    print(f"forward: {len(fwd)} chars; leaked Odia Unicode chars: {len(leaked)}")

    if leaked:
        c = Counter(leaked)
        for ch, n in c.most_common(40):
            print(f"  leak {ch!r} x{n}")

    # ---- round trip: Sreelipi -> Unicode ----
    rt = convert_sreelipi_to_unicode(fwd)
    print(f"roundtrip: {len(rt)} chars; byte-identical: {rt == text}")

    if rt != text:
        # find first diffs
        n = min(len(rt), len(text))
        diffs = 0
        for i in range(n):
            if rt[i] != text[i]:
                if diffs < 20:
                    print(f"  diff@{i}: input {text[i:i+6]!r} -> roundtrip {rt[i:i+6]!r}")
                diffs += 1
        if diffs < 20:
            for i in range(n, max(len(rt), len(text))):
                if diffs < 20:
                    print(f"  diff@{i}: tail")
                diffs += 1
        print(f"total differing positions: {diffs}")

    # unique mismatching words (whitespace-delimited)
    if rt != text:
        src_words = text.split()
        rt_words = rt.split()
        bad = [(w1, w2) for w1, w2 in zip(src_words, rt_words) if w1 != w2]
        print(f"mismatched word pairs: {len(bad)} (of {len(src_words)})")
        c2 = Counter((w1, w2) for w1, w2 in bad)
        for (w1, w2), n in c2.most_common(25):
            print(f"  {w1!r} -> {w2!r}  x{n}")
        # also report leaked-char words from forward pass
    return 0


if __name__ == "__main__":
    sys.exit(main())