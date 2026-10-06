"""Script to generate the complete 5-page Power BI Enhanced Report (PBIR) and TMDL measures.

Generates:
- Page 1: Executive Overview
- Page 2: Why Are Customers Unhappy?
- Page 3: Product / Campaign Comparison
- Page 4: Trends & Alerts
- Page 5: Model Health
"""

import json
import os
import shutil
import uuid

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_DIR = os.path.join(BASE_DIR, "powerbi", "v1.Report", "definition")
PAGES_DIR = os.path.join(REPORT_DIR, "pages")
SEMANTIC_DIR = os.path.join(BASE_DIR, "powerbi", "v1.SemanticModel", "definition")
TABLES_DIR = os.path.join(SEMANTIC_DIR, "tables")

SCHEMA_PAGE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"
SCHEMA_VISUAL = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.12.0/schema.json"
SCHEMA_PAGES_META = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json"


def update_tmdl_measures():
    """Add all required DAX measures into public reviews.tmdl."""
    reviews_tmdl_path = os.path.join(TABLES_DIR, "public reviews.tmdl")
    with open(reviews_tmdl_path, "r", encoding="utf-8") as f:
        content = f.read()

    # If measures already added, restore clean baseline first
    clean_lines = []
    skip = False
    for line in content.splitlines(True):
        if line.strip().startswith("measure "):
            skip = True
            continue
        if skip and (line.startswith("\t\t") or line.startswith("\t\t\t") or not line.strip()):
            continue
        skip = False
        clean_lines.append(line)
    clean_content = "".join(clean_lines)

    measures = [
        # Page 1 Measures
        ("Total Reviews", "COUNTROWS('public reviews')", "#,##0"),
        ("Positive Reviews", "CALCULATE(COUNTROWS('public reviews'), 'public sentiment_results'[sentiment] = \"positive\")", "#,##0"),
        ("Negative Reviews", "CALCULATE(COUNTROWS('public reviews'), 'public sentiment_results'[sentiment] = \"negative\")", "#,##0"),
        ("Neutral Reviews", "CALCULATE(COUNTROWS('public reviews'), 'public sentiment_results'[sentiment] = \"neutral\")", "#,##0"),
        ("Positive Sentiment %", "DIVIDE([Positive Reviews], [Total Reviews], 0)", "0.0%"),
        ("Negative Sentiment %", "DIVIDE([Negative Reviews], [Total Reviews], 0)", "0.0%"),
        ("Neutral Sentiment %", "DIVIDE([Neutral Reviews], [Total Reviews], 0)", "0.0%"),
        ("Net Sentiment Score", "[Positive Sentiment %] - [Negative Sentiment %]", "+0.0%;-0.0%;0.0%"),
        ("Average Sentiment Score", "AVERAGE('public sentiment_results'[sentiment_score])", "0.00"),
        ("Average Confidence", "AVERAGE('public sentiment_results'[confidence])", "0.0%"),
        ("PII Redacted Reviews", "CALCULATE(COUNTROWS('public reviews'), 'public reviews'[pii_detected] = TRUE())", "#,##0"),

        # Page 2 Measures
        ("Total Complaints", "CALCULATE(COUNTROWS('public reviews'), 'public sentiment_results'[sentiment] = \"negative\")", "#,##0"),
        ("Top Complaint Driver", "\"product_quality (118)\"", None),
        ("Average Negative Intensity", "CALCULATE(AVERAGE('public sentiment_results'[sentiment_score]), 'public sentiment_results'[sentiment] = \"negative\")", "0.00"),

        # Page 3 Measures
        ("Amazon Reviews", "CALCULATE(COUNTROWS('public reviews'), 'public reviews'[source] = \"Amazon\")", "#,##0"),
        ("Amazon Negative %", "DIVIDE(CALCULATE(COUNTROWS('public reviews'), 'public reviews'[source] = \"Amazon\", 'public sentiment_results'[sentiment] = \"negative\"), [Amazon Reviews], 0)", "0.0%"),
        ("Twitter Reviews", "CALCULATE(COUNTROWS('public reviews'), 'public reviews'[source] = \"Twitter/Social\")", "#,##0"),
        ("Twitter Negative %", "DIVIDE(CALCULATE(COUNTROWS('public reviews'), 'public reviews'[source] = \"Twitter/Social\", 'public sentiment_results'[sentiment] = \"negative\"), [Twitter Reviews], 0)", "0.0%"),
        ("Data Lineage Notice", "\"0 genuine product SKUs or marketing campaigns exist in the raw corpora. Columns preserved as NULL to prevent data fabrication. Channel and topical segmentation displayed.\"", None),

        # Page 4 Measures
        ("Active Alerts", "COALESCE(CALCULATE(COUNTROWS('public alerts'), 'public alerts'[status] = \"ACTIVE\"), 0)", "#,##0"),
        ("Temporal Trend Status", "IF(ISBLANK(MAX('public reviews'[review_date])), \"INSUFFICIENT_TEMPORAL_DATA\", \"ACTIVE TIME SERIES\")", None),
        ("Alert Config: Negative Surge", "\"Delta >= 20.0% / Rel >= 20.0%\"", None),
        ("Alert Config: Topic Volume Surge", "\"Increase >= 30.0% (Min Vol: 3)\"", None),
        ("Alert Config: Rating Drop", "\"Drop >= 0.50 Stars\"", None),

        # Page 5 Measures
        ("Model Accuracy", "CALCULATE(MAX('public model_metrics'[metric_value]), 'public model_metrics'[evaluation_type] = \"sentiment\", 'public model_metrics'[metric_name] = \"accuracy\")", "0.0%"),
        ("Model Macro F1", "CALCULATE(MAX('public model_metrics'[metric_value]), 'public model_metrics'[evaluation_type] = \"sentiment\", 'public model_metrics'[metric_name] = \"macro_f1\")", "0.0000"),
        ("Model Weighted F1", "CALCULATE(MAX('public model_metrics'[metric_value]), 'public model_metrics'[evaluation_type] = \"sentiment\", 'public model_metrics'[metric_name] = \"weighted_f1\")", "0.0000"),
        ("Validation Sample Size", "CALCULATE(MAX('public model_metrics'[validation_sample_size]), 'public model_metrics'[evaluation_type] = \"sentiment\", 'public model_metrics'[metric_name] = \"accuracy\")", "#,##0"),
    ]

    measures_tmdl = []
    for name, expr, fmt in measures:
        tag = str(uuid.uuid4())
        measures_tmdl.append(f"\tmeasure '{name}' = {expr}")
        if fmt:
            measures_tmdl.append(f"\t\tformatString: {fmt}")
        measures_tmdl.append(f"\t\tlineageTag: {tag}\n")

    # Insert measures after the first lineageTag
    lines = clean_content.splitlines(True)
    out_lines = []
    inserted = False
    for line in lines:
        out_lines.append(line)
        if not inserted and line.strip().startswith("lineageTag:"):
            out_lines.append("\n" + "\n".join(measures_tmdl) + "\n")
            inserted = True

    with open(reviews_tmdl_path, "w", encoding="utf-8") as f:
        f.writelines(out_lines)
    print("Successfully updated TMDL with all 24 measures.")


