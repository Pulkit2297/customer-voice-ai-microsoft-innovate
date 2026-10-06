# CustomerVoice AI

A production-oriented Customer Voice Intelligence Platform designed to process customer reviews and unstructured feedback at scale to deliver actionable business intelligence.

---

## 1. What the Project Does

**CustomerVoice AI** transforms unstructured customer reviews and multi-channel feedback into structured, high-value insights. The platform enables organizations to:

- **Analyze Sentiment**: Detect nuanced polarity, aspect-based sentiments, and customer emotions across review corpora.
- **Detect Topics & Themes**: Discover emerging discussion points, cluster complaints, and classify feedback into functional areas.
- **Attribute Feedback**: Map reviews to specific products, feature rollouts, or marketing campaigns.
- **Identify Trends**: Track chronological changes in customer satisfaction and identify inflection points over time.
- **Trigger Complaint Alerts**: Detect urgent, safety-critical, or high-severity customer complaints in real-time.
- **Evaluate Models**: Continuously assess NLP/ML model performance, precision, recall, and calibration benchmarks.
- **Monitor Drift**: Detect both data drift (shifting vocabulary/distributions) and concept drift (decaying model accuracy).
- **Power BI Analytics**: Output curated, normalized analytical datasets optimized for direct consumption in Power BI dashboards.

---

## 2. Current Architecture

The project follows a clean, modular, production-ready structure separating ingestion, processing, modeling, serving, and reporting:

```
customer-voice-ai/
├── data/
│   ├── raw/                  # Immutable raw review datasets
│   ├── processed/            # Cleaned, anonymized, and transformed data
│   └── validation/           # Evaluation and benchmark datasets
├── src/
│   ├── ingestion/            # Raw data ingestion connectors & adapters
│   ├── preprocessing/        # Text normalization, tokenization, cleaning
│   ├── pii/                  # PII detection, redaction, and compliance
│   ├── sentiment/            # Sentiment classification pipeline
│   ├── topics/               # Unsupervised & supervised topic models
│   ├── attribution/          # Product and campaign entity attribution
│   ├── evaluation/           # Performance metrics and validation suites
│   ├── trends/               # Temporal analytics and trend detection
│   ├── alerts/               # Real-time alert triggers and notification logic
│   └── monitoring/           # Data drift and model decay monitoring
├── api/                      # FastAPI routers, schemas, and endpoints
├── tests/                    # Unit, integration, and performance tests
├── notebooks/                # Exploratory data analysis and model prototyping
├── dashboard/                # Power BI templates and reporting assets
├── docs/                     # Technical specifications and API documentation
├── scripts/                  # Data migration, operational, and maintenance scripts
├── .env.example              # Environment variable template
├── .gitignore                # Git exclusion rules
├── requirements.txt          # Python dependencies
├── README.md                 # Project documentation
└── main.py                   # Application entrypoint & server runner
```

---

## 3. Planned Pipeline

The planned production processing pipeline consists of sequential, decoupled stages:

```
[Raw Customer Reviews / API Feeds]
               │
               ▼
   [1. Ingestion Layer] (Validation & Schema Enforcement)
               │
               ▼
   [2. PII Scrubbing] (Masking names, emails, phone numbers)
               │
               ▼
   [3. Preprocessing & Normalization] (Tokenization, Lemmatization, Cleaning)
               │
               ▼
   [4. Feature Extraction & Modeling Engine]
        ├── Sentiment Analysis Engine
        ├── Topic Detection & Clustering
        └── Product / Campaign Attribution
               │
               ▼
   [5. Analytics & Signal Generation]
        ├── Real-Time Complaint Alerts (Threshold Breaches)
        └── Temporal Trend & Anomaly Detection
               │
               ▼
   [6. Storage & Serving Layer]
        ├── PostgreSQL (Relational schema for transactional data)
        ├── FastAPI (Low-latency programmatic access)
        └── Power BI Analytics Data Views (Curated star schema / dimensional models)
               │
               ▼
   [7. Continuous Monitoring & Governance]
        ├── Model Evaluation & Benchmarking
        └── Data and Concept Drift Monitoring
```

---

## 4. How to Install Dependencies

### Prerequisites
- Python 3.11+
- Virtual environment tool (`venv` recommended)

### Step 1: Clone or navigate to the project directory
```bash
cd customer-voice-ai
```

### Step 2: Create and activate a virtual environment
**On Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**On Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install required dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure environment variables
Copy the template configuration to create your local `.env`:
```bash
cp .env.example .env
```
*(On Windows PowerShell: `Copy-Item .env.example .env`)*

Modify `.env` to match your local setup (database credentials, port, secret key).

---

## 5. How to Run the Project

### Running the API Server

You can run the application directly using Python or via Uvicorn:

**Using Python:**
```bash
python main.py
```

**Using Uvicorn directly (with live reload):**
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### Verifying the Health Endpoint

Once the server is running, check the health endpoint:

```bash
curl http://127.0.0.1:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "CustomerVoice AI"
}
```

Interactive API documentation (Swagger UI) is available at:
`http://127.0.0.1:8000/docs`

### Running Tests

Execute the automated test suite with pytest:
```bash
pytest
```
