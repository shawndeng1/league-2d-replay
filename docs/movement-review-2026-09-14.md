# Movement review — 2026-09-14

## Controlled comparison

Both populations use the current renderer. The baseline removes only the seven
`positionOnly` observations from the current caches. This avoids mixing changes
from earlier rapid-turn interpolation with the Amumu supplement.

| Replay | Baseline flags | Updated flags | Added observation boundaries | Removed old boundaries |
| --- | ---: | ---: | ---: | ---: |
| NA1-5640962900 | 677 | 679 | 3 | 1 |
| NA1-5640901584 | 523 | 523 | 2 | 2 |
| NA1-5640933743 | 917 | 917 | 2 | 2 |
| Other replay a3657dbd88f3 | 393 | 393 | 0 | 0 |
| NA1-5640196741 | 844 | 844 | 0 | 0 |
| **Total** | **3354** | **3356** | **7** | **5** |

Flags are discontinuities of at least 30 world units outside known life
transitions, not confirmed protocol defects. No common flagged boundary changed
magnitude or hold duration. Every added flag is at an inserted observation.
The two extra flags at 933.029 and 1035.553 seconds reveal previously hidden
corrections before subsequent death events; the data does not establish their
travel path. A higher flag count here does not by itself show a regression.

At Amumu's 342.335 observation, the preceding hold is 1.837 seconds instead of
3.644 seconds until the old 344.142 movement observation. The earlier relocation
is about 712 units; the old discontinuity was about 722 units. It is an earlier
observation, not a reconstructed dash or a completely smooth movement fix.

Machine-readable evidence: `samples/supplemental-movement-audit.json`.
Run `npm run audit:movement` inside `web` to regenerate both the ordinary report
and `supplemental-comparison.json` with the current renderer.

## Diagnostic corrections

The audit now recognizes position-only samples as held observations, even without
speed/path fields. It previously could incorrectly report zero hold duration.

When a player has no decoded personal respawns, the audit uses decoded same-team
respawns as spatial evidence. It records `spawnEvidence: TEAM_RESPAWNS`; opponents
and unavailable respawn coverage are excluded. This correctly classifies five
Master Yi arrivals at (394, 462) in NA1-5640901584. It does not infer recall or
teleport events. Personal spawn evidence still takes precedence.

The updated hold categories are 95 small corrections, 279 arrivals at observed
spawn, 21 departures from observed spawn, and 66 unexplained relocations (461
total). Compared with the earlier 462-hold baseline, one Amumu hold falls below
the two-second threshold and five Yi arrivals receive spawn context.

## Next protocol candidate

A bounded raw-packet window at 990–1010 seconds in NA1-5640196741 contains a common
`0x02c4` action fingerprint, `0x008fa255`, before three large relocations:

| Champion | Action time | Next movement origin | Interval | Target error |
| --- | ---: | ---: | ---: | ---: |
| Twisted Fate | 994.375 | 1000.554 | 6.179 s | 26.21 units |
| Syndra | 996.880 | 1002.892 | 6.012 s | 23.49 units |
| Malphite | 1000.153 | 1006.444 | 6.291 s | 28.16 units |

Decoded origins agree with the stopped positions within 2.1 units. Each action
is paired with fingerprint `0x0a9306a0`, whose target equals its origin and is
therefore rejected by the target-correlation check. All three cases share a
small-packet sequence about three seconds after the first action, followed by
another sequence about 33 ms before the next movement origin. Their semantics
remain unknown.

This is **LIKELY target-correlated relocation evidence**, not a verified teleport,
completion notification, or trajectory. Same-cluster observations can be
correlated; they are not independent validation across matches. Broader full-match
scanning, cancelled/interrupted-action counterexamples, and the client consumers
of these packets must be checked before a production decoder is justified.

Portable evidence: `samples/relocation-cluster-fixture.json` and
`samples/relocation-cluster-summary.json`. The research command is
`python -m tools.analyze_relocation_candidates <decoded-actions.json> <normalized-replay.json> --output <report.json>`.
It never modifies normalized replay data. The local raw window and decoded action
rows are in `samples/local/movement-audit/relocation-cluster-*.json`.

## Validation

50 frontend tests pass, including five real teammate-spawn examples, opponent and
coverage exclusions, position-only hold accounting, and controlled comparison
without mutating the replay. The production frontend build passes. Seven focused
Python research tests pass, including two new relocation-correlation checks for
identity, clock, target, finite coordinates, and real observed destinations.
No new production packet decoder or playback heuristic was introduced in this review.
