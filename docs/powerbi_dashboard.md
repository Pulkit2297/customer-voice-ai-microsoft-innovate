# CustomerVoice AI — Power BI Analytical Dashboard Guide

## 1. Overview & Architectural Principle

The **CustomerVoice AI** Power BI dashboard is designed to consume normalized, preprocessed, sentiment-scored, and topic-attributed analytical data directly from the **PostgreSQL analytics layer** (`customervoice_db` locally on port 5434 or Supabase PostgreSQL in the cloud). 

> [!IMPORTANT]
> **No Raw CSV Consumption:**
> In accordance with enterprise analytics best practices, the Power BI dashboard connects exclusively to the relational analytical tables in PostgreSQL (`reviews`, `sentiment_results`, `topics`, `products`, `alerts`, `model_metrics`). This ensures strict data lineage, enforces schema consistency, and leverages PostgreSQL indexing for low-latency queries.

---

## 2. PostgreSQL Connection Setup

### 2.1 Active Connection Parameters

| Parameter | Your Live Supabase Cloud Database |
| :--- | :--- |
| **Connector** | **PostgreSQL Database** |
| **Server** | `db.ehmgeoakcckhagdjjmmr.supabase.co:5432` |
| **Database** | `postgres` |
| **Data Connectivity** | **Import** *(Recommended for DAX & offline speed)* |
| **User Name** | `postgres` |
| **Password** | `Innovate@#2297` *(Or configured project password)* |
| **Encryption (SSL)** | **Mandatory** (`sslmode=require`) |

### 2.2 Verifying Database Connectivity Prior to Power BI Launch
Execute the automated connectivity check script to verify that all 6 tables and indexes are active:

```powershell
python scripts/check_database.py
```

Verified live output:
```text
Target Database: postgresql+psycopg2://postgres:***@db.ehmgeoakcckhagdjjmmr.supabase.co:5432/postgres?sslmode=require
Connection Status: [CONNECTED]
Database Dialect:  POSTGRESQL
Engine Version:    PostgreSQL 17.6 on aarch64-unknown-linux-gnu
  [OK] Table 'reviews' exists.
  [OK] Table 'products' exists.
  [OK] Table 'sentiment_results' exists.
  [OK] Table 'topics' exists.
  [OK] Table 'alerts' exists.
  [OK] Table 'model_metrics' exists.
[SUCCESS] All connectivity, schema, and index checks passed successfully.
```
[SUCCESS] All connectivity, schema, and index checks passed successfully.
```

---

## 3. Power Query (M) Ingestion & Data Transformation

All Power Query code is externalized in [`powerbi/powerquery_m_scripts.pq`](file:///d:/Mission%20Internship%20and%20Placement/Microsoft%20Innovate/customer-voice-ai/powerbi/powerquery_m_scripts.pq).

### 3.1 Step-by-Step Power BI Loading Instructions
1. Open **Power BI Desktop**.
2. Click **Get Data** &rarr; **PostgreSQL Database**.
3. In Server, enter `localhost:5434` (or your Supabase host); in Database, enter `customervoice_db`.
4. In the Navigator, select the 6 analytical tables:
   - `public.reviews` &rarr; rename query to **`FactReviews`**
   - `public.sentiment_results` &rarr; rename query to **`FactSentiment`**
   - `public.topics` &rarr; rename query to **`BridgeTopics`**
   - `public.products` &rarr; rename query to **`DimProducts`**
   - `public.alerts` &rarr; rename query to **`FactAlerts`**
   - `public.model_metrics` &rarr; rename query to **`FactModelMetrics`**
5. Click **Transform Data** to open the Power Query Editor.
6. Open **Advanced Editor** for each query and paste the corresponding block from `powerbi/powerquery_m_scripts.pq`.
7. Click **Close & Apply**.

---

## 4. Star Schema & Relational Model

The analytical model in Power BI is organized as a Star Schema centered around customer feedback facts:

```
               ┌───────────────────────────┐
               │        DimProducts        │ (Dimension)
               ├───────────────────────────┤
               │ product_id (PK)           │
               │ product_name              │
               │ category                  │
               └─────────────┬─────────────┘
                             │ 1
                             │
                             │ *
               ┌─────────────▼─────────────┐
               │        FactReviews        │ (Core Fact Table)
               ├───────────────────────────┤
               │ review_id (PK)            │
               │ review_text               │
               │ cleaned_text              │
               │ rating (NULL)             │
               │ review_date (NULL)        │
               │ product_id (FK)           │
               │ campaign (NULL)           │
               │ source (Amazon/Twitter)   │
               │ pii_detected              │
               │ pii_types                 │
               └───────┬───────────┬───────┘
                       │ 1         │ 1
                       │           │
                       │ 1         │ *
      ┌────────────────▼──────┐   ┌▼─────────────────────────┐
      │     FactSentiment     │   │       BridgeTopics       │ (Bridge Table)
      ├───────────────────────┤   ├──────────────────────────┤
      │ id (PK)               │   │ id (PK)                  │
      │ review_id (FK)        │   │ review_id (FK)           │
      │ sentiment             │   │ topic                    │
      │ sentiment_score       │   │ topic_confidence         │
      │ confidence            │   │ is_primary               │
      │ model_name            │   └──────────────────────────┘
      │ model_version         │
      └───────────────────────┘

 ┌───────────────────────────┐     ┌───────────────────────────┐
 │        FactAlerts         │     │     FactModelMetrics      │ (Benchmark Fact)
 ├───────────────────────────┤     ├───────────────────────────┤
 │ alert_id (PK)             │     │ id (PK)                   │
 │ alert_type                │     │ evaluation_type           │
 │ severity                  │     │ category                  │
 │ product                   │     │ metric_name               │
 │ topic                     │     │ metric_value              │
 │ metric                    │     │ validation_sample_size    │
 │ percentage_change         │     │ evaluation_timestamp      │
 │ status                    │     └───────────────────────────┘
 └───────────────────────────┘
