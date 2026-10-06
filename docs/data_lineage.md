# Data Lineage and Semantic Validation Audit Report

## 1. Executive Summary & Audit Mandate

This document provides a comprehensive **Data Lineage and Semantic Validation Audit** for the active 5,000-record dataset processed in CustomerVoice AI.

> [!CAUTION]
> **Audit Finding: NOT PRODUCTION-READY FOR COMMERCIAL BUSINESS DECISION-MAKING**
> While the text processing, PII scrubbing, sentiment engine, and taxonomy-driven topic classification run authentically on real human text, **key business dimensions (timestamps, continuous star ratings, marketing campaigns, and specific product SKU identifiers) were inferred, defaulted, or synthetically generated** in the ingestion adapters to allow pipeline simulation. They must not be presented to executive stakeholders as verified historical business metrics.

---

## 2. Ingestion Source Record Counts

| Source Dataset Name | File Path | Ingested Records | True Modality |
| :--- | :--- | :--- | :--- |
| **Amazon FastText Corpus** | `archive (1)/test.ft.txt.bz2` | **4,000** | E-commerce product review titles and bodies with binary sentiment labels (`__label__1` = negative, `__label__2` = positive) |
| **Sentiment140 Corpus** | `archive/train_data.csv` | **1,000** | Microblogging / Twitter short status updates with binary sentiment (`0` = negative, `1` = positive) |
| **Total Ingested Corpus** | `data/raw/reviews_multi_source.csv` | **5,000** | Multi-source feedback corpus |

---

## 3. Field-by-Field Lineage and Derivation Audit

Every field across the 5,000 records has been traced back to its raw origins:

| Field Name | Raw Source File | Source Column | Transformation Performed | Derivation Classification | Records Affected |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`review_id`** | Ingestion pipeline | *None* | Assigned sequential identifier `REV_000001` to `REV_005000` | **Generated / Defaulted** | 5,000 (100%) |
| **`review_text`** | Both archives | Amazon: `<Title>: <Body>`<br>Twitter: `sentence` | HTML unescaping, tag stripping, typographic quote replacement, whitespace normalization. Punctuation and negations preserved. | **Directly Observed** | 5,000 (100%) |
| **`rating`** | Both archives | Amazon: `__label__<1\|2>`<br>Twitter: `sentiment` (0/1) | Binary classification mapped to discrete numeric proxies: `1.0` (for negative) and `5.0` (for positive). No intermediate ratings exist. | **Inferred from Binary Sentiment** | 5,000 (100%) |
| **`review_date`** | Ingestion pipeline | *None* | Synthetic timestamps injected via base date `2023-01-01 + (count % 180)` days. | **Synthesized** | 5,000 (100%) |
| **`product_id`** | Both archives | *None* | Keyword regex matching clustered Amazon reviews into 6 category segments; Twitter data assigned `PROD_SOCIAL_MENTIONS`. | **Inferred Category Segment** | 5,000 (100%) |
| **`product_name`** | Ingestion pipeline | *None* | Human-friendly descriptive names mapped to the 7 category segments. | **Defaulted** | 5,000 (100%) |
| **`category`** | Ingestion pipeline | *None* | Department labels mapped to the 7 category segments. | **Inferred Category Segment** | 5,000 (100%) |
| **`campaign`** | Ingestion pipeline | *None* | Hardcoded placeholder strings (`"Amazon_Organic_Review"` and `"Social_Feedback_Monitoring"`). | **Defaulted** | 5,000 (100%) |
| **`source`** | Ingestion pipeline | File origin | Tagged as `"Amazon"` (4,000) or `"Twitter/Social"` (1,000). | **Inferred from Origin File** | 5,000 (100%) |

---

## 4. Specific Verification Items

### 4.1 Are the 7 reported "products" actual product IDs or generated category segments?
- **Finding**: They are **generated category segments, NOT genuine product SKU/ASIN identifiers**.
- **Evidence**:
  - The raw FastText Amazon corpus contains only text and labels; it lacks ASINs, model numbers, or manufacturer SKUs.
  - The adapter parsed product keywords (e.g. *"battery"*, *"headphone"*, *"dvd"*) to assign 6 broad functional buckets (`PROD_POWER_BATTERY`, `PROD_AUDIO_SOUND`, etc.).
  - The 7th segment (`PROD_SOCIAL_MENTIONS`) grouped all 1,000 Sentiment140 Twitter posts. **Treating Sentiment140's source identity as a product is a semantic misclassification**; social media posts are an ingestion channel, not a purchased SKU.
- **Actual Product Count**: **0** actual product SKUs (7 heuristic category clusters).

### 4.2 Are the 4 alerts real-world business incidents or generated threshold breaches?
- **Finding**: They are **algorithmic threshold breaches** triggered on synthetic chronological trends.
- **Evidence**:
  - Because `review_date` values were synthesized across a rolling 180-day window, the trend detector observed artificial week-over-week fluctuations.
  - When the rolling proportion of negative reviews in a synthetic week exceeded configured thresholds (e.g., negative sentiment shift $\ge 20\%$), an alert was triggered (e.g., `ALT_5FB235A8`).
  - These alerts prove that the alerting engine's mathematical logic functions correctly, but they do **not** represent historical commercial incidents or manufacturing recalls.

### 4.3 Does `review_date` contain genuine source dates?
- **Finding**: **NO**.
- **Evidence**:
  - Neither source file contained timestamp metadata.
  - All 5,000 dates were injected by the adapter using formulaic modulo offsets across the first 6 months of 2023.
- **Actual Date Availability in Raw Data**: **0%**.

