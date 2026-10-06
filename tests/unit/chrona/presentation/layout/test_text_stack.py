from decimal import Decimal

from chrona.presentation.layout.sources import MeasuredTextRun
from chrona.presentation.layout.text_stack import measure_text_stack


def _run(role, *, size, block_size, baseline):
    return MeasuredTextRun(
        source_ref=role,
        content=role,
        typography_role=role,
        inline_size=Decimal(10),
        block_size=Decimal(block_size),
        baseline=Decimal(baseline),
        font_family="Test Sans",
        font_weight=400,
        font_size=float(size),
        line_height=float(block_size) / float(size),
        font_asset_identity="sha256:test",
    )


def test_mixed_role_stack_closes_baselines_and_actual_run_envelope():
    runs = (
        _run("caption", size=10, block_size=15, baseline=7),
        _run("figure", size=20, block_size=27, baseline=28),
        _run("unit", size=8, block_size=9, baseline=2),
    )
    measured = measure_text_stack(runs, (Decimal(3), Decimal(4), Decimal(0)))

    assert measured.baselines == (Decimal(10), Decimal(49), Decimal(68))
    assert measured.block_size == Decimal(69)
    bounds = tuple(
        (baseline - Decimal(str(run.font_size)),
         baseline - Decimal(str(run.font_size)) + run.block_size)
        for run, baseline in zip(runs, measured.baselines)
    )
    assert min(top for top, _ in bounds) == 0
    assert max(bottom for _, bottom in bounds) == measured.block_size
    assert bounds[1][0] - bounds[0][1] >= Decimal(3)
    assert bounds[2][0] - bounds[1][1] == Decimal(4)
    assert measured.baselines[0] == Decimal(10)
    assert measured.baselines[-1] == Decimal(68)


def test_last_run_gap_does_not_add_phantom_block_extent():
    runs = (
        _run("caption", size=10, block_size=15, baseline=7),
        _run("figure", size=20, block_size=27, baseline=28),
        _run("unit", size=8, block_size=9, baseline=2),
    )

    no_trailing_gap = measure_text_stack(runs, (Decimal(3), Decimal(4), Decimal(0)))
    large_trailing_gap = measure_text_stack(runs, (Decimal(3), Decimal(4), Decimal(1000)))

    assert large_trailing_gap == no_trailing_gap
