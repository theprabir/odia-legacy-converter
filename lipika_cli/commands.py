"""Input parsing and slash-command registry (pure logic, no I/O)."""

from __future__ import annotations

from dataclasses import dataclass

HELP_TRIGGERS = frozenset({"h", "/h", "/help", "?"})
QUIT_COMMANDS = frozenset({"/quit", "/exit"})
MODE_COMMANDS = frozenset({"/u2a", "/a2u", "/u2s", "/s2u"})
KNOWN_COMMANDS = MODE_COMMANDS | QUIT_COMMANDS | {"/fix", "/copy", "/save", "/clear", "/help"}


@dataclass(frozen=True)
class Command:
    """A parsed command (first whitespace token starts with '/')."""

    name: str
    arg: str | None = None


@dataclass(frozen=True)
class Message:
    """Plain text to convert with the active mode."""


@dataclass(frozen=True)
class Help:
    """Short help requested via h / /h / /help / ?."""


@dataclass(frozen=True)
class Quit:
    """Exit requested via /quit or /exit."""


@dataclass(frozen=True)
class Ignore:
    """Empty/whitespace-only submit."""


@dataclass(frozen=True)
class Unknown:
    """Unknown slash command; nothing converted."""

    name: str


def parse(raw: str) -> Command | Message | Help | Quit | Ignore | Unknown:
    """Classify one submitted line/buffer. Pure function; no I/O."""
    text = raw.strip()
    if not text:
        return Ignore()
    if text in HELP_TRIGGERS:
        return Help()
    if text in QUIT_COMMANDS:
        return Quit()

    first, _, rest = text.partition(" ")
    if first.startswith("/"):
        arg = rest.strip() or None
        if first in KNOWN_COMMANDS:
            return Command(name=first, arg=arg)
        return Unknown(name=first)
    return Message()