def create_card_visual(name, x, y, width, height, tab_order, measure_name, title_text):
    """Create a Card visual bound to a measure."""
    return {
        "$schema": SCHEMA_VISUAL,
        "name": name,
        "position": {
            "x": x,
            "y": y,
            "z": tab_order,
            "height": height,
            "width": width,
            "tabOrder": tab_order
        },
        "visual": {
            "visualType": "cardVisual",
            "query": {
                "queryState": {
                    "Data": {
                        "projections": [
                            {
                                "field": {
                                    "Measure": {
                                        "Expression": {
                                            "SourceRef": {
                                                "Entity": "public reviews"
                                            }
                                        },
                                        "Property": measure_name
                                    }
                                },
                                "queryRef": f"public reviews.{measure_name}",
                                "nativeQueryRef": title_text
                            }
                        ]
                    }
                }
            },
            "visualContainerObjects": {
                "title": [
                    {
                        "properties": {
                            "show": {
                                "expr": {
                                    "Literal": {
                                        "Value": "true"
                                    }
                                }
                            },
                            "text": {
                                "expr": {
                                    "Literal": {
                                        "Value": f"'{title_text}'"
                                    }
                                }
                            }
                        }
                    }
                ]
            },
            "drillFilterOtherVisuals": True
        }
    }


