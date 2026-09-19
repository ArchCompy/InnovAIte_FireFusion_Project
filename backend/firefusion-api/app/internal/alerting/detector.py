from .models import AlertDecision, AlertKind, AlertRule, RegionAssessment


def evaluate(
    previous: RegionAssessment | None,
    current: RegionAssessment,
    rule: AlertRule,
) -> AlertDecision | None:
    """Decide whether a new forecast should raise an alert for a rule.

    Alerts fire on getting worse, not on being bad: a region that stays at the
    same severity produces nothing, and easing produces nothing. A missing
    previous assessment is treated as "no known risk", so a first forecast that
    is already at or beyond the threshold does alert. Erring toward an alert is
    the safe direction for an emergency tool.

    Callers should only pass forecasts that are fresh. Alerting on a stale
    forecast would present old information as news.
    """
    now = current.risk_factor
    if now is None or now > rule.threshold_risk_factor:
        return None

    before = previous.risk_factor if previous is not None else None
    was_at_or_beyond = before is not None and before <= rule.threshold_risk_factor

    if not was_at_or_beyond:
        kind = AlertKind.THRESHOLD_CROSSED
    elif now < before:
        kind = AlertKind.ESCALATED
    else:
        return None

    return AlertDecision(
        kind=kind,
        previous_risk_factor=before,
        current_risk_factor=now,
        feature_count=current.feature_count,
        max_fire_probability=current.max_fire_probability,
    )