```

### Relational Settings in Power BI Model View:
- `FactSentiment[review_id] 1 <---> 1 FactReviews[review_id]` (Cross filter direction: **Both**)
- `BridgeTopics[review_id] * <---> 1 FactReviews[review_id]` (Cross filter direction: **Both**)
- `FactReviews[product_id] * <---> 1 DimProducts[product_id]` (Cross filter direction: **Single**)

---

## 5. Page-by-Page Construction Specifications

The dashboard contains 5 dedicated analytical pages:

---

### PAGE 1: Executive Overview

**Objective:** High-level executive pulse on customer sentiment, review volume, and privacy governance.

#### 1. KPI Cards (Top Ribbon):
- **Total Reviews**: `[Total Reviews]` &rarr; **5,000**
- **Positive Sentiment %**: `[Positive Sentiment %]` &rarr; **62.8%** (Green accent)
- **Negative Sentiment %**: `[Negative Sentiment %]` &rarr; **30.5%** (Red accent)
- **Net Sentiment Score (NSS)**: `[Net Sentiment Score (NSS)]` &rarr; **+32.3%**
- **PII Protection Rate**: `[PII Redaction Rate %]` &rarr; **2.4%** (120 records masked)

#### 2. Visuals:
- **Donut Chart**: Sentiment Distribution (`FactSentiment[sentiment]`, Values: `[Total Reviews]`).
  - Colors: Positive = Green (`#107C41`), Neutral = Gray (`#8A8886`), Negative = Red (`#D13438`).
- **Stacked Bar Chart**: Volume & Sentiment by Channel (`FactReviews[source]`, Legend: `FactSentiment[sentiment]`).
  - Shows Amazon (4,000) vs Twitter/Social (1,000).
- **Matrix / Summary Cards**: Top 5 Discussion Drivers (`Product Quality`: 392, `Pricing`: 346, `Performance`: 221, `Return`: 201, `Packaging`: 128).
- **Slicers**:
  - Slicer 1: `FactReviews[source]` (Amazon, Twitter/Social)
  - Slicer 2: `FactSentiment[sentiment]` (Positive, Neutral, Negative)
  - Slicer 3: `FactReviews[pii_detected]` (True, False)

---

### PAGE 2: Why Are Customers Unhappy?

**Objective:** Root cause diagnostic of customer complaints, dissatisfaction drivers, and critical product issues.

#### 1. KPI Cards:
- **Total Complaints**: `[Negative Reviews]` &rarr; **1,526 Dissatisfied Customers**
- **Top Complaint Topic**: **Product Quality** &rarr; **118 negative mentions**
- **Highest Negative Concentration**: **Refund** &rarr; **46.3% negative rate**
- **Hardware Durability Issues**: **Battery & Reliability** &rarr; **38.8% average negative rate**

#### 2. Visuals:
- **Horizontal Bar Chart (Ranked)**: Negative Review Volume by Topic.
  - X-Axis: `[Negative Review Count by Topic]`
  - Y-Axis: `BridgeTopics[topic]`
  - Sort: Descending by negative count.
  - Ranks: Product Quality (118) &rarr; Pricing (100) &rarr; Return (70) &rarr; Performance (47) &rarr; Delivery (35) &rarr; Packaging (34) &rarr; Battery (27).
- **100% Stacked Bar Chart**: Topic Sentiment Breakdown.
  - Shows the proportion of Positive vs Neutral vs Negative per topic.
- **Complaint Drilldown Table**:
  - Filter: `FactSentiment[sentiment] = "Negative"`
  - Columns: `FactReviews[review_id]`, `FactReviews[source]`, `BridgeTopics[topic]`, `FactSentiment[sentiment_score]`, `FactReviews[cleaned_text]`.