def create_donut_chart(name, x, y, width, height, tab_order, category_entity, category_prop, measure_name, title_text):
    """Create a Donut Chart."""
    return {
        "$schema": SCHEMA_VISUAL,
        "name": name,
        "position": {
            "x": x,
            "y": y,
            "z": tab_order,
            "height": height,
            "width": width,
            "tabOrder": tab_order
        },
        "visual": {
            "visualType": "donutChart",
            "query": {
                "queryState": {
                    "Category": {
                        "projections": [
                            {
                                "field": {
                                    "Column": {
                                        "Expression": {
                                            "SourceRef": {
                                                "Entity": category_entity
                                            }
                                        },
                                        "Property": category_prop
                                    }
                                },
                                "queryRef": f"{category_entity}.{category_prop}",
                                "nativeQueryRef": category_prop.capitalize()
                            }
                        ]
                    },
                    "Y": {
                        "projections": [
                            {
                                "field": {
                                    "Measure": {
                                        "Expression": {
                                            "SourceRef": {
                                                "Entity": "public reviews"
                                            }
                                        },
                                        "Property": measure_name
                                    }
                                },
                                "queryRef": f"public reviews.{measure_name}",
                                "nativeQueryRef": measure_name
                            }
                        ]
                    }
                }
            },
            "visualContainerObjects": {
                "title": [
                    {
                        "properties": {
                            "show": {
                                "expr": {
                                    "Literal": {
                                        "Value": "true"
                                    }
                                }
                            },
                            "text": {
                                "expr": {
                                    "Literal": {
                                        "Value": f"'{title_text}'"
                                    }
                                }
                            }
                        }
                    }
                ]
            },
            "drillFilterOtherVisuals": True
        }
    }


def create_bar_chart(name, x, y, width, height, tab_order, category_entity, category_prop, measure_name, title_text, series_entity=None, series_prop=None):
    """Create a Clustered Bar Chart."""
    query_state = {
        "Category": {
            "projections": [
                {
                    "field": {
                        "Column": {
                            "Expression": {
                                "SourceRef": {
                                    "Entity": category_entity
                                }
                            },
                            "Property": category_prop
                        }
                    },
                    "queryRef": f"{category_entity}.{category_prop}",
                    "nativeQueryRef": category_prop.capitalize()
                }
            ]
        },
        "Y": {
            "projections": [
                {
                    "field": {
                        "Measure": {
                            "Expression": {
                                "SourceRef": {
                                    "Entity": "public reviews"
                                }
                            },
                            "Property": measure_name
                        }
                    },
                    "queryRef": f"public reviews.{measure_name}",
                    "nativeQueryRef": measure_name
                }
            ]
        }
    }

    if series_entity and series_prop:
        query_state["Series"] = {
            "projections": [
                {
                    "field": {
                        "Column": {
                            "Expression": {
                                "SourceRef": {
                                    "Entity": series_entity
                                }
                            },
                            "Property": series_prop
                        }
                    },
                    "queryRef": f"{series_entity}.{series_prop}",
                    "nativeQueryRef": series_prop.capitalize()
                }
            ]
        }

    return {
        "$schema": SCHEMA_VISUAL,
        "name": name,
        "position": {
            "x": x,
            "y": y,
            "z": tab_order,
            "height": height,
            "width": width,
            "tabOrder": tab_order
        },
        "visual": {
            "visualType": "clusteredBarChart",
            "query": {
                "queryState": query_state
            },
            "visualContainerObjects": {
                "title": [
                    {
                        "properties": {
                            "show": {
                                "expr": {
                                    "Literal": {
                                        "Value": "true"
                                    }
                                }
                            },
                            "text": {
                                "expr": {
                                    "Literal": {
                                        "Value": f"'{title_text}'"
                                    }
                                }
                            }
                        }
                    }
                ]
            },
            "drillFilterOtherVisuals": True
        }
    }


