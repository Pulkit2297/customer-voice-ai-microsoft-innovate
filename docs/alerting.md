# Operational Alerting Architecture

## 1. Overview

**CustomerVoice AI** provides automated, real-time alert generation to proactively surface emerging product defects, logistics failures, customer support bottlenecks, and model accuracy decay. The alerting subsystem evaluates operational metrics against externalized, configurable thresholds rather than embedding hardcoded constants inside business logic.

---

## 2. Configurable Alert Thresholds

Threshold parameters are managed via [`src/alerts/alert_config.py`](file:///d:/Mission%20Internship%20and%20Placement/Microsoft%20Innovate/customer-voice-ai/src/alerts/alert_config.py) and can be overridden dynamically at runtime through environment variables in `.env`:

| Alert Type | Monitored Metric | Default Trigger Threshold | Environment Variable Override |
| :--- | :--- | :--- | :--- |
| `NEGATIVE_SENTIMENT_SURGE` | `negative_sentiment_pct` | $\ge 20.0\%$ increase | `ALERT_NEGATIVE_SENTIMENT_INCREASE_PCT` |
| `TOPIC_VOLUME_SURGE` | `topic_volume` | $\ge 30.0\%$ volume increase | `ALERT_TOPIC_VOLUME_INCREASE_PCT` |
| `RATING_DROP` | `average_rating` | $\ge 0.5$ star drop | `ALERT_RATING_DECREASE_ABSOLUTE` |
| `MODEL_F1_DECAY` | `model_f1_score` | $\ge 0.10$ F1 score decay | `ALERT_MODEL_F1_DECREASE_ABSOLUTE` |

---

## 3. Severity Classification Matrix

Alerts are categorized into three distinct operational severity levels:

- **LOW**: Minor statistical variance or early-warning notice without immediate business impact.
- **MEDIUM**: Standard threshold breach requiring triage within 24 hours by domain stakeholders.
- **HIGH**: Critical operational disruption (e.g. negative sentiment surge $\ge 40\%$, rating drop $\ge 1.0$, or F1 collapse $\ge 0.20$) requiring immediate escalation.

---

## 4. Standardized Alert Schema

Every alert emitted by `AlertEngine` adheres to the standardized contract:

```json
{
  "alert_id": "ALT_4A81B3C0",
  "alert_type": "NEGATIVE_SENTIMENT_SURGE",
  "severity": "HIGH",
  "product": "Kindle Paperwhite",
  "topic": "battery",
  "metric": "negative_sentiment_pct",
  "previous_value": 18.5,
  "current_value": 62.0,
  "percentage_change": 235.14,
  "message": "Negative sentiment surged from 18.5% to 62.0% (+235.1% shift) for product='Kindle Paperwhite', topic='battery'.",
  "created_at": "2026-09-27T10:04:12.184912+00:00",
  "status": "ACTIVE"
}
```

### Schema Definitions:
- `alert_id`: Unique identifier formatted as `ALT_<HEX>` for tracking and auditability.
- `alert_type`: Functional category (`NEGATIVE_SENTIMENT_SURGE`, `TOPIC_VOLUME_SURGE`, `RATING_DROP`, `MODEL_F1_DECAY`).
- `severity`: Operational priority (`LOW`, `MEDIUM`, `HIGH`).
- `product`: The affected product name or SKU (or `"all"`).
- `topic`: The affected taxonomy topic (or `"all"`).
- `metric`: The specific numerical metric being measured.
- `previous_value` / `current_value`: Chronological baseline and observed values.
- `percentage_change`: Calculated percentage shift.
- `message`: Human-readable summary tailored for notification cards and BI tooltips.
- `created_at`: ISO-8601 UTC timestamp of detection.
- `status`: Lifecycle state (`ACTIVE`, `ACKNOWLEDGED`, `RESOLVED`).

---

## 5. Storage & Visual Layer Integration

- **CSV Persistence**: All alerts are written to [`data/processed/alerts.csv`](file:///d:/Mission%20Internship%20and%20Placement/Microsoft%20Innovate/customer-voice-ai/data/processed/alerts.csv).
- **Power BI Notification Feed**: The alerts dataset connects directly into Power BI dashboards as a dedicated KPI alert card feed with conditional red/yellow/green badge indicators.
- **Webhook Extensibility**: The modular `Alert` object easily serializes to JSON for webhook routing to Microsoft Teams, Slack channels, or PagerDuty incident queues.
