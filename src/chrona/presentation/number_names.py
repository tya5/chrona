"""The existing Japanese digit/ten names, shared by ordinals and count text."""

KANJI_DIGITS = "〇一二三四五六七八九"
KANJI_FORMAL_DIGITS = "〇壱弐参肆伍陸漆捌玖"


def kanji_number(value: int, *, formal: bool = False) -> str:
    """Render0..99 using the shared names; callers own diagnostic/range policy."""
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 99:
        raise ValueError("kanji number outside0..99")
    digits, ten = (KANJI_FORMAL_DIGITS, "拾") if formal else (KANJI_DIGITS, "十")
    if value == 0:
        return digits[0]
    tens, ones = divmod(value, 10)
    prefix = "" if tens == 0 else ten if tens == 1 else digits[tens] + ten
    return prefix + (digits[ones] if ones else "")
