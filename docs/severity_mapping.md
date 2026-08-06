# Severity mapping methodology

Every TfL `statusSeverity` code is explicitly mapped in `src/severity_map.py`
to one of three analytical treatments: disrupted, not disrupted, or excluded.

## Why not "severity < 10 = disrupted"?

The TfL scale is not monotonic. 10 is "Good Service" and lower codes are
generally worse, but codes above 10 exist (11 "Part Closed", 20 "Service
Closed") and some codes are informational (13 "No Step Free Access",
19 "Information") rather than evidence of unreliability. An inequality filter
would silently misclassify these.

## Exclusions and rationale

| Code | Description         | Treatment | Rationale |
|------|---------------------|-----------|-----------|
| 13   | No Step Free Access | Excluded  | Accessibility information, not service reliability |
| 16   | Not Running         | Excluded  | Typically outside operating hours |
| 19   | Information         | Excluded  | Informational only |
| 20   | Service Closed      | Excluded  | Scheduled closure (e.g. overnight) |

Planned closures (code 4 and planned works identified from disruption
category/reason text) are *included* but flagged `is_planned = 1` and analysed
separately, so maintenance is never conflated with unreliability.

## Verification

Verify against the live list before trusting results:

    GET https://api.tfl.gov.uk/Line/Meta/Severity

Last verified: [DATE — update when you run this]

Unknown codes are auto-excluded and surfaced by the QA query in
sql/analysis.sql, so new codes fail loudly rather than silently.
