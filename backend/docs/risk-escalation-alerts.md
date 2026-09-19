# Risk Escalation Alerts

**Status:** Phase 1 (decision logic) implemented. Delivery is not built yet.
**Stream:** Back-end only.

## The gap

FireFusion shows the current risk picture, and (with forecast history) can
replay past ones. What it cannot do is *tell* anyone. A responder has to be
looking at the map at the moment risk rises in the area they care about.

This feature lets a subscriber define a region and a severity threshold, and
be notified when a new forecast makes that region worse.

## Boundaries: what this does not touch

This is built to add to the backend without changing anything other streams own.

- **Data Engineering.** No DE table is read, altered or referenced. A region is
  supplied by the subscriber, not derived from `Location_Registry` or any other
  DE data. Alerting never goes through the aggregator or its read-only DE role.
- **AI Modelling.** No change to the forecast contract. Alerting consumes the
  same `FeatureCollection` the API already serves.
- **Front-end.** No existing endpoint or response shape changes. Alerts are
  delivered out of band (webhook, email); the map is unaffected.
- **Existing back-end code.** Phase 1 adds a new package,
  `app/internal/alerting/`, and edits no existing file. It adds no dependency:
  polygon intersection is implemented in pure Python rather than adding a
  geometry library to `requirements.txt`.
- **Database (later phases).** Persistence will live in its own Postgres schema,
  `alerting`, created by a single migration file next to the forecast-history
  one. It adds no columns to existing tables and has no foreign keys into them,
  so `DROP SCHEMA alerting CASCADE` removes the feature entirely. This depends
  on `firefusion-api`'s database being backend-owned, which `forecast_history`
  already assumes; confirm that before the migration is applied anywhere shared.

## How a decision is made

For each rule (a region plus a threshold) and each new forecast:

1. **Assess the region.** Find the forecast polygons that touch the region. The
   region's risk is the *most severe* (lowest `risk_factor`) among them. The
   worst is used rather than an average on purpose: one extreme polygon inside
   the region is what a responder needs to hear about, however mild the rest is.
   `risk_factor` follows the Fire Risk Map convention: 1 is most severe, 5 least.
2. **Compare with the previous assessment** for the same region.
3. **Decide:**

| Previous | Now | Threshold met? | Result |
|---|---|---|---|
| below threshold, or no risk | at or beyond threshold | yes | `threshold_crossed` |
| at or beyond threshold | more severe | yes | `escalated` |
| at or beyond threshold | same | yes | nothing (already told) |
| any | less severe | - | nothing (easing is not alerted) |
| any | below threshold | no | nothing |

The threshold is inclusive: `threshold_risk_factor = 2` means "tell me at 2
(high) or 1 (extreme)".

**Design choices that lean toward alerting**, because a missed alert is worse
than an extra one for an emergency tool:

- A polygon that only touches the region's boundary counts as affecting it.
- With no previous assessment, a forecast already at or beyond the threshold
  alerts.

**Callers must pass only fresh forecasts.** Alerting on a stale forecast would
present old information as news. Freshness is already classified by
`meta.status` (see `fire-risk-map-graceful-degradation.md`).

## Known limitation: flapping

The detector is stateless, so risk oscillating around the threshold
(`4, 2, 4, 2`) alerts each time it crosses. Suppressing that needs stored state
(a cooldown per subscription), so it belongs to the delivery layer, not the
decision. A test documents the current behaviour so the gap is explicit.

## Phases

1. **Decision logic (done).** Region model, polygon intersection, region
   assessment, escalation decision. Pure, no I/O, fully unit-tested.
2. **Subscriptions.** A keyed API to create, list and delete subscriptions; the
   `alerting` schema; baselining a new subscription so it is not alerted about a
   risk that already existed when it was created.
3. **Wiring and delivery.** Evaluate subscriptions when a prediction is stored,
   best-effort so a failure here can never affect live forecast delivery (the
   same rule as the history write). Deliver through RabbitMQ workers with
   webhook and email channels, retries with backoff, a dead-letter queue,
   idempotency and a per-subscription cooldown.
4. **Audit.** Record each alert and its delivery outcome.

## Tests

`tests/test_risk_escalation.py` needs no database, broker or running stack. It
covers segment and polygon intersection (including concave shapes, holes,
touching edges and corners, and nesting), a randomized check of the geometry
against the analytic answer for rectangles, region and rule validation, region
assessment, and the full decision table. The tests were also checked by
deliberately breaking the code in six places (the nesting check, endpoint
touching, holes, the alert-on-unchanged rule, the threshold boundary, and
worst-versus-least-severe) to confirm each is caught.
