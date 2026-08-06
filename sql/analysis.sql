-- ===========================================================================
-- TfL Service Reliability Analysis
-- Corrected and extended from original draft:
--   * removed duplicate disruption_rate column
--   * uses explicit is_disrupted / is_excluded flags instead of severity < 10
--   * separates planned vs unplanned disruption
--   * adds severity-weighted disruption score
--   * handles baseline cold start (first 28 days per line return NULL and
--     are excluded from deviation reporting)
--   * flags days with collection gaps via observation-count threshold
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- 1. Daily performance per line (unplanned disruption is the headline metric)
-- ---------------------------------------------------------------------------
WITH daily_performance AS (
    SELECT
        line_name,
        DATE(observed_at_utc) AS observation_date,
        COUNT(*)                                              AS observations,
        SUM(CASE WHEN is_disrupted = 1 AND is_planned = 0
                 THEN 1 ELSE 0 END)                           AS unplanned_disrupted,
        SUM(CASE WHEN is_disrupted = 1 AND is_planned = 1
                 THEN 1 ELSE 0 END)                           AS planned_disrupted,
        -- severity weighting: suspensions count more than minor delays
        SUM(CASE
                WHEN is_disrupted = 1 AND severity_level IN (1, 2)      THEN 3.0  -- closed/suspended
                WHEN is_disrupted = 1 AND severity_level IN (3, 5, 11)  THEN 2.0  -- partial
                WHEN is_disrupted = 1 AND severity_level = 6            THEN 1.5  -- severe delays
                WHEN is_disrupted = 1                                   THEN 1.0  -- other disruption
                ELSE 0
            END)                                              AS weighted_disruption
    FROM line_status_history
    WHERE is_excluded = 0
    GROUP BY line_name, DATE(observed_at_utc)
),

-- ---------------------------------------------------------------------------
-- 2. Data quality gate: flag days with too few observations to be reliable
--    (expected observations per day = 24h * 60 / POLL_MINUTES; threshold 80%)
-- ---------------------------------------------------------------------------
quality_gated AS (
    SELECT
        *,
        CASE WHEN observations >= 115 THEN 1 ELSE 0 END AS is_complete_day
    FROM daily_performance
),

-- ---------------------------------------------------------------------------
-- 3. Reliability rates (complete days only)
-- ---------------------------------------------------------------------------
reliability AS (
    SELECT
        line_name,
        observation_date,
        unplanned_disrupted * 1.0 / observations   AS unplanned_rate,
        planned_disrupted   * 1.0 / observations   AS planned_rate,
        weighted_disruption * 1.0 / observations   AS weighted_score
    FROM quality_gated
    WHERE is_complete_day = 1
)

-- ---------------------------------------------------------------------------
-- 4. Baseline deviation: each line against its own previous 28 complete days
--    Cold start handled: deviation is NULL until a full 28-day window exists.
-- ---------------------------------------------------------------------------
SELECT
    line_name,
    observation_date,
    ROUND(unplanned_rate, 4)  AS unplanned_rate,
    ROUND(planned_rate, 4)    AS planned_rate,
    ROUND(weighted_score, 4)  AS weighted_score,
    ROUND(AVG(unplanned_rate) OVER w28, 4) AS baseline_28d,
    CASE
        WHEN COUNT(*) OVER w28 < 28 THEN NULL   -- cold start: incomplete window
        ELSE ROUND(unplanned_rate - AVG(unplanned_rate) OVER w28, 4)
    END AS deviation_from_baseline
FROM reliability
WINDOW w28 AS (
    PARTITION BY line_name
    ORDER BY observation_date
    ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING
)
ORDER BY line_name, observation_date;


-- ===========================================================================
-- Supporting queries (run separately; used for dashboard pages)
-- ===========================================================================

-- Weekday vs weekend, unplanned only (planned works would swamp weekends)
-- SELECT
--     line_name,
--     CASE WHEN CAST(STRFTIME('%w', observation_date) AS INTEGER) IN (0, 6)
--          THEN 'Weekend' ELSE 'Weekday' END AS day_type,
--     ROUND(AVG(unplanned_rate), 4) AS avg_unplanned_rate
-- FROM reliability
-- GROUP BY line_name, day_type;

-- Root-cause categories from reason text (top recurring themes)
-- SELECT
--     CASE
--         WHEN LOWER(reason) LIKE '%signal%'    THEN 'Signal failure'
--         WHEN LOWER(reason) LIKE '%points%'    THEN 'Points failure'
--         WHEN LOWER(reason) LIKE '%engineer%'  THEN 'Engineering works'
--         WHEN LOWER(reason) LIKE '%customer incident%'
--           OR LOWER(reason) LIKE '%passenger%' THEN 'Passenger incident'
--         WHEN LOWER(reason) LIKE '%staff%'     THEN 'Staff availability'
--         WHEN LOWER(reason) LIKE '%weather%'
--           OR LOWER(reason) LIKE '%flood%'     THEN 'Weather'
--         ELSE 'Other'
--     END AS cause_category,
--     COUNT(*) AS occurrences
-- FROM line_status_history
-- WHERE is_disrupted = 1 AND reason IS NOT NULL
-- GROUP BY cause_category
-- ORDER BY occurrences DESC;

-- QA: surface any unknown severity codes (should return zero rows)
-- SELECT DISTINCT severity_level, severity_description
-- FROM line_status_history
-- WHERE is_excluded = 1
--   AND severity_level NOT IN (13, 16, 19, 20);
