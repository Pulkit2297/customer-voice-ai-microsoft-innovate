"""CLI script for generating operational and performance alerts.

Usage:
    python scripts/generate_alerts.py [--trends <CSV>] [--metrics <CSV>] [--output <CSV>]

Default Input:
    trends:  data/processed/trends.csv
    metrics: data/processed/model_metrics.csv
Default Output:
    data/processed/alerts.csv
"""

import argparse
from collections import Counter
import logging
from pathlib import Path
import sys
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.alerts.alert_engine import AlertEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("generate_alerts")


def run_alert_generation(
    trends_path: str,
    metrics_path: str,
    output_path: str,
    is_demonstration: bool = False,
) -> None:
    """Run alert detection across operational trends and model benchmark metrics."""
    trends_file = Path(trends_path).resolve()
    metrics_file = Path(metrics_path).resolve()
    out_file = Path(output_path).resolve()

    # Safeguard against raw dataset modification
    raw_dir = (PROJECT_ROOT / "data" / "raw").resolve()
    try:
        out_file.relative_to(raw_dir)
        logger.error(
            "Security Error: Output destination '%s' cannot be within data/raw/.",
            out_file,
        )
        sys.exit(1)
    except ValueError:
        pass

    logger.info("=" * 65)
    logger.info("CustomerVoice AI - Complaint & Operational Alert Generator")
    logger.info("=" * 65)
    logger.info("Trends file:        %s", trends_file)
    logger.info("Metrics file:       %s", metrics_file)
    logger.info("Alerts output:      %s", out_file)
    logger.info("Demonstration mode: %s", is_demonstration)

    trends_df = None
    if trends_file.is_file():
        try:
            trends_df = pd.read_csv(trends_file)
            logger.info("Loaded %d records from trends dataset.", len(trends_df))
        except Exception as e:
            logger.warning("Could not load trends dataset: %s", e)

    metrics_df = None
    if metrics_file.is_file():
        try:
            metrics_df = pd.read_csv(metrics_file)
            logger.info("Loaded %d records from model metrics dataset.", len(metrics_df))
        except Exception as e:
            logger.warning("Could not load model metrics dataset: %s", e)

    engine = AlertEngine(is_demonstration=is_demonstration)
    alerts = engine.evaluate_all(
        trends_df=trends_df,
        model_metrics_df=metrics_df,
        is_demonstration=is_demonstration,
    )

    alert_columns = [
        "alert_id",
        "alert_type",
        "severity",
        "product",
        "topic",
        "metric",
        "previous_value",
        "current_value",
        "percentage_change",
        "message",
        "created_at",
        "status",
    ]

    if alerts:
        alerts_df = pd.DataFrame([a.to_dict() for a in alerts])
    else:
        alerts_df = pd.DataFrame(columns=alert_columns)

    # Ensure parent output directory exists
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Save to data/processed/alerts.csv
    alerts_df.to_csv(out_file, index=False)
    logger.info("Saved %d generated alerts to: %s", len(alerts_df), out_file)

    # Summary
    severity_counts = Counter(alerts_df["severity"])
    type_counts = Counter(alerts_df["alert_type"])

    logger.info("-" * 65)
    logger.info("Alert Generation Summary:")
    logger.info("  Total Alerts Created: %d", len(alerts_df))
    logger.info("  Severity Breakdown:")
    for sev in ["HIGH", "MEDIUM", "LOW"]:
        logger.info("    - %-6s: %3d", sev, severity_counts.get(sev, 0))
    logger.info("  Alert Types Breakdown:")
    for a_type, count in type_counts.items():
        logger.info("    - %-28s: %3d", a_type, count)
    logger.info("=" * 65)


def main():
    parser = argparse.ArgumentParser(
        description="Generate CustomerVoice AI alerts."
    )
    parser.add_argument(
        "--trends",
        "-t",
        type=str,
        default=str(PROJECT_ROOT / "data" / "processed" / "trends.csv"),
        help="Path to trends CSV (default: data/processed/trends.csv)",
    )
    parser.add_argument(
        "--metrics",
        "-m",
        type=str,
        default=str(PROJECT_ROOT / "data" / "processed" / "model_metrics.csv"),
        help="Path to model metrics CSV (default: data/processed/model_metrics.csv)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=str(PROJECT_ROOT / "data" / "processed" / "alerts.csv"),
        help="Path for output alerts CSV (default: data/processed/alerts.csv)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in demonstration mode (labels alerts as Algorithmic Alert Demonstration)",
    )

    args = parser.parse_args()
    run_alert_generation(args.trends, args.metrics, args.output, is_demonstration=args.demo)


if __name__ == "__main__":
    main()
