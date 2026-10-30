# Hole size from WITSML bit runs: experiment and decision

Status: rejected as a hole-size source. Kept as evidence only.

## Question

ADR 0002 D7 gives each daily-drilling-report hole section a hole size from the report's
`diaHole`. Many sections never state one (`hole_size_source = 'unknown'`), so their lost time
cannot be attributed to a hole size. The question was whether WITSML bit runs, meaning BHA runs
whose tubular assembly holds a component typed as a bit with a stated diameter, could fill the
gap, with precedence report > bit size > unknown. Report comment text was not considered.

## Coverage

Only 31 of 161 WITSML BHA runs link to a bit with a stated size. Only 14 of the 26 wellbores
with drilling reports have BHA runs at all.

## Rule comparison

Each candidate rule was tested on the sections where the report also states a hole size
(agreement within 0.01 in, bit size rounded to 1/8 in). The last column counts unknown-size
sections that would gain a size.

| Rule | Agrees | Disagrees | Unknown sections gaining a size |
|---|---|---|---|
| Bit run starts inside the section | 4 | 6 (plus 4 with several sizes) | 3 |
| Bit run with the largest time overlap | 14 | 2 | 6 |
| Latest bit run at or before the section's stated start | 15 | 3 | 54 |
| Same, run started within 7 days before the stated start | 14 | 2 | 10 |

The unbounded "latest bit run" rule fills the most sections, but it reaches back weeks, often
from completion or workover sections to a bit used in an earlier drilling section.

The best-bounded rule (the last row) disagrees with the report in 2 of 16 sections where both
exist. The likely causes are:

- a 36 in hole drilled with a 26 in bit below a hole opener whose size is not in the data;
- a 12.25 in shoe drill-out bit that was still the latest run when the next section started.

## Recovery

Under the best-bounded rule, 10 of 156 unknown-size sections gained a size (nine 8.5 in, one
5.5 in). These sections hold 103.5 h of the 4,792.0 h of interruption time with no hole size,
about 2 %.

## Mislabel on 15/9-F-11 T2

Section 4 of 15/9-F-11 T2 is the plug-back and kick-off after the 8.5 in section reached TD. The
reports state no hole size for it, and 0 m of new hole was drilled in it. The bit rule labelled
it "8.5 in" from the latest bit run (8.5 in, started 2013-05-06, within 7 days of the section's
stated start). That label is a statement about the bit on the string, not the hole being drilled,
and it would merge plug-back time into the 8.5 in hole section's lost time.

## Decision

Bit size is not used as a hole-size source. `hole_size_source` stays 'report' or 'unknown',
and 15/9-F-11 T2 section 4 is of unknown size. The reasons:

- it recovers about 2 % of the unknown-size interruption time;
- it disagrees with the report in 2 of 16 checkable sections;
- where it fills a gap, it can describe the bit rather than the hole, as on 15/9-F-11 T2.

The lookup is kept as `dim_hole_section.bit_size_evidence_in`: evidence only, never used as hole
size. It uses the best-bounded rule above.
