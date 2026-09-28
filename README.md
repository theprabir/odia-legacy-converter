# 🔄 Lipika — Unicode ⇄ Akruti/Sreelipi Converter

**Created by Prabir Kumar Das** · [github.com/theprabir/odia-legacy-converter](https://github.com/theprabir/odia-legacy-converter)

A terminal tool for converting **Odia text** between Unicode and the legacy
**Akruti** and **Sreelipi** fonts — as an interactive chat-style shell or as
quick one-shot commands.

> ✨ Interactive shell · ⚡ One-shot CLI · 📋 Clipboard support · 💾 Font-safe file saving

---

## 📦 Install

Requires **Python 3.10+**.

```bash
# from a clone of this repository
pip install .

# or with a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux
pip install .
```

You now have the `lipika` command (and `python -m lipika_cli` as an alias).

---

## 🚀 Quick start

```bash
lipika            # 🖥️  opens the interactive shell
lipika u2a "ନମସ୍କାର"   # ⚡ one-shot: Unicode → Akruti
```

---

## 💬 Interactive shell

Run `lipika` with no arguments. You get:

- 🎨 a large gradient banner with the title, author and project link
- ⌨️  a multiline chatbox: **Enter** converts, **Ctrl+J** inserts a newline
- 📌 a bottom toolbar showing the active mode, the fix flag, and key hints
- 🔁 **sticky modes** — pick a mode once, every message uses it

| Command | Does |
|---|---|
| `/u2a` | Unicode → Akruti *(default at startup)* |
| `/a2u` | Akruti → Unicode |
| `/u2s` | Unicode → Sreelipi |
| `/s2u` | Sreelipi → Unicode |
| `/fix` | toggle the Windows glyph fix (see below) |
| `/copy` | copy the last result to the clipboard 📋 |
| `/save [file]` | write the last result to a file with the correct encoding 💾 |
| `/clear` | clear the screen and redraw the banner |
| `h`, `/help`, `?` | short help |
| `/quit`, `/exit`, `Ctrl+D` | leave the shell |

Keys: **Enter** convert · **Ctrl+J** newline · **Ctrl+C** clear the input ·
**Ctrl+D** exit.

---

## ⚡ Non-interactive commands

Four subcommands mirror the modes. Each takes text, a file, or a pipe:

```bash
lipika u2a "ନମସ୍କାର"                # text argument
lipika a2u -f legacy.txt            # 📄 convert a legacy Akruti file
lipika u2s -f chapter.odt.txt -o out.txt   # 📤 write result to a file
cat legacy.txt | lipika s2u         # 🔗 pipe stdin in
```

| Option | Meaning |
|---|---|
| `-f, --file FILE` | read input from a file |
| `-o, --out FILE` | write the result to a file instead of stdout |
| `--fixed` | apply the Windows glyph fix (only meaningful for `u2a`) |
| `--encoding NAME` | override the output encoding for `-o` |
| `--debug` | show full tracebacks instead of one-line errors |
| `--version` | print the version |

Input files are decoded smartly: UTF-8 first, falling back to legacy
`cp1252` decoding for saved Akruti/Sreelipi files.

---

## 🔤 Encoding notes (important!)

Legacy Akruti/Sreelipi text is **single-byte font text**: the characters are
codes that only *look* right when displayed with the matching font.

- 🖥️ **In the terminal, legacy output looks garbled — that is expected.**
  Use `/save` or `/copy`, then apply the Akruti/Sreelipi font in your
  word processor.
- 💾 Files are written with the encoding the font expects:
  Akruti → `cp1252`, Sreelipi → `cp1252`, Unicode results → UTF-8,
  Akruti with `--fixed` → `latin-1`.
- ❓ If a character cannot be encoded, `lipika` **warns and asks** before
  substituting `?` — it never replaces silently.
- 🛠️ `--fixed` (or `/fix`) replaces a few Akruti conjunct glyphs (`ତ୍ତ`, `ଣ୍ଟ`,
  `ଞ୍ଚ`, `ତ୍ଥ`) with C1 control bytes that the same fonts render correctly on
  Windows 7/XP — use it when a modern Windows machine shows blank boxes for
  those conjuncts.

---

## ⚠️ Known limitations

- Legacy output **looks garbled in any terminal** by design — the fonts do
  the rendering, the terminal can't.
- ASCII input is *converted* by the engine (typewriter → Odia mapping), so
  ASCII text does not survive a Unicode → Akruti → Unicode round trip.
- Odia letter `ଵ` (WA) has no reverse mapping and comes back as `ବ`.
- Nukta letters (`କ଼`, `ଡ଼` …) keep their nukta as a Unicode combining mark;
  files mixing them with legacy bytes are not byte-safe.
- Fixed-mode output containing *both* a C1 glyph and a high cp1252 glyph has
  no single lossless 8-bit encoding; the CLI warns and substitutes `?`.
- Clipboard managers may strip C1 control bytes; prefer `/save` for
  fixed-mode output.

---

## 🧪 Development

```bash
pip install -r requirements.txt
pytest -q          # 505 tests, real engine, no mocks
ruff check .       # lint + import sorting
```

The conversion engine lives in `converter_engine/` and is treated as
read-only; all wrapper code is in `lipika_cli/`.

## 📄 License

[MIT](LICENSE) © Prabir Kumar Das
