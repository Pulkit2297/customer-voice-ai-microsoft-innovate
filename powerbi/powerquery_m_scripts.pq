// ============================================================================
// CustomerVoice AI - Power Query (M) Scripts for PostgreSQL Ingestion
// ============================================================================
// Target Database: PostgreSQL / Supabase
// Local Instance:  localhost:5434 | Database: customervoice_db
// Supabase Cloud:  db.[project-ref].supabase.co:5432 | Database: postgres
//
// These scripts connect directly to the relational tables in PostgreSQL,
// strictly avoiding raw CSV files and preserving semantic data lineage.
// ============================================================================

// ----------------------------------------------------------------------------
// 1. Connection Parameters (Configured for your Supabase Cloud Database)
// ----------------------------------------------------------------------------
// Parameter: Server
// Description: Hostname and port of your Supabase PostgreSQL instance
let
    Server = "db.ehmgeoakcckhagdjjmmr.supabase.co:5432" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
in
    Server

// Parameter: Database
// Description: Database name
let
    Database = "postgres" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
in
    Database


// ----------------------------------------------------------------------------
// 2. Fact Table: FactReviews
// ----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(Server, Database),
    public_reviews = Source{[Schema="public",Item="reviews"]}[Data],
    #"Filtered Rows" = Table.SelectRows(public_reviews, each true),
    #"Changed Type" = Table.TransformColumnTypes(#"Filtered Rows",{
        {"review_id", type text},
        {"review_text", type text},
        {"cleaned_text", type text},
        {"rating", type number},
        {"review_date", type date},
        {"product_id", type text},
        {"campaign", type text},
        {"source", type text},
        {"pii_detected", type logical},
        {"pii_types", type text},
        {"created_at", type datetimezone}
    }),
    #"Added Rating Status" = Table.AddColumn(#"Changed Type", "Rating_Availability", each if [rating] = null then "Unavailable (NULL)" else "Recorded", type text),
    #"Added Date Status" = Table.AddColumn(#"Added Rating Status", "Date_Availability", each if [review_date] = null then "Unavailable (NULL)" else "Recorded", type text)
in
    #"Added Date Status"


// ----------------------------------------------------------------------------
// 3. Fact Table: FactSentiment
// ----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(Server, Database),
    public_sentiment_results = Source{[Schema="public",Item="sentiment_results"]}[Data],
    #"Changed Type" = Table.TransformColumnTypes(public_sentiment_results,{
        {"id", Int64.Type},
        {"review_id", type text},
        {"sentiment", type text},
        {"sentiment_score", type number},
        {"confidence", type number},
        {"model_name", type text},
        {"model_version", type text},
        {"created_at", type datetimezone}
    }),
    #"Normalized Sentiment Class" = Table.TransformColumns(#"Changed Type", {{"sentiment", Text.Proper, type text}}),
    #"Added Sentiment Score Bucket" = Table.AddColumn(#"Normalized Sentiment Class", "Sentiment_Polarity_Group", each 
        if [sentiment_score] >= 0.05 then "Positive"
        else if [sentiment_score] <= -0.05 then "Negative"
        else "Neutral", type text
    )
in
    #"Added Sentiment Score Bucket"


// ----------------------------------------------------------------------------
// 4. Bridge Table: BridgeTopics
// ----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(Server, Database),
    public_topics = Source{[Schema="public",Item="topics"]}[Data],
    #"Changed Type" = Table.TransformColumnTypes(public_topics,{
        {"id", Int64.Type},
        {"review_id", type text},
        {"topic", type text},
        {"topic_confidence", type number},
        {"is_primary", type logical},
        {"created_at", type datetimezone}
    }),
    #"Formatted Topic Name" = Table.TransformColumns(#"Changed Type", {{"topic", each Text.Replace(_, "_", " "), type text}}),
    #"Proper Topic Case" = Table.TransformColumns(#"Formatted Topic Name", {{"topic", Text.Proper, type text}})
in
    #"Proper Topic Case"


// ----------------------------------------------------------------------------
// 5. Dimension Table: DimProducts
// ----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(Server, Database),
    public_products = Source{[Schema="public",Item="products"]}[Data],
    #"Changed Type" = Table.TransformColumnTypes(public_products,{
        {"product_id", type text},
        {"product_name", type text},
        {"category", type text},
        {"created_at", type datetimezone}
    })
in
    #"Changed Type"


// ----------------------------------------------------------------------------
// 6. Fact Table: FactAlerts
// ----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(Server, Database),
    public_alerts = Source{[Schema="public",Item="alerts"]}[Data],
    #"Changed Type" = Table.TransformColumnTypes(public_alerts,{
        {"alert_id", type text},
        {"alert_type", type text},
        {"severity", type text},
        {"product", type text},
        {"topic", type text},
        {"metric", type text},
        {"previous_value", type number},
        {"current_value", type number},
        {"percentage_change", type number},
        {"message", type text},
        {"created_at", type datetimezone},
        {"status", type text}
    })
in
    #"Changed Type"


// ----------------------------------------------------------------------------
// 7. Fact Table: FactModelMetrics
// ----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(Server, Database),
    public_model_metrics = Source{[Schema="public",Item="model_metrics"]}[Data],
    #"Changed Type" = Table.TransformColumnTypes(public_model_metrics,{
        {"id", Int64.Type},
        {"evaluation_type", type text},
        {"category", type text},
        {"metric_name", type text},
        {"metric_value", type number},
        {"validation_sample_size", Int64.Type},
        {"evaluation_timestamp", type datetimezone}
    })
in
    #"Changed Type"
