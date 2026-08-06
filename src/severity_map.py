"""
Explicit mapping of TfL statusSeverity codes to analytical categories.

Design principle: no code is classified by inequality shortcuts (e.g.
"severity < 10 means disrupted"). Every code is mapped deliberately, because
the TfL severity scale is not monotonic: 10 is "Good Service", lower numbers
are generally worse, but codes above 10 exist (e.g. 20 "Service Closed") and
some codes are informational rather than disruptive.

Verify this table against the live API before relying on results:
    GET https://api.tfl.gov.uk/Line/Meta/Severity
and update docs/severity_mapping.md with the date of verification.

Returns (is_disrupted, is_excluded):
    is_disrupted - counts toward disruption metrics
    is_excluded  - excluded from denominator (e.g. "Not Running" outside
                   operating hours is not evidence of unreliability)
"""

# code: (description, is_disrupted, is_excluded)
SEVERITY_TABLE = {
    0:  ("Special Service",        True,  False),
    1:  ("Closed",                 True,  False),
    2:  ("Suspended",              True,  False),
    3:  ("Part Suspended",         True,  False),
    4:  ("Planned Closure",        True,  False),  # analysed separately via is_planned
    5:  ("Part Closure",           True,  False),
    6:  ("Severe Delays",          True,  False),
    7:  ("Reduced Service",        True,  False),
    8:  ("Bus Service",            True,  False),
    9:  ("Minor Delays",           True,  False),
    10: ("Good Service",           False, False),
    11: ("Part Closed",            True,  False),
    12: ("Exit Only",              True,  False),
    13: ("No Step Free Access",    False, True),   # accessibility info, not reliability
    14: ("Change of Frequency",    True,  False),
    15: ("Diverted",               True,  False),
    16: ("Not Running",            False, True),   # typically outside operating hours
    17: ("Issues Reported",        True,  False),
    18: ("No Issues",              False, False),
    19: ("Information",            False, True),
    20: ("Service Closed",         False, True),   # scheduled closure, e.g. overnight
}


def classify_severity(code):
    """Return (is_disrupted, is_excluded) for a TfL statusSeverity code.

    Unknown codes are flagged as excluded and disrupted=False so they never
    silently inflate or deflate metrics; they surface in QA queries instead.
    """
    if code in SEVERITY_TABLE:
        _, disrupted, excluded = SEVERITY_TABLE[code]
        return disrupted, excluded
    return False, True
