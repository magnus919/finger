"""
Terminal markdown rendering for finger output.

Renders markdown to terminal with formatting reminiscent of the `links` browser:
  - **bold** → bold (ANSI escape)
  - *italic* → italic  
  - `code` → inverted/bright background
  - [links](url) → underlined and colored
  - Plain mode strips all formatting
"""

import re
import sys


def render(text: str, plain: bool = False) -> str:
    """Render markdown text for terminal output.

    If plain is True, strip all formatting and return plain text.
    """
    if plain:
        return _strip_markdown(text)

    if not sys.stdout.isatty():
        return _strip_markdown(text)

    return _render_ansi(text)


def _strip_markdown(text: str) -> str:
    """Remove markdown formatting, return plain text."""
    # Remove link markup: [text](url) → text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove bold/italic markers
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", text)
    # Remove inline code backticks
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text


def _render_ansi(text: str) -> str:
    """Render markdown with ANSI escape codes."""
    # Bold: **text** → bright white
    text = re.sub(r"\*\*([^*]+)\*\*", _ansi_bold, text)

    # Italic: *text* → dim/italic
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", _ansi_italic, text)

    # Inline code: `text` → inverted
    text = re.sub(r"`([^`]+)`", _ansi_code, text)

    # Links: [text](url) → underlined blue text
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _ansi_link, text)

    return text


def _ansi_bold(m):
    return f"\033[1m{m.group(1)}\033[22m"


def _ansi_italic(m):
    return f"\033[3m{m.group(1)}\033[23m"


def _ansi_code(m):
    return f"\033[7m{m.group(1)}\033[27m"


def _ansi_link(m):
    return f"\033[4m\033[34m{m.group(1)}\033[24m\033[39m"
