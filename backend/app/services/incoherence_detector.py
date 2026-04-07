"""Incoherence detection orchestrator for consolidated client profiles.

Thin facade that delegates to individual check functions in incoherence_checks
and aggregates/sorts the results.

All public check functions are re-exported for backward compatibility.
"""

from app.core.logging import get_logger
from app.domain.schemas.consolidation import (
    ConsolidatedClientProfile,
    ConsolidationAlert,
)

# Re-export all check functions for backward compatibility
from app.services.incoherence_checks import (  # noqa: F401
    detect_equipment_incoherences,
    detect_field_status_alerts,
    detect_optical_incoherences,
    detect_temporal_incoherences,
)
from app.services.incoherence_financial_checks import (  # noqa: F401
    detect_financial_incoherences,
    detect_identity_incoherences,
    detect_missing_data,
)

logger = get_logger("incoherence_detector")

# Backward-compatible alias for private function
_detect_field_status_alerts = detect_field_status_alerts


def detect_incoherences(
    profile: ConsolidatedClientProfile,
) -> list[ConsolidationAlert]:
    """Run all incoherence detection rules on a consolidated profile.

    Returns a list of alerts sorted by severity (error first, then warning, then info).
    """
    alerts: list[ConsolidationAlert] = []

    alerts.extend(detect_field_status_alerts(profile))
    alerts.extend(detect_temporal_incoherences(profile))
    alerts.extend(detect_optical_incoherences(profile))
    alerts.extend(detect_financial_incoherences(profile))
    alerts.extend(detect_identity_incoherences(profile))
    alerts.extend(detect_equipment_incoherences(profile))
    alerts.extend(detect_missing_data(profile))

    # Sort: errors first, then warnings, then info
    severity_order = {"error": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: severity_order.get(a.severity, 3))

    logger.info(
        "incoherence_detection_completed",
        total_alerts=len(alerts),
        errors=sum(1 for a in alerts if a.severity == "error"),
        warnings=sum(1 for a in alerts if a.severity == "warning"),
    )

    return alerts
