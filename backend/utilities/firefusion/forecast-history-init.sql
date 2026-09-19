-- FireFusion forecast history.
-- Records every prediction served on GET /api/bushfire-forecast, so the
-- system can answer "what did the dashboard show at time X" for after-action
-- review, and drive a time slider over recent risk trend. See
-- docs/forecast-history.md.

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', 'public', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';
SET default_table_access_method = heap;

-- Remove old objects first so the script can run cleanly again.
DROP TABLE IF EXISTS forecast_history CASCADE;

-- Written best-effort from ForecastService.store_prediction(): a write
-- failure here must never block live forecast delivery, so this table can
-- legitimately have gaps.
CREATE TABLE forecast_history (
    id BIGSERIAL PRIMARY KEY,

    -- The same timestamp already written to the predictions:generated_at
    -- Redis key, not a second notion of when this forecast was produced.
    generated_at TIMESTAMPTZ NOT NULL,

    -- The FeatureCollection actually served (type + features), as returned
    -- by ForecastService.store_prediction(). Freshness meta is derived at
    -- read time, not stored, so it stays correct relative to when it's read.
    payload JSONB NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Every query (point-in-time lookup, window scan, retention prune) filters
-- on generated_at.
CREATE INDEX forecast_history_generated_at_idx ON forecast_history (generated_at DESC);