- **Topic Slicer**: `BridgeTopics[topic]` for interactive multi-topic drill-through.

---

### PAGE 3: Product / Campaign Comparison

**Objective:** Multi-channel and topical comparison with transparent data lineage governance.

#### 1. Lineage & Semantic Integrity Banner:
- Card displaying `[Data Integrity Note: Products & Campaigns]`:
  > *"AUTHENTIC DATA POLICY: 0 genuine product SKUs or marketing campaigns exist in the raw corpora. Columns preserved as NULL to prevent data fabrication. Channel-level and topical segment comparisons displayed."*

#### 2. Visuals:
- **Comparison Matrix**:
  - Rows: `FactReviews[source]` (`Amazon`, `Twitter/Social`)
  - Values: `[Total Reviews]`, `[Positive Sentiment %]`, `[Negative Sentiment %]`, `[Net Sentiment Score (NSS)]`.
  - Highlights: Amazon has +44.3% NSS (71.0% positive); Twitter has -15.8% NSS (45.9% negative).
- **Inferred Category Segments Matrix (Amazon)**:
  - Topical segments extracted from text: *Audio & Sound* (~1,200), *Power & Battery* (~850), *Video & Display* (~650), *Computer Hardware* (~500), *Books & Publications* (~450), *General Consumer Goods* (~350).
- **Catalog Integration Guidance Callout**:
  - Outlines schema readiness to receive real ASINs/SKUs and UTM tracking campaigns when enterprise catalog feeds are connected.

---

### PAGE 4: Trends & Alerts

**Objective:** Statistical anomaly detection, threshold alerting, and temporal governance.

#### 1. Temporal Status Warning Banner:
- Card displaying `[Temporal Trend Engine Status]`:
  > *"STATUS: INSUFFICIENT_TEMPORAL_DATA (Synthetic date offsets eliminated. Genuine timestamps absent in source archives)."*

#### 2. KPI Cards:
- **Active Production Alerts**: `[Active Alerts Count]` &rarr; **0** *(0 false alerts)*
- **Temporal Status**: **INSUFFICIENT_TEMPORAL_DATA**
- **Threshold Rules Active**: **4 Configured Rules**

#### 3. Visuals:
- **Alert Configuration Table**:
  - Lists threshold cutoffs:
    1. Negative Sentiment Surge: `Delta >= 20.0%`
    2. Topic Discussion Surge: `Increase >= 30.0%`
    3. Rating Drop: `Drop >= 0.50 Stars`
    4. Model F1 Decay: `Decrease >= 0.10`
- **PostgreSQL Alerts Log**:
  - Visual connected to `FactAlerts`. Correctly reflects 0 rows on static historical data.
- **Demonstration Alert Simulation Table**:
  - Demonstrates how alerts format with `alert_type = "DEMONSTRATION - ..."` and `message = "[Algorithmic Alert Demonstration] ..."` during simulation testing.

---

### PAGE 5: Model Health

**Objective:** Transparent evaluation of the underlying NLP algorithms (VADER sentiment analysis and multi-label topic detection).

#### 1. Benchmark KPIs (from `FactModelMetrics`):
- **Accuracy**: `[Sentiment Model Accuracy]` &rarr; **46.7%**
- **Macro F1-Score**: `[Sentiment Model Macro F1]` &rarr; **0.3294**
- **Weighted F1-Score**: `[Sentiment Model Weighted F1]` &rarr; **0.3953**
- **Validation Sample Size**: `[Validation Corpus Size]` &rarr; **15 Reviews**
- **Positive Class Recall**: `[Sentiment Model Macro Recall]` &rarr; **83.3%**

#### 2. Visuals:
- **Clustered Column Chart**: Sentiment Performance by Class.
  - X-Axis: Class (`positive`, `neutral`, `negative`).
  - Values: Precision, Recall, F1-Score.
- **Topic Model Metrics Table**:
  - Topic performance benchmarks from `FactModelMetrics`:
    - Delivery: Precision 1.00, Recall 1.00, F1 1.00
    - Customer Support: Precision 1.00, Recall 1.00, F1 1.00
    - Battery: Precision 1.00, Recall 0.50, F1 0.67
    - Pricing: Precision 1.00, Recall 0.50, F1 0.67
- **Model Governance Disclosure**:
  > *"Metrics computed strictly against human-annotated validation ground truth (`data/validation/validation_set.csv`). No synthetic ground-truth labels were manufactured."*

---

## 6. Interactive HTML Dashboard Preview

An interactive, browser-based standalone dashboard implementing the complete visual design and data bindings is located at:
[`powerbi/dashboard_preview.html`](file:///d:/Mission%20Internship%20and%20Placement/Microsoft%20Innovate/customer-voice-ai/powerbi/dashboard_preview.html).

Open this file in any browser to interactively explore all 5 pages, examine KPI cards, view complaint distributions, and inspect live PostgreSQL metric summaries.
