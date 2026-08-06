# Dashboard specification

Four pages. Build in Power BI (preferred for TfL/Thames applications) or Tableau.

## 1. Executive overview
- Total disruptions recorded (unplanned, headline)
- Most disrupted line (severity-weighted)
- Longest single disruption period
- Lines currently at Good Service
- Week-on-week reliability change

## 2. Line performance
- Reliability ranking (unplanned rate AND weighted score side by side —
  the reordering between them is itself a finding)
- Disruption over time (line chart per line)
- Severity distribution
- Average recovery time

## 3. Root-cause analysis
- Cause category breakdown (signal, points, engineering, passenger, staff, weather)
- Cause mix per line
- Planned vs unplanned split

## 4. Baseline deviation (the differentiator)
- Per line: daily unplanned rate vs its own 28-day rolling baseline
- Highlight periods where deviation exceeds a chosen threshold
- Annotate the largest deviations with their dominant cause category

## 5. Data quality note (footer or small page)
- Collection completeness by day
- Excluded days and why
- Severity mapping reference
