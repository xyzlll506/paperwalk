# A Small Windowed Lookup Study

Version: synthetic fixture 1. This is original fictional material for testing PaperWalk, not a published scientific result.

## Abstract

We compare full lookup with windowed lookup on twelve paired queries over eighteen ordered cards. Full lookup retrieves twelve targets and windowed lookup retrieves eleven. The smaller window examines fewer candidates but misses one distant target.

## Method

The same twelve queries are evaluated in both settings. Full lookup examines all eighteen cards. Windowed lookup examines six cards near the query anchor. We count a hit when the target card is included. This fixture illustrates reading coverage rather than supplying a reproducible benchmark.

## Equation 1

Mean candidate count is C = (c_1 + ... + c_12) / 12, where c_i is the number of examined cards for query i. A lower C represents fewer examined candidates; it is not a measurement of wall-clock runtime.

## Figure 1

```text
Full lookup:     [1][2][3][4][5][6] ... [17][18]
Windowed lookup:[1][2][3][4][5][6]
                                        ^ target missed
```

Figure 1 caption: The window near the beginning excludes a target at position eighteen. This schematic depicts the failure case; it is not a distribution of all query results.

## Table 1

| Method | Hits out of 12 | Mean examined candidates |
|---|---:|---:|
| Full lookup | 12 | 18 |
| Windowed lookup | 11 | 6 |

## Discussion

The window reduces candidate examinations in this constructed example but loses a long-range target. We do not measure runtime or uncertainty, so these observations do not establish a speedup or general accuracy advantage.

## References

This synthetic fixture cites no external publications.

## Appendix A

The failure query has its anchor at position one and its target at position eighteen. A six-card window cannot include both under this setup. This example limits any interpretation that reduced candidate count alone establishes equivalent retrieval quality.

## Declaration

All content and numbers are invented for software testing. No user-provided paper is redistributed here.