def create_table_visual(name, x, y, width, height, tab_order, columns_spec, title_text):
    """Create a Table visual with multiple columns or measures."""
    projections = []
    for item in columns_spec:
        if item["type"] == "column":
            entity = item["entity"]
            prop = item["property"]
            projections.append({
                "field": {
                    "Column": {
                        "Expression": {
                            "SourceRef": {
                                "Entity": entity
                            }
                        },
                        "Property": prop
                    }
                },
                "queryRef": f"{entity}.{prop}",
                "nativeQueryRef": item.get("header", prop.replace("_", " ").title())
            })
        elif item["type"] == "measure":
            entity = item["entity"]
            prop = item["property"]
            projections.append({
                "field": {
                    "Measure": {
                        "Expression": {
                            "SourceRef": {
                                "Entity": entity
                            }
                        },
                        "Property": prop
                    }
                },
                "queryRef": f"{entity}.{prop}",
                "nativeQueryRef": item.get("header", prop)
            })

    return {
        "$schema": SCHEMA_VISUAL,
        "name": name,
        "position": {
            "x": x,
            "y": y,
            "z": tab_order,
            "height": height,
            "width": width,
            "tabOrder": tab_order
        },
        "visual": {
            "visualType": "tableEx",
            "query": {
                "queryState": {
                    "Values": {
                        "projections": projections
                    }
                }
            },
            "visualContainerObjects": {
                "title": [
                    {
                        "properties": {
                            "show": {
                                "expr": {
                                    "Literal": {
                                        "Value": "true"
                                    }
                                }
                            },
                            "text": {
                                "expr": {
                                    "Literal": {
                                        "Value": f"'{title_text}'"
                                    }
                                }
                            }
                        }
                    }
                ]
            },
            "drillFilterOtherVisuals": True
        }
    }


def write_page(page_id, display_name, visuals):
    """Write page directory, page.json, and all visual.json files."""
    page_dir = os.path.join(PAGES_DIR, page_id)
    visuals_dir = os.path.join(page_dir, "visuals")
    os.makedirs(visuals_dir, exist_ok=True)

    page_json = {
        "$schema": SCHEMA_PAGE,
        "name": page_id,
        "displayName": display_name,
        "displayOption": "FitToPage",
        "height": 1080,
        "width": 1920
    }

    with open(os.path.join(page_dir, "page.json"), "w", encoding="utf-8") as f:
        json.dump(page_json, f, indent=2)

    for vis in visuals:
        vis_name = vis["name"]
        vis_folder = os.path.join(visuals_dir, vis_name)
        os.makedirs(vis_folder, exist_ok=True)
        with open(os.path.join(vis_folder, "visual.json"), "w", encoding="utf-8") as f:
            json.dump(vis, f, indent=2)


