# London Transport Reliability Analytics

**Identifying persistent disruption across TfL services using longitudinal baseline deviation**

*Author: Peace Osemegbe Okoegwale — [LinkedIn](https://linkedin.com/in/peace-okoegwale-md-815254306)*

---

## The business question

Which TfL lines experience the most frequent or severe disruption, when does disruption occur, and — most importantly — **which services are deviating from their own normal operating baseline?**

Raw disruption counts are misleading. A line with heavy weekend engineering works can look "unreliable" while actually being well maintained. A line with few disruptions can be quietly degrading against its own history. This project measures each line against **itself**, using a 28-day rolling baseline to flag periods of meaningful departure from normal performance.

This is longitudinal change detection: the same analytical discipline used in clinical safety monitoring (detecting deterioration against a patient's own baseline), applied to transport infrastructure.

## Key findings

> *This section is updated as data accumulates. Findings below reflect the current collection window.*

1. **[Finding 1 — e.g. "The X line showed a sustained deviation of N points above its 28-day baseline during the week of DD/MM, driven primarily by signal failures."]**
2. **[Finding 2 — e.g. "Unplanned disruption is concentrated in weekday peak windows (07:00–09:30), while ~80% of weekend disruption is planned engineering work — the two must be analysed separately."]**
3. **[Finding 3 — e.g. "Severity-weighted scoring reorders the reliability ranking: line Y has fewer disruptions than line Z but a worse weighted score due to longer suspensions."]**

## How it works

```
TfL Unified API  ──►  Python collector (scheduled)  ──►  SQLite (timestamped observations)
                                                              │
                                                              ▼
                                              SQL analysis (window functions,
                                              baseline deviation, severity weighting)
                                                              │
                                                              ▼
                                              Power BI / Tableau dashboard
```

1. **Collect** — `src/collector.py` polls the TfL Line Status endpoint on a fixed cadence and stores raw, timestamped observations. Collection gaps are logged so distorted days can be flagged or excluded.
2. **Validate** — severity codes are mapped explicitly against TfL's published severity list (see *Data quality* below). Nothing is inferred silently.
3. **Analyse** — `sql/analysis.sql` computes disruption rates, planned vs unplanned splits, severity-weighted scores, and each line's deviation from its own 28-day rolling baseline.
4. **Present** — a dashboard with four pages: Executive overview, Line performance, Root-cause analysis, and Baseline deviation.

## Data quality and limitations

Honest analysis states its limits. The ones that matter here:

- **Severity mapping is explicit, not assumed.** TfL's `statusSeverity` scale is not monotonic ("Good Service" = 10, but codes above 10 exist, e.g. closures). Every code is mapped to disrupted / not disrupted / excluded in `src/severity_map.py`, with the mapping documented in `docs/severity_mapping.md`.
- **Planned vs unplanned disruption is separated.** Scheduled engineering works are identified from disruption category and reason text and analysed separately, so maintenance does not masquerade as unreliability.
- **Disruption rate depends on consistent polling.** The collector logs every run; days with collection gaps above a threshold are flagged in the data and excluded from baseline calculations.
- **Cold start.** The 28-day rolling baseline is null for a line's first 28 days of observation; deviation metrics are only reported once a full baseline window exists.
- **Observation ≠ duration.** Disruption rate measures the share of observations showing disruption, which approximates duration only at consistent polling intervals. This is stated on the dashboard.

## Technical evidence

Python (requests, scheduling, JSON parsing) · SQLite · SQL window functions · date/time analysis · explicit data validation · severity-weighted metric design · Power BI / Tableau · analytical writing

## Repository structure

```
src/            Python collection pipeline
sql/            Analysis queries
dashboard/      Dashboard file + screenshots
docs/           Severity mapping, methodology notes
data/           SQLite database (gitignored; sample extract included)
```

## Running it yourself

```bash
pip install -r requirements.txt
python src/collector.py --once      # single collection run
python src/collector.py             # continuous collection (default: every 10 min)
python src/build_analysis.py        # run SQL analysis, export CSVs for the dashboard
```

An optional free TfL API key (register at api-portal.tfl.gov.uk) raises rate limits; set it as the environment variable `TFL_APP_KEY`.

---

*Data source: Transport for London Unified API, used under the TfL open data licence. This is an independent analytical project and is not affiliated with or endorsed by TfL.*
