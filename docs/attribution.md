# Product and Campaign Attribution Architecture

## 1. Overview

In **CustomerVoice AI**, raw customer reviews are frequently collected from disparate ingestion channels (e.g., app stores, e-commerce marketplaces, web portals, direct feedback widgets). To make unstructured voice-of-the-customer signals actionable for product management, brand marketing, and executive leadership, each review must be attributed to concrete business entities.

The attribution layer enforces rigorous data integrity:
- **Zero Hallucination / Invention**: Product, category, or campaign values are never synthesized or fabricated.
- **Explicit Unknowns**: Missing metadata is consistently marked as `"unknown"`, preventing ambiguity in downstream BI visualizations.
- **Zero Silent Loss**: No record is ever dropped due to missing attribution metadata. Every review is retained and assigned an explicit `product_attribution_status` (`"attributed"` vs. `"unattributed"`).

---

## 2. Core Distinctions: Attribution vs. Classification

A common source of confusion in customer voice platforms is the conceptual boundary between **Attribution** and **Text Classification**. The table below defines these four distinct analytical pillars:

| Capability | Core Question Answered | Source of Truth | Typical Output Values | Primary Business Stakeholder |
| :--- | :--- | :--- | :--- | :--- |
| **Product Attribution** | *What physical/digital asset or SKU is this review about?* | Transaction / Catalog Metadata | `PROD_102` (*Kindle Paperwhite*), `category: E-Readers` | Product Managers, Hardware Engineering, QA |
| **Campaign Attribution** | *Which marketing initiative or promotion prompted this feedback?* | Ingestion / UTM / Referral Metadata | `Holiday_Promo_2023`, `PrimeDay_Launch`, `unknown` | Growth Marketing, Brand Managers, Ad Ops |
| **Topic Classification** | *Which functional themes or areas does the text discuss?* | Unstructured NLP Text Analysis | `battery`, `customer_support`, `pricing`, `delivery` | Customer Support, Logistics, UX Designers |
| **Sentiment Classification**| *How does the customer emotionally evaluate their experience?* | Polarity / Affective Modeling | `positive`, `neutral`, `negative` (with continuous score) | Executive Leadership, CX Operations |

---

## 3. Illustrative Example

Consider this customer review:

> *"Got this during the Black Friday special. The battery is terrible and customer support never replied to my email."*

Here is how CustomerVoice AI decomposes the record across all four dimensions:

```
[Raw Ingestion Record]
  │
  ├── Product Attribution:
  │     • product_id:        "PROD_KINDLE_01"
  │     • product_name:      "Kindle Oasis"
  │     • category:          "E-Readers"
  │     • status:            "attributed"
  │
  ├── Campaign Attribution:
  │     • campaign:          "Black_Friday_2023"
  │     • status:            "attributed"
  │
  ├── Topic Classification (Multi-Label NLP):
  │     • topics:            ["battery", "customer_support"]
  │     • primary_topic:     "customer_support"
  │
  └── Sentiment Classification (Polarity Modeling):
        • sentiment:         "negative"
        • sentiment_score:   -0.6542
        • confidence:        0.6542
```

---

## 4. Why Distinguishing These Dimensions Matters

1. **Root-Cause Attribution vs. Subject Matter**:
   - A customer might express severe negative sentiment about `customer_support` during a `Holiday_Rush` campaign. Marketing needs to know if their campaign attracted an influx of angry users, while Customer Support needs to know whether the issue was call wait times or unhelpful agents.
2. **Product Quality Isolation**:
   - By slicing sentiment by `product_name` and `topic`, hardware teams can observe that *Kindle Paperwhite* has high satisfaction overall ($+0.82$), but the `battery` sub-topic shows isolated negative spikes ($-0.45$).
3. **Power BI Dimensional Modeling**:
   - In the analytical star schema, `product_id` and `campaign` act as **Conformed Dimensions** linked to transactional review facts, whereas `sentiment_score` acts as a continuous **Additive Measure**, and `topics` serves as a multi-valued **Bridge Dimension**.