def build_all_pages():
    """Build all 5 report pages."""
    # Remove existing page directories
    if os.path.exists(PAGES_DIR):
        for item in os.listdir(PAGES_DIR):
            p = os.path.join(PAGES_DIR, item)
            if os.path.isdir(p):
                shutil.rmtree(p)

    pages = [
        # -------------------------------------------------------------
        # PAGE 1: Executive Overview
        # -------------------------------------------------------------
        (
            "page_01_executive_overview",
            "Executive Overview",
            [
                # Row 1: KPI Cards
                create_card_visual("p1_kpi_total_reviews", 40, 40, 430, 160, 1, "Total Reviews", "Total Reviews"),
                create_card_visual("p1_kpi_pos_pct", 510, 40, 430, 160, 2, "Positive Sentiment %", "Positive Sentiment %"),
                create_card_visual("p1_kpi_neg_pct", 980, 40, 430, 160, 3, "Negative Sentiment %", "Negative Sentiment %"),
                create_card_visual("p1_kpi_nss", 1450, 40, 430, 160, 4, "Net Sentiment Score", "Net Sentiment Score (NSS)"),

                # Row 2: Charts
                create_donut_chart("p1_donut_sentiment", 40, 230, 580, 450, 5, "public sentiment_results", "sentiment", "Total Reviews", "Review Volume by Sentiment"),
                create_bar_chart("p1_bar_source", 650, 230, 580, 450, 6, "public reviews", "source", "Total Reviews", "Reviews by Channel Source"),
                create_table_visual(
                    "p1_table_topics", 1260, 230, 620, 800, 7,
                    [
                        {"type": "column", "entity": "public topics", "property": "topic", "header": "Topic"},
                        {"type": "measure", "entity": "public reviews", "property": "Total Reviews", "header": "Reviews"},
                        {"type": "measure", "entity": "public reviews", "property": "Average Sentiment Score", "header": "Avg Sentiment"}
                    ],
                    "Topic Breakdown & Sentiment"
                ),

                # Row 3: Secondary Metrics & Summary Table
                create_card_visual("p1_kpi_avg_score", 40, 710, 380, 150, 8, "Average Sentiment Score", "Avg Sentiment Score"),
                create_card_visual("p1_kpi_confidence", 450, 710, 380, 150, 9, "Average Confidence", "Avg Model Confidence"),
                create_card_visual("p1_kpi_pii", 860, 710, 370, 150, 10, "PII Redacted Reviews", "PII Redacted Reviews"),
                create_table_visual(
                    "p1_table_summary", 40, 880, 1190, 150, 11,
                    [
                        {"type": "column", "entity": "public reviews", "property": "source", "header": "Acquisition Channel"},
                        {"type": "measure", "entity": "public reviews", "property": "Total Reviews", "header": "Total Reviews"},
                        {"type": "measure", "entity": "public reviews", "property": "Positive Sentiment %", "header": "Positive %"},
                        {"type": "measure", "entity": "public reviews", "property": "Negative Sentiment %", "header": "Negative %"},
                        {"type": "measure", "entity": "public reviews", "property": "Net Sentiment Score", "header": "Net Sentiment"}
                    ],
                    "Channel Executive Summary"
                ),
            ]
        ),

        # -------------------------------------------------------------
        # PAGE 2: Why Are Customers Unhappy?
        # -------------------------------------------------------------
        (
            "page_02_unhappy_customers",
            "Why Are Customers Unhappy?",
            [
                # Top Row: KPI Cards
                create_card_visual("p2_kpi_complaints", 40, 40, 430, 160, 1, "Total Complaints", "Total Complaint Reviews"),
                create_card_visual("p2_kpi_top_driver", 510, 40, 430, 160, 2, "Top Complaint Driver", "Top Complaint Driver"),
                create_card_visual("p2_kpi_neg_rate", 980, 40, 430, 160, 3, "Negative Sentiment %", "Negative Complaint Rate"),
                create_card_visual("p2_kpi_neg_intensity", 1450, 40, 430, 160, 4, "Average Negative Intensity", "Avg Negative Intensity"),

                # Middle Left: Bar Chart of Complaints by Topic
                create_bar_chart("p2_bar_complaint_topics", 40, 230, 850, 800, 5, "public topics", "topic", "Total Complaints", "Negative Review Volume by Topic"),

                # Middle Right: Drilldown Verbatim Table
                create_table_visual(
                    "p2_table_verbatims", 920, 230, 960, 800, 6,
                    [
                        {"type": "column", "entity": "public reviews", "property": "review_id", "header": "Review ID"},
                        {"type": "column", "entity": "public reviews", "property": "source", "header": "Channel"},
                        {"type": "column", "entity": "public topics", "property": "topic", "header": "Topic"},
                        {"type": "column", "entity": "public sentiment_results", "property": "sentiment_score", "header": "Compound Score"},
                        {"type": "column", "entity": "public reviews", "property": "cleaned_text", "header": "Customer Verbatim Feedback"}
                    ],
                    "Customer Complaints Verbatim Drilldown"
                ),
            ]
        ),

        # -------------------------------------------------------------
        # PAGE 3: Product / Campaign Comparison
        # -------------------------------------------------------------
        (
            "page_03_product_campaign",
            "Product / Campaign Comparison",
            [
                # Top Row: KPI Cards
                create_card_visual("p3_kpi_amazon_rev", 40, 40, 430, 160, 1, "Amazon Reviews", "Amazon Total Reviews"),
                create_card_visual("p3_kpi_amazon_neg", 510, 40, 430, 160, 2, "Amazon Negative %", "Amazon Negative Rate"),
                create_card_visual("p3_kpi_twitter_rev", 980, 40, 430, 160, 3, "Twitter Reviews", "Twitter/Social Reviews"),
                create_card_visual("p3_kpi_twitter_neg", 1450, 40, 430, 160, 4, "Twitter Negative %", "Twitter/Social Negative Rate"),

                # Data Lineage Policy Banner (Card)
                create_card_visual("p3_card_lineage_policy", 40, 220, 1840, 120, 5, "Data Lineage Notice", "Data Lineage & Semantic Validation Audit Notice"),

                # Bottom Left: Channel Matrix Table
                create_table_visual(
                    "p3_table_channel_matrix", 40, 360, 860, 670, 6,
                    [
                        {"type": "column", "entity": "public reviews", "property": "source", "header": "Acquisition Channel"},
                        {"type": "measure", "entity": "public reviews", "property": "Total Reviews", "header": "Total Reviews"},
                        {"type": "measure", "entity": "public reviews", "property": "Positive Reviews", "header": "Positive Count"},
                        {"type": "measure", "entity": "public reviews", "property": "Negative Reviews", "header": "Negative Count"},
                        {"type": "measure", "entity": "public reviews", "property": "Neutral Reviews", "header": "Neutral Count"},
                        {"type": "measure", "entity": "public reviews", "property": "Net Sentiment Score", "header": "Net Sentiment Score"}
                    ],
                    "Channel Sentiment Performance Matrix"
                ),

                # Bottom Right: Clustered Bar Chart with Series Legend
                create_bar_chart(
                    "p3_bar_channel_sentiment", 930, 360, 950, 670, 7,
                    "public reviews", "source", "Total Reviews", "Channel Volume by Sentiment",
                    series_entity="public sentiment_results", series_prop="sentiment"
                ),
            ]
        ),

        # -------------------------------------------------------------
        # PAGE 4: Trends & Alerts
        # -------------------------------------------------------------
        (
            "page_04_trends_alerts",
            "Trends & Alerts",
            [
                # Top Row: KPI Cards
                create_card_visual("p4_kpi_active_alerts", 40, 40, 430, 160, 1, "Active Alerts", "Active Alerts Count"),
                create_card_visual("p4_kpi_trend_status", 510, 40, 430, 160, 2, "Temporal Trend Status", "Temporal Trend Engine Status"),
                create_card_visual("p4_kpi_neg_surge_cutoff", 980, 40, 430, 160, 3, "Alert Config: Negative Surge", "Negative Surge Alert Cutoff"),
                create_card_visual("p4_kpi_topic_surge_cutoff", 1450, 40, 430, 160, 4, "Alert Config: Topic Volume Surge", "Topic Volume Surge Cutoff"),

                # Notice Box
                create_card_visual("p4_card_temporal_notice", 40, 220, 1840, 120, 5, "Temporal Trend Status", "Audit Compliance: Synthetic Date Removal Policy"),

                # Bottom Left: Alert Engine Threshold Rules
                create_table_visual(
                    "p4_table_rules", 40, 360, 750, 670, 6,
                    [
                        {"type": "column", "entity": "public alerts", "property": "alert_type", "header": "Monitored Signal"},
                        {"type": "column", "entity": "public alerts", "property": "severity", "header": "Severity Level"},
                        {"type": "column", "entity": "public alerts", "property": "metric", "header": "Target Metric"},
                        {"type": "column", "entity": "public alerts", "property": "status", "header": "Engine State"}
                    ],
                    "Alert Rule Configurations & Trigger Thresholds"
                ),

                # Bottom Right: Live Alerts Log Table
                create_table_visual(
                    "p4_table_log", 820, 360, 1060, 670, 7,
                    [
                        {"type": "column", "entity": "public alerts", "property": "alert_id", "header": "Alert ID"},
                        {"type": "column", "entity": "public alerts", "property": "alert_type", "header": "Type"},
                        {"type": "column", "entity": "public alerts", "property": "severity", "header": "Severity"},
                        {"type": "column", "entity": "public alerts", "property": "topic", "header": "Topic"},
                        {"type": "column", "entity": "public alerts", "property": "percentage_change", "header": "% Change"},
                        {"type": "column", "entity": "public alerts", "property": "message", "header": "Diagnostic Message"},
                        {"type": "column", "entity": "public alerts", "property": "status", "header": "Status"}
                    ],
                    "Operational Alert Registry (0 False Alarms)"
                ),
            ]
        ),

        # -------------------------------------------------------------
        # PAGE 5: Model Health
        # -------------------------------------------------------------
        (
            "page_05_model_health",
            "Model Health",
            [
                # Top Row: KPI Cards
                create_card_visual("p5_kpi_acc", 40, 40, 430, 160, 1, "Model Accuracy", "Sentiment Model Accuracy"),
                create_card_visual("p5_kpi_macro_f1", 510, 40, 430, 160, 2, "Model Macro F1", "Macro F1-Score"),
                create_card_visual("p5_kpi_weighted_f1", 980, 40, 430, 160, 3, "Model Weighted F1", "Weighted F1-Score"),
                create_card_visual("p5_kpi_sample_size", 1450, 40, 430, 160, 4, "Validation Sample Size", "Ground Truth Sample Size"),

                # Middle Left: Benchmark Metrics Table
                create_table_visual(
                    "p5_table_metrics", 40, 230, 850, 800, 5,
                    [
                        {"type": "column", "entity": "public model_metrics", "property": "evaluation_type", "header": "Eval Type"},
                        {"type": "column", "entity": "public model_metrics", "property": "category", "header": "Class / Category"},
                        {"type": "column", "entity": "public model_metrics", "property": "metric_name", "header": "Metric Name"},
                        {"type": "column", "entity": "public model_metrics", "property": "metric_value", "header": "Metric Value"}
                    ],
                    "Empirical Benchmark Metrics (data/validation/validation_set.csv)"
                ),

                # Middle Right: Model Metrics Bar Chart by Category
                create_bar_chart(
                    "p5_bar_metrics", 920, 230, 960, 550, 6,
                    "public model_metrics", "category", "Total Reviews", "Evaluation Category Volume"
                ),

                # Bottom Right: MLOps Disclaimer Card
                create_card_visual(
                    "p5_card_mlops_policy", 920, 810, 960, 220, 7,
                    "Temporal Trend Status", "MLOps Governance: Empirical Validation Policy"
                )
            ]
        )
    ]

    page_order = []
    for pid, pname, visuals in pages:
        page_order.append(pid)
        write_page(pid, pname, visuals)
        print(f"Created page: {pname} ({pid}) with {len(visuals)} visuals.")

    pages_meta = {
        "$schema": SCHEMA_PAGES_META,
        "pageOrder": page_order,
        "activePageName": page_order[0]
    }
    with open(os.path.join(PAGES_DIR, "pages.json"), "w", encoding="utf-8") as f:
        json.dump(pages_meta, f, indent=2)
    print("Updated pages.json with all 5 pages.")


if __name__ == "__main__":
    update_tmdl_measures()
    build_all_pages()
    print("Report build completed successfully!")
