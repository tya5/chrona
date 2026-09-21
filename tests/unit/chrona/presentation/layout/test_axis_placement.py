from datetime import date

from chrona.presentation.layout.axis import axis_label_fits, fitting_axis


class _Font:
    def width(self, content, size):
        return len(content) * size


def test_fitting_axis_and_axis_label_fit_are_layout_decisions():
    intervals = fitting_axis(requested="auto", start=date(2026, 1, 1), end=date(2026, 2, 1),
                             inline_size=310, font_size=10, font_metrics=_Font())
    assert intervals[0].level == "month"
    assert axis_label_fits(content="Jan", available_inline=30, font_size=10, font_metrics=_Font())