### 4.4 Does `rating` contain genuine source ratings?
- **Finding**: **NO**.
- **Evidence**:
  - The source data only provided binary sentiment polarity (positive vs. negative).
  - The adapter assigned `1.0` to negative records and `5.0` to positive records.
  - There are zero granular 2-star, 3-star, or 4-star ratings in the dataset.
- **Actual Granular Rating Availability in Raw Data**: **0%**.

### 4.5 Does `campaign` contain genuine source campaign information?
- **Finding**: **NO**.
- **Evidence**:
  - Neither source dataset contained marketing attribution or UTM tracking tags.
  - All values were defaulted to placeholder strings (`"Amazon_Organic_Review"` and `"Social_Feedback_Monitoring"`).
- **Actual Campaign Availability in Raw Data**: **0%**.

### 4.6 Do Sentiment140 and Amazon records maintain source traceability?
- **Finding**: **YES**.
  - All 1,000 Sentiment140 records are cleanly segregated under `source = "Twitter/Social"` (`REV_004001` to `REV_005000`).
  - All 4,000 Amazon records are cleanly segregated under `source = "Amazon"` (`REV_000001` to `REV_004000`).

### 4.7 Were any records duplicated between the two datasets?
- **Finding**: **NO**.
  - Cross-dataset text overlap check: **0 duplicates** between Amazon reviews and Twitter status updates.
  - Intra-dataset duplicate check: **0 duplicate texts** and **0 duplicate IDs**.

---

## 5. Audit Metrics Summary

| Audit Dimension | Reported in Schema | Genuine Source Reality | Audit Status |
| :--- | :--- | :--- | :--- |
| **Total Ingested Records** | 5,000 | 5,000 | **Verified Authentic** |
| **Directly Observed Review Texts** | 5,000 | 5,000 | **Verified Authentic** |
| **Actual Product SKUs** | 7 | **0** (Category clusters only) | **Inferred / Segmented** |
| **Actual Categories** | 7 | **0** (Heuristic topics only) | **Inferred** |
| **Actual Source Channels** | 2 | 2 (Amazon & Twitter) | **Verified Authentic** |
| **Authentic Granular Star Ratings** | 5,000 | **0** (Binary sentiment proxies only) | **Inferred** |
| **Authentic Chronological Timestamps** | 5,000 | **0** (Synthesized dates) | **Synthesized** |
| **Authentic Marketing Campaigns** | 2 | **0** (Defaulted placeholders) | **Defaulted** |
| **Historical Operational Incidents** | 4 | **0** (Threshold alerts on simulated dates) | **Algorithmic Simulation** |

---

## 6. Recommendations & Concerns Requiring Correction Before Production

1. **Product Entity Integrity**:
   - For real enterprise deployment, ingest a dataset that contains true product catalog metadata (e.g. ASINs, SKUs, or product titles like *"Kindle Paperwhite 11th Gen"*, *"Echo Dot 5th Gen"*).
   - Segregate social media feedback (`Sentiment140`) into an unassigned or channel-level dimension rather than forcing it into a pseudo-product SKU (`PROD_SOCIAL_MENTIONS`).

2. **Temporal Trend Authenticity**:
   - Remove simulated dates prior to business reporting. When timestamps are missing from a source, retain `review_date = None` and explicitly report that temporal trends (WoW, MoM) cannot be calculated without genuine transaction dates.

3. **Rating Transparency**:
   - If ratings are derived from binary sentiment, label the column `sentiment_proxy_rating` or leave `rating = None` to avoid misleading stakeholders into believing customers submitted 5-star or 1-star survey scores.

4. **Alert Framing**:
   - Clearly label generated alerts as **"Algorithmic Threshold Demonstrations"** in executive decks and Power BI dashboards until deployed against streaming live customer feeds with true timestamps.

---

## 7. Post-Audit Realignment Implementation & Current Verified State

Following the audit findings, the entire data pipeline, ingestion adapters, trend detector, and alerting engine were realigned to eliminate data fabrication:

| Dimension | Pre-Audit State | Post-Audit Realignment State | Verification Status |
| :--- | :--- | :--- | :--- |
| **`review_date`** | `2023-01-01 + modulo` offsets | **`NULL` / `None`** across all 5,000 records | Verified: Zero dates manufactured |
| **`rating`** | Binary `0/1` mapped to `1.0/5.0` stars | **`NULL` / `None`** across all 5,000 records (`rating_source = 'not_available'`) | Verified: Zero false ratings stored |
| **`sentiment_proxy_rating`** | Overwrote genuine `rating` | Isolated to separate derived column | Verified: Transparently labeled as proxy |
| **`product_id`** | Pseudo-SKUs (`PROD_POWER_BATTERY`, etc.) | **`NULL` / `None`** across all 5,000 records | Verified: Zero pseudo-SKUs |
| **`segment`** | Conflated with product SKUs | Inferred topical category segment (Amazon: 6, Twitter: NULL) | Verified: Explicitly labeled as inferred segment |
| **`campaign`** | Hardcoded strings (`Amazon_Organic_Review`) | **`NULL` / `None`** across all 5,000 records | Verified: Zero placeholder campaigns |
| **`source`** | Amazon & Twitter/Social | Authentically preserved as `"Amazon"` (4,000) & `"Twitter/Social"` (1,000) | Verified: Origin provenance intact |
| **Trends Engine** | Calculated spurious WoW / MoM trends | Returns `status = 'insufficient_temporal_data'` | Verified: Graceful fallback without fake trends |
| **Alerts Engine** | Fired 11 alerts on synthetic time series | Temporal alerts skipped; demo alerts labeled `DEMONSTRATION - ...` | Verified: Zero misleading operational alerts |
