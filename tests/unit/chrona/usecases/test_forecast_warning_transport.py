from chrona.core.diagnostics import Diagnostic
from chrona.usecases.diagnostic_messages import collapse_warnings
from chrona.usecases.warning_ledger import collect_render_warnings


def test_observed_start_forecast_warning_keeps_producer_message_and_scene_identity():
    details = {
        "object": "visual-design", "endpoint": "start", "placed": "2026-11-09",
        "relation": "wireframes-visual-design",
        "from": {"object": "wireframes", "endpoint": "end", "value": "2026-11-10"},
        "lag": "0d", "required": "2026-11-10", "earliest": "2026-11-10",
        "forcedBy": "wireframes-visual-design", "beforeBoundDays": 1,
        "overlapDays": 1, "sourceDateBasis": "observed",
    }
    message = ("Work on visual-design started on 2026-11-09, 1 calendar day(s) before predecessor "
               "wireframes's observed finish on 2026-11-10; relation "
               "wireframes-visual-design requires 2026-11-10 after lag 0d. The observed start is retained.")
    warning = Diagnostic("W_FORECAST_OBSERVED_START_BEFORE_BOUND", message,
                         "/relations/wireframes-visual-design", details=details)
    records = collect_render_warnings(
        surface_diagnostics=(), tabular_warnings=(), glyph_warnings=(), fit_warnings=(),
        perceptibility_warnings=(), scale_collisions=(), attachment_warnings=(),
        forecast_warnings=(warning,),
    )

    record, = records
    assert record.identity == (
        'W_FORECAST_OBSERVED_START_BEFORE_BOUND:{"endpoint":"start","object":"visual-design",'
        '"relation":"wireframes-visual-design"}'
    )
    assert record.payload["diagnostic"] == record.identity
    assert record.payload["severity"] == "warning"
    assert record.payload["details"] == details
    assert record.payload["message"] == message
    collapsed, = collapse_warnings((record.payload,))
    assert collapsed["diagnostic"] == record.identity
    assert collapsed["severity"] == "warning"
    assert collapsed["message"] == message
