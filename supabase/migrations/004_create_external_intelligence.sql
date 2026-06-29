-- External intelligence layer for BI agent enrichment.
-- This table stores curated market, logistics, and customer experience signals
-- gathered from approved external sources such as Brave Search MCP.
-- It intentionally remains separate from the core Olist warehouse facts and
-- dimensions so external context can be refreshed without changing historical
-- transactional metrics.

CREATE TABLE IF NOT EXISTS dim_external_intelligence (
    external_intelligence_sk BIGSERIAL PRIMARY KEY,
    intelligence_track TEXT NOT NULL CHECK (
        intelligence_track IN (
            'product_category_market',
            'geographic_logistics',
            'delivery_customer_experience'
        )
    ),
    entity_type TEXT NOT NULL,
    entity_value TEXT NOT NULL,
    intelligence_date DATE NOT NULL DEFAULT CURRENT_DATE,
    internal_metric_context JSONB,
    search_query TEXT NOT NULL,
    market_summary TEXT,
    target_customer_segment TEXT,
    business_recommendation TEXT,
    risk_or_challenge TEXT,
    source_titles JSONB,
    source_urls JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_dim_external_intelligence_track_entity_query
        UNIQUE (intelligence_track, entity_type, entity_value, search_query)
);

COMMENT ON TABLE dim_external_intelligence IS
    'Stores external market intelligence from controlled search tools, allowing BI analysis to compare Olist warehouse metrics with current market, logistics, and customer experience context without modifying core fact or dimension tables.';

COMMENT ON COLUMN dim_external_intelligence.intelligence_track IS
    'High-level intelligence track: product category market trends, geographic logistics context, or delivery customer experience signals.';

COMMENT ON COLUMN dim_external_intelligence.internal_metric_context IS
    'Optional JSONB snapshot of related internal BI metrics, such as revenue, late delivery rate, review score, or freight ratio, used to ground the external insight.';

COMMENT ON COLUMN dim_external_intelligence.search_query IS
    'Exact external search query used to gather the market intelligence, retained for reproducibility and auditability.';

COMMENT ON COLUMN dim_external_intelligence.source_titles IS
    'JSONB array of source titles returned by the external intelligence search.';

COMMENT ON COLUMN dim_external_intelligence.source_urls IS
    'JSONB array of source URLs returned by the external intelligence search.';

CREATE INDEX IF NOT EXISTS idx_dim_external_intelligence_track
    ON dim_external_intelligence (intelligence_track);

CREATE INDEX IF NOT EXISTS idx_dim_external_intelligence_entity
    ON dim_external_intelligence (entity_type, entity_value);

CREATE INDEX IF NOT EXISTS idx_dim_external_intelligence_date
    ON dim_external_intelligence (intelligence_date);
