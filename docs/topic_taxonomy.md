# Controlled Topic Taxonomy for CustomerVoice AI

## 1. Overview

Rather than relying on unrestricted unsupervised topic discovery (such as LDA or raw k-means), **CustomerVoice AI** employs a **controlled, hierarchical domain taxonomy**. Unsupervised clustering often generates ambiguous, non-actionable clusters that fluctuate with every retraining cycle. A controlled taxonomy provides:

- **Business Alignment**: Topics map directly to operational departments (Product, Logistics, Customer Support, Billing, Engineering).
- **Multi-Topic Assignment**: Customer feedback often spans several functional domains simultaneously (e.g., both battery drain and slow shipping).
- **Deterministic & Auditable**: Rule-based matching enables full transparency and zero latency without GPU infrastructure.
- **Power BI Ready**: Generates stable, standardized categorical dimensions for Power BI slicers, drill-downs, and trend tracking.

---

## 2. Taxonomy Reference (12 Core Topics)

| Topic Identifier | Display Name | Functional Domain | Primary Keywords / Triggers | Actionable Business Unit |
| :--- | :--- | :--- | :--- | :--- |
| `product_quality` | Product Quality | Hardware / Manufacturing | quality, build quality, material, defective, sturdy, broken, flimsy, well made | Quality Assurance / Manufacturing |
| `battery` | Battery & Charging | Hardware / Power | battery, battery life, charge, charger, drain, draining, recharge, power bank | Hardware Engineering |
| `performance` | Performance & Speed | Software / Firmware | performance, fast, speed, slow, sluggish, lag, latency, freeze, smooth | Software / Firmware Engineering |
| `delivery` | Shipping & Delivery | Supply Chain / Logistics | delivery, shipping, courier, transit, tracking, arrived, dispatch, delayed | Supply Chain & Logistics |
| `customer_support`| Customer Support | CX / Service Ops | customer support, customer service, support team, representative, helpdesk, never replied | Customer Experience / Support Ops |
| `pricing` | Pricing & Value | Sales & Marketing | price, pricing, expensive, cost, overpriced, affordable, value for money, cheap | Pricing & Product Marketing |
| `refund` | Refunds & Credits | Finance / Billing | refund, refunded, money back, reimburse, chargeback, billing error | Finance & Billing |
| `return` | Returns & Exchanges | CX / Reverse Logistics | return, returned, replacement, replace, exchange, return policy, RMA | Returns & Reverse Logistics |
| `packaging` | Packaging & Unboxing| Fulfillment / Warehouse | packaging, box, unboxing, bubble wrap, damaged box, crushed box, seal | Fulfillment & Warehouse Ops |
| `usability` | Usability & Ease of Use | UX / Design | easy to use, intuitive, difficult to use, complicated, setup, confusing, ergonomic | UX / Product Design |
| `features` | Features & Specs | Product Management | feature, features, functionality, specs, bluetooth, wifi, settings, options | Product Management |
| `reliability` | Reliability & Stability | Software QA / Reliability | reliable, crash, crashed, glitch, reboot, random shutdown, disconnect, fault | Reliability Engineering (SRE) |

---

## 3. Multi-Topic Detection Logic

A single customer review can contain feedback regarding multiple disparate areas:

> **Example**: *"The battery is terrible and customer support never replied."*
> - **Detected Topics**: `["battery", "customer_support"]`
> - **Confidence**: Computed for each topic independently based on keyword match density.
> - **Primary Topic**: The topic with the highest match score is assigned as `primary_topic` for single-dimension BI reporting, while the multi-topic array allows granular multi-label filtering.

If a review does not trigger any taxonomy keywords:
- `topics`: `""` (empty)
- `topic_confidence`: `"{}"`
- `primary_topic`: `None`

---

## 4. Modifying and Extending the Taxonomy

The taxonomy is declared declaratively in [`src/topics/taxonomy.yaml`](file:///d:/Mission%20Internship%20and%20Placement/Microsoft%20Innovate/customer-voice-ai/src/topics/taxonomy.yaml).

To introduce a new topic:
1. Open `taxonomy.yaml`.
2. Add a new key following this structure:
   ```yaml
   warranty:
     display_name: "Warranty & Protection Plans"
     description: "Inquiries regarding extended warranty coverage or claims."
     keywords:
       - "warranty"
       - "extended warranty"
       - "claim"
       - "guarantee"
   ```
3. The `TopicClassifier` automatically compiles word-boundary regexes dynamically on instantiation—no code alterations required.

---

## 5. Future Evolutionary Roadmap

- **Phase A**: Rule-based keyword matching (current baseline).
- **Phase B**: Embedding-assisted zero-shot classification (e.g., SetFit or Sentence-Transformers) for synonym and semantic paraphrase detection.
- **Phase C**: Azure AI Language Conversational Topic Clustering integration for automated discovery of emerging micro-topics under each parent category.
