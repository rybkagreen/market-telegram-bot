"""Telegram message size constants and ad_text truncate helper.

Constants reflect Telegram Bot API limits and are not configurable.
The truncate helper preserves word boundaries with a trailing ellipsis.

Used by ``PublicationService._build_marked_text`` for caption budget
enforcement on media posts (BL-080 8d).
"""

TELEGRAM_CAPTION_LIMIT = 1024
"""Max chars for sendPhoto / sendVideo / sendDocument / sendAudio /
sendAnimation captions and sendMediaGroup item captions.
"""

TELEGRAM_MESSAGE_LIMIT = 4096
"""Max chars for sendMessage text field."""


def truncate_ad_text(text: str, max_chars: int) -> str:
    """Truncate text к max_chars chars, respecting word boundaries.

    Behavior:
      * ``len(text) <= max_chars`` — return text unchanged.
      * Otherwise — cut at the last whitespace within (max_chars - 1) and
        append ``"…"``. If no whitespace fits, do a hard cut at
        (max_chars - 1) + ``"…"``.
      * Empty / non-positive budget — return empty string.

    Args:
        text: Source text to truncate.
        max_chars: Maximum allowed result length, ellipsis included.

    Returns:
        Truncated string of length at most ``max_chars``.
    """
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text

    # Reserve 1 codepoint for ellipsis "…"
    cutoff = max_chars - 1
    if cutoff <= 0:
        return "…"

    head = text[:cutoff]
    last_space = max(head.rfind(" "), head.rfind("\n"), head.rfind("\t"))

    if last_space > 0:
        return text[:last_space].rstrip() + "…"
    return text[:cutoff] + "…"
