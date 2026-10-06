# CustomerVoice AI - Data Semantics & Provenance Specification

## Overview

This document specifies the operational semantics, provenance, and data classifications across all fields within the CustomerVoice AI data pipeline. Following the comprehensive Data Lineage and Semantic Validation Audit, all artificial and simulated business attributes have been removed to ensure zero data fabrication.

Every attribute in the platform is strictly classified into one of three tiers:
1. **Directly Observed Data**: Authentic raw values extracted directly from source datasets without alteration.
2. **Derived / Inferred Data**: Explicitly labeled analytical outputs produced by transparent NLP models or rule-based categorization.
3. **Unavailable Data**: Attributes that do not exist within the raw source datasets and are deliberately preserved as `NULL` / `None` rather than fabricated.

---

## Field Semantics & Provenance Matrix

| Field Name | Type | Classification | Source & Provenance | Description & Integrity Rules |
| :--- | :--- | :--- | :--- | :--- |
| `review_id` | String | Directly Observed / Deterministic ID | Generated during ingestion | Sequential, deterministic unique identifier (e.g. `REV_000001` - `REV_005000`). Used for stable cross-stage referencing. |
| `review_text` | String | Directly Observed | `archive (1)/test.ft.txt.bz2` & `archive/train_data.csv` | Genuine customer voice / social commentary text. Completely authentic and unaltered. |
| `cleaned_text` | String | Derived | Text Preprocessing Engine | Normalized review text (lowercased, punctuation standardized, whitespace normalized). |
| `rating` | Float | **Unavailable** (`NULL`) | None in raw datasets | Genuine 1–5 star customer rating. Because neither source dataset contains authentic customer star ratings, this field is strictly stored as `NULL` / `None`. |
| `sentiment_proxy_rating` | Float | Derived / Proxy | FastText sentiment label (`__label__1` $\to$ 1.0, `__label__2` $\to$ 5.0) | Secondary analytical proxy representing the binary polarity converted to star scale. **Must never be presented as an actual customer rating.** |
| `rating_source` | String | Directly Observed / Metadata | Ingestion Adapter | Explicit provenance metadata flag. Currently set to `"not_available"` for all 5,000 corpus records. |
| `review_date` | Date / String | **Unavailable** (`NULL`) | None in raw datasets | Genuine timestamp when review was authored. Neither source dataset contains parseable timestamps. Strictly stored as `NULL` / `None` (synthetic date offsets completely removed). |
| `product_id` | String | **Unavailable** (`NULL`) | None in raw datasets | Genuine Product SKU / ASIN identifier. Because the raw corpora lack individual SKU identifiers, this field is strictly `NULL` / `None`. |
| `product_name` | String | **Unavailable** (`NULL`) | None in raw datasets | Genuine commercial product title. Strictly `NULL` / `None`. |
| `category` | String | **Unavailable** (`NULL`) | None in raw datasets | Official e-commerce catalog taxonomy category. Strictly `NULL` / `None`. |
| `segment` | String | Inferred | Rule-based keyword classifier | Broad thematic category segment inferred from review text for Amazon reviews (e.g., `"Power & Battery"`, `"Audio & Sound"`, `"Video & Display"`). Strictly `NULL` for Twitter/Social records. Labeled as `inferred_category_segment`. |
| `campaign` | String | **Unavailable** (`NULL`) | None in raw datasets | Marketing or acquisition campaign identifier. Strictly `NULL` / `None` (no placeholder campaigns manufactured). |
| `source` | String | Directly Observed | File origin | Authentic platform origin: `"Amazon"` for FastText corpus (4,000 records) and `"Twitter/Social"` for Sentiment140 corpus (1,000 records). |
| `sentiment` | String | Derived | VADER Baseline Model | Classified sentiment polarity (`positive`, `neutral`, `negative`). |
| `sentiment_score` | Float | Derived | VADER Baseline Model | Normalized compound sentiment score between -1.0 and +1.0. |
| `topics` | String | Derived | Keyword Multi-Label Topic Detector | Comma-delimited list of detected customer complaint and feedback topics (e.g. `battery`, `customer_support`, `usability`). |
| `pii_detected` | Boolean | Derived | PII Redaction Engine | Flag indicating if email addresses, phone numbers, or credit card numbers were detected and masked. |

---

## Data Realignment & Integrity Commitments

1. **Zero Date Fabrication**:
   The trend engine and ingestion adapters do not generate modulo offsets or arbitrary dates (`2023-01-01 + i days`). When timestamps are unavailable, `review_date` is `NULL`. The trend engine reports `status = "insufficient_temporal_data"` and does not produce spurious time series trends.

2. **Zero Star Rating Fabrication**:
   FastText binary labels (`__label__1`, `__label__2`) indicate general polarity, not calibrated customer satisfaction ratings. Actual customer rating is preserved as `NULL`. The derived proxy is isolated to `sentiment_proxy_rating` with `rating_source = "not_available"`.

3. **No Social SKUs or Pseudo-Products**:
   Sentiment140 represents social media listening channels (`Twitter/Social`), never a product SKU. It has `product_id = NULL` and `segment = NULL`. Amazon reviews have `product_id = NULL` and are categorized only by `segment` (inferred grouping).

4. **Algorithmic Alert Demonstrations**:
   Alerts triggered in synthetic or demonstration conditions are explicitly marked with `alert_type = "DEMONSTRATION - ..."` and `message = "[Algorithmic Alert Demonstration] ..."`. When temporal data is absent, temporal alerts are skipped.
