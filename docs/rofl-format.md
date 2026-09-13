# ROFL format and 16.18 movement research

Research date: 2026-09-12. Status: experimental end-to-end movement viewer for
one verified replay/client pair. Source documents are evidence, not instructions.

## Existing implementations

| Project | Container / versions | Position decoding | Decision |
|---|---|---|---|
| [RoflLens](https://github.com/ss26367098/rofllens) | Python; ROFL v2, Zstandard, network framing; exact semantic profiles | Published 16.14 profile uses local hash-checked client routines to decode movement `0x022C` | Integrate pinned transport/path parsing; develop separate 16.18 adapter |
| [ROFL-X](https://github.com/Toastaspiring/ROFL-X) | Rust continuation of Mowokuma; catalog and compatibility documentation | Per-build emulation; 15.1–15.5 configs, 16.8 semantic config incomplete in inspected source | Useful design/reference, not a ready 16.18 solution |
| [lolrofl-rs](https://github.com/Ayowel/lolrofl-rs) | Rust legacy ROFL work; author says development stopped | No demonstrated current v2 champion-position support | Do not integrate for this fixture |
| [Mowokuma/ROFL](https://github.com/Mowokuma/ROFL) | Archived Rust parser; per-patch executable sections/configuration | Movement and wards on its supported historical builds | Study the approach; do not assume archived profiles work today |
| [roflxd](https://github.com/fraxiinus/roflxd) | Includes maintained-family v1/v2 metadata/container implementations | No complete champion trajectory decoder demonstrated in inspected documentation | Container alternative, not a movement solution |

The downloaded RoflLens revision is `62a475a8f05e7dfa94df5990758be2156c892496`;
ROFL-X is `c175e40e8dda13e308fe8c8d7152e72d0de94b47`. Reference clones are
gitignored. RoflLens supplies an MIT-licensed Python dependency; no upstream
semantic-version checks were disabled in the production adapter.

**Decision:** Python/FastAPI provides the fastest evidence-driven MVP because
the usable transport and research implementation is Python. Rust remains a
reasonable later replacement behind `ReplayParser.parse(path)` and the normalized
JSON contract. Container support does not imply gameplay-protocol support.

## Generic ROFL v2 transport

The pinned reader separates header, chunk framing, optional Zstandard
decompression, trailing signature boundary, and JSON participant metadata.
After decompression, a separate block reader handles timestamp/opcode reuse,
parameter deltas, and payload lengths. An unknown opcode remains a framed block.
The frontend never receives those structures.

The v2 layout inspected here is:

```text
header
chunk records and stored bodies
256-byte signature region
metadata JSON
u32 little-endian metadata length
```

The header ends at byte 29 in this fixture. A chunk record uses `<IBIII>`:
u32 chunk ID, u8 slot, u32 stream field, u32 raw size, and u32 compressed size.
The stream ID is the high byte of the stream field (`stream_raw >> 24`).
Consult [upstream container source](https://github.com/ss26367098/rofllens/blob/62a475a8f05e7dfa94df5990758be2156c892496/src/rofllens/container.py)
for the exact field extraction. The parser verifies structural boundaries, not
Riot's cryptographic signature authenticity.

## Supplied fixture: measured facts

| Property | Observed value |
|---|---|
| Source | `NA1-5640196741.rofl`, kept outside source control |
| Bytes | 20,722,656 |
| SHA-256 | `d2758074c6c538f09f8dc8650da904228c0c8e88b53b603f667a9b84c5cd6581` |
| Client | `16.18.817.5716` |
| Protocol digest | `f6a10af08504a7ee` |
| Duration | 2,193.710 seconds |
| Chunk records | 113: 74 gameChunk, 37 keyframe, 1 startKeyframe, 1 startSentinel |
| Network blocks | 2,413,360 total; 1,971,319 gameChunk |
| Distinct opcodes | 262 across all streams |
| Signature boundary | 20,621,570 |
| Metadata offset / length | 20,621,826 / 100,826 |

The ten metadata entries match the supplied blue/red roster. Account IDs are not
exported into the normalized model. `samples/fixture-report.json` contains the
sanitized measurements and full **gameChunk-only** histogram. `tools/probe_replay.py`
can additionally export raw examples into ignored local research storage.

## 0x022C is not the 16.18 movement opcode

Generate the histogram **before** assigning packet names. On this fixture:

- `0x022C`: zero gameChunk occurrences.
- `0x004C`: 51,264 gameChunk occurrences; 51,301 across all streams.
- The 16.18 constructor for `0x022C` is anchored at RVA `0xEA8A27`, with
  deserializer `0x102E270`. Its field layout differs from the old movement buffer.
- The 16.18 constructor for `0x004C` is anchored at RVA `0xEBCC77`.
  Its vtable identifies deserializer `0x104F430`, ending at `0x104F82C`.
  The decoded byte vector starts at object offset `0x18`, with **u32** length
  at `0x20` and capacity at `0x24`.

These addresses were discovered from the **matching local executable**, not by
adding offsets to the 16.14 profile. `tools/inspect_client.py` finds opcode
constructor anchors; `tools/disassemble.py` prints the relevant local code.

Executable SHA-256:
`6c3a62afa3d62b66db8a777140c4338979bdb56b87242446570fe6b118f40095`.
No executable bytes or extracted PE sections are distributed by this project.

## Decoder evidence

Offline emulation first decoded real `0x004C` payloads. The research profile
used return-check RVA `0x1256800`, malloc RVA `0x11B9530`, and free RVA
`0x11B9560`; stubs existed only inside Unicorn's private memory. League was
not started or modified. This recovered coherent path records at time 0.146,
including ten champion entities at the opposing spawn corners.

For runtime performance, `parser/patch_16_18.py` translates the narrow byte-buffer
logic. It processes selector bits, encoded varints, and a byte mapping derived
from the local executable's table at `0x1B92E90`. The buffer is filled alternately
from its front and back. Treating it as a sequential copy produces invalid paths.
Unresolved header fields are skipped structurally, without assigning meanings.

Validation performed:

1. Compare translated buffers byte-for-byte with offline emulation for the first
   30 packets plus every 1,000th packet: **81 matches**, zero mismatches.
2. Parse all **51,264** movement packets: zero buffer, framing, speed, or path
   structure failures; each decoded buffer is consumed completely.
3. Find ten persistent entities `0x400000AE`–`0x400000B7`, beginning at 0.146s
   and with final updates after 2,180s.
4. Extract **56,432** champion-origin records. Timestamps are monotonic; world
   x ranges 132–14,592 and y ranges 136–14,672.
5. Plot origins on the map and inspect at 3:00 and later timestamps. Top laners
   occupy the upper-left lane, mid occupies center, and bot pairs the lower-right.
6. Upload the actual source file through the browser and verify the API returns
   normalized data, icons appear, and playback updates positions.

The normalized model includes observed first waypoints and the recorded route. The path-record
structure follows the known `<u16 flags, u32 entity, f32 speed>` prefix, optional
flag byte, delta bitmap, and compact coordinates. Additional waypoints are exported
under `path`, not as timestamped observations: future destinations do not have
independent sample timestamps. `parser/movement.py` decodes deltas as signed i8
with signed i16 wrapping, correcting upstream's unsigned-byte interpretation.

To validate this interpretation, project each command along its route at its
recorded speed and compare with the next observed origin 0.03–1 seconds later.
Across 23,061 comparisons where signed and unsigned routes differ, signed deltas
give median error **7.89 world units** (22,723 within 50), versus **89.61** for
unsigned deltas (5,944 within 50). Reproduce with
`python -m tools.check_path_deltas C:\\path\\NA1-5640196741.rofl`.
This is trajectory evidence, not a claim of exact simulation parity.

The playback regression was visible in Malphite's command at 17.215s: its route
goes from (620,750) to (1400,10284), speed 824.625, with no next origin until
29.073s. Holding gaps over ten seconds discarded this real movement. Playback
now traverses the commanded route, stops at its endpoint, and uses the next
observed origin when it arrives. Routes are interrupted immediately by new commands.

## Player identity and confidence boundary

The profile maps entity `0x400000AE + participantIndex` to the original metadata
order, matching the convention used by existing parsers. It does **not** sort
players by role before mapping. This produces:

| Entity | Champion | Team / role |
|---|---|---|
| 0x400000AE | Malphite | BLUE TOP |
| 0x400000AF | Graves | BLUE JUNGLE |
| 0x400000B0 | TwistedFate | BLUE MIDDLE |
| 0x400000B1 | Ashe | BLUE BOTTOM |
| 0x400000B2 | Seraphine | BLUE UTILITY |
| 0x400000B3 | Camille | RED TOP |
| 0x400000B4 | Naafiri | RED JUNGLE |
| 0x400000B5 | Syndra | RED MIDDLE |
| 0x400000B6 | Vayne | RED BOTTOM |
| 0x400000B7 | Shaco | RED UTILITY |

Spawn grouping and early laning corroborate the mapping in this fixture. A
16.18 hero-spawn decoder that directly ties champion identity to entity IDs is
not yet implemented. Thus this mapping is a tested profile convention, not a
claim that identity names were extracted from movement payloads. Additional
fixtures and hero-spawn identity decoding are the next confidence improvements.

## Coordinates and sampling

Path-origin coordinate conversion after buffer decoding:

```text
world_x = signed16(encoded_x) * 2 + 7358
world_y = signed16(encoded_y) * 2 + 7412
```

Here `y` means the ground-plane axis, often called `z` in 3D game code; it is
not altitude. The selected map bounds are x `[0,14716]`, y `[0,14824]`, based
on twice the compact-coordinate centers. These are calibration bounds, not
an assertion that every point in the rectangular image is walkable terrain.
The official Data Dragon schematic is 512 × 512; Pixi uses an 800 × 800 logical
canvas scaled to the available display size.

```text
image_x = (world_x - minX) / (maxX - minX) * imageWidth
image_y = (maxY - world_y) / (maxY - minY) * imageHeight
```

World origin is southwest; image origin is northwest, so image y is inverted.
There is no additional translation or clamp. The transform is centralized and
takes configurable bounds. Center `(7358,7412)` maps to `(400,400)`. Tests also
plot the extreme corners and a custom non-square coordinate domain. The developer
overlay prints true world coordinates and logical map pixels separately.

Observed origins are irregular; per-champion median gaps in this fixture range
from 0.167 to 0.301 seconds. There is no fixed 60 Hz resampling. The renderer uses
elapsed time and recorded speed along route segments. It never extrapolates beyond
the endpoint. Speed changes between updates and missing recall semantics can
still cause corrections at the next origin. Verified deaths now hold the champion
at its death location until an actual respawn notification. Old JSON without routes
retains the original hold/interpolation fallback; re-upload to obtain route data.

## Version handling and next decoding work

Production decoding requires exact client version **and** protocol digest,
followed by executable SHA-256 validation. New patches need their own decoder
adapter and evidence. Unknown opcodes are skipped, while malformed container or
supported movement payloads produce typed errors. Map 11 is an explicit current
profile assumption; there is no claimed support for other maps or modes.

Next reverse-engineering steps: independently decode assist credit,
then objectives and structures using exact-build constructor/vtable evidence.
The champion-death evidence below now confirms the ten base entity identities.
Dragons, Baron, Herald, towers, inhibitors, wards, health, vision and combat
remain undecoded. Final metadata totals alone cannot supply event timestamps.

## Phase 2: champion kills and deaths (16.18)

**VERIFIED on the supplied fixture:** `gameChunk` opcode **0x0475**, 75 packets.
Do not reuse RoflLens's 16.14 `0x036F` opcode or object offsets. Its death decoder
was useful as a structural reference, not as a compatible decoder. The 16.18
constructor anchor is `0xE99401`; PE unwind records give constructor
`0xE993F0` through return `0xE99572`. The constructor sets vtable `0x1B87DE0`,
whose deserializer is `0xF1B3A0`, ending at `0xF1BD06`.

The production adapter uses RoflLens's offline Unicorn engine and the exact-hash
profile `parser/profiles/16.18-events.json`. It reads sections from the user's
matching executable at runtime. The repository includes only addresses/hashes,
not game code. The existing translated movement decoder remains unchanged.
Constructor execution is necessary to initialize the nested victim record's
vtable; skipping it fails at the indirect call at `0xF1B78D`.

| Decoded object field | Interpretation | Confidence and validation |
|---|---|---|
| `+0x30`, final 4-byte write | Victim network ID | VERIFIED; all 75 names and per-player death totals agree |
| `+0x38` u64 pointer, `+0x40` u32 length | Victim champion UTF-8 name in private heap | VERIFIED; names match metadata and base entity mapping on all 75 packets |
| `+0x58`, final 4-byte write | Killer network ID | VERIFIED; opposing team and all ten final kill totals agree |
| `+0x48` pointer / `+0x50` count | Combat-context records | LIKELY combat context; contains champions and jungle units, NOT verified assists |
| `+0x10`, `+0x14`, `+0x5C`, `+0x60` | Additional scalars | UNKNOWN semantics; not exported as gameplay stats |

The final **4-byte write**, rather than the final object snapshot, supplies a
plaintext entity ID. Later individual byte writes re-obfuscate that field.
Named parsing constants and bounds checks live in `parser/events.py`.

Validation covers every occurrence, not just a count match:

- All victim IDs resolve to their decoded champion names, with no team conflicts.
- Per-player kills: `12,4,7,8,2,16,7,10,5,4`; deaths:
  `7,13,9,8,5,3,4,9,8,9`, in original participant order. Both vectors exactly
  match independent trailing metadata. Parsing rejects mismatched totals.
- All 75 timestamps also match the complete timestamp sequences of companion
  opcodes `0x04DC`, `0x00E7`, and `0x01A4`. Their payload meanings remain UNKNOWN.
  Some companion block parameters differ by 0x100; these parameters are not used
  as participant IDs. The decoded death IDs consistently use the base range.
- Transport timestamps are retained as seconds; normalized times round to six
  decimals. Stable IDs combine rounded milliseconds, victim ID and a payload
  SHA-256 prefix. IDs do not depend on event sorting or array indexes.
- Four packet fixtures in `samples/death-packets.json` retain source payloads,
  timestamps and expected fields. `tools/probe_events.py` and
  `tools/discover_deaths.py` reproduce the offline investigation. Private full
  observations stay under ignored `samples/local`.

First independently decoded events:

```text
01:02.370  CHAMPION_KILL  Syndra → TwistedFate
03:44.314  CHAMPION_KILL  TwistedFate → Shaco
05:10.794  CHAMPION_KILL  Seraphine → Vayne
05:18.889  CHAMPION_KILL  Ashe → Shaco
```

Champion deaths are represented by the victim of each `CHAMPION_KILL`; no duplicate
death event is added. A non-player killer may be omitted. Assists are omitted
(unavailable), not an empty list implying no assists. Current K/D comes from
events at or before the replay time. Final K/D/A, level, gold and minion totals
come from metadata and are displayed exclusively under **Final match stats**.

**LIKELY location:** 56 of 75 events have an observed victim movement origin no
more than 0.5 seconds earlier. Those coordinates are attached with their own
source timestamp and LIKELY coordinate confidence. They support a subtle 2.5s
ring, not a claim of exact death coordinates. The other 19 events omit location.
The event's verified killer/victim confidence is separate from location confidence.

**UNKNOWN / unsupported:** assists, dragon subtype/kills, Herald,
Baron, tower and inhibitor destruction, and current HP/level/gold/CS/items/spells.
Final objective totals exist but cannot establish event time, so no objective or
structure events are manufactured. Next: correlate candidate notifications with
objective totals and exact-build decoded names; validate several occurrences and
additional replays before enabling those event types.

## Phase 3: verified respawns and rejected assist candidate (2026-09-13)

The local replay folder contains just one file on the supported exact build.
`NA1-5636332267` and `NA1-5636363575` are both `16.17.810.4348`, digest
`3714cb24566263e2`; they cannot validate the 16.18 semantic profile. The older
fixture now has an integration test asserting an unsupported-version error.
No cross-patch compatibility is claimed.

**VERIFIED:** opcode `0x01B3` is the respawn notification on this fixture.
Its constructor is `0xE88460`–`0xE884FC`, anchor `0xE88467`, vtable
`0x1B87D60`, deserializer `0xF09620`–`0xF0989F`. This leaf constructor has
no PE unwind entry; its start/return were checked in disassembly explicitly.

| Field | Meaning | Evidence |
|---|---|---|
| Network block parameter | Champion entity ID | VERIFIED: all 71 are exact base-range participant IDs; every event pairs with a preceding verified death |
| Decoded object `+0x10`, last u32 write interpreted as f32 | Spawn world x | VERIFIED: finite team spawn coordinate, corroborated by the following movement update |
| Decoded object `+0x14`, last u32 write interpreted as f32 | Spawn world y | VERIFIED: same check, using the existing planar axes |
| Decoded object `+0x18` scalar | UNKNOWN | Not labeled as HP, speed or another gameplay statistic |
| Block timestamp | Recorded return time | VERIFIED: all 71 agree with independently decoded timer expiry within one 33ms server tick |

The blue notification position is `(394,461)` and red is `(14340,14391)`.
Subsequent movement origins use quantized coordinates and can reflect spawn
offsets; all 71 have a movement observation within 0.2 seconds and 300 world units.
The notification coordinates are used during the short interval before that
first movement sample, avoiding a stale corpse position at respawn.

Independent timer check: the `0x00E7` death-notification candidate has constructor
`0xE8ACD0`–`0xE8AE13`, decoder `0xF0A660`–`0xF0ABDD`. Decoded object `+0x1C`
matches the killer in all 75 death records; `+0x54` contains the delay to return.
For all 71 in-match respawns, notification minus (death time + delay) is
**0.0007–0.0334 seconds**, median **0.0170 seconds**. The other four expiries
are beyond the match duration. Research correlation checks time, killer and the
victim parameter; some companion parameters include an additional 0x100 of
UNKNOWN semantics. Production does not mask it or depend on that timer packet.

Production uses the actual `0x01B3` events and validates chronological death →
respawn pairing. An orphan respawn, repeat death without a respawn, invalid
participant, or impossible location fails clearly. The four unpaired final
deaths (TwistedFate, Seraphine, Ashe, Syndra) remain unpaired; future events are
not manufactured. Respawn IDs are stable hashes with time and player, and each
event references its `deathEventId`. `metadata.eventCoverage.respawns` gates
frontend life-state rendering for backward compatibility.

**REJECTED assist interpretation:** death context records are 0x30-byte entries,
with entity at +0x18 and name pointer/length at +0x20/+0x28. Even retaining only
records whose entity AND champion name match metadata, excluding the killer and
deduplicating each event, produces assist totals:

```text
Candidate: 7,6,8,11,14,8,9,15,7,16
Metadata:  8,5,8,11,13,7,9,15,6,14
```

This both misses and overcounts credits. Some context records have a champion
entity ID but a jungle-unit name. Neither raw context IDs nor filtered contributors
are suitable for an assist feed. Opcode `0x02CA` also happens to occur 106 times,
the sum of final assists, but its timing and recipient distribution contradict
an assist-credit interpretation. It is not decoded or labeled in production.

Reproduction: run the existing death discovery, then:

```powershell
python tools/probe_packet.py --opcode 0xe7 --entry 0xf0a660 --constructor-anchor 0xe8ace3 --all
python tools/probe_packet.py --opcode 0x1b3 --entry 0xf09620 --constructor-anchor 0xe88467 --constructor-start 0xe88460 --constructor-end 0xe884fc --all
python -m tools.validate_life_research samples/local/review.json
```

Research dumps stay private in `samples/local`. Sanitized results are in
`samples/lifecycle-evidence.json`; four real respawn payload fixtures are in
`samples/respawn-packets.json`. Tests cover all real respawns and unchanged kill
totals, malformed packets, stable IDs, unsupported 16.17 input, lifecycle pairing,
boundary seeking, countdowns, corpse holds and trail discontinuities.

## Dragon notifications and assist-credit audit (five replay corpus)

The four newly supplied files have the same supported client version
`16.18.817.5716` and protocol digest. They all pass movement, participant,
kill-total and lifecycle validation without changing the movement decoder.

| Replay | Movement samples | Kill + respawn events | Dragon notifications (Blue / Red) |
| --- | ---: | ---: | ---: |
| NA1-5640196741 | 56,432 | 146 | 2 / 4 |
| NA1-5640893952 | 37,603 | 64 | 0 / 3 |
| NA1-5640901584 | 35,706 | 76 | 2 / 0 |
| NA1-5640933743 | 59,746 | 164 | 0 / 4 |
| NA1-5640962900 | 37,965 | 164 | 3 / 0 |

### VERIFIED: team dragon notification, `0x002D`

Exact client constructor RVA `0xEA0120`–`0xEA0228`; deserializer
`0xF1E520`–`0xF1ED4D`. The constructor writes opcode `0x002D` at
`0xEA0127`. These are offline emulated client functions, under the same
executable/section hash checks as the death decoder.

The last **two-byte** write to decoded object `+0x10` is team 100 or 200.
Subsequent individual byte writes obfuscate it again, so reading the final
object snapshot directly is wrong. This is a decoded structure offset, not
a guessed offset in the raw payload.

Evidence: all 18 packets across five matches match both total and per-team
`DRAGON_KILLS` metadata exactly. The first write to object `+0x28` also equals
the team's number of previously killed dragons, separately for each team
throughout these matches (0, 1, 2, 3). That counter interpretation is LIKELY;
it is not exported. The packet's team interpretation is further supported by
the initial fixture's recorded locations: Naafiri is near the dragon pit at
all four red notifications; Graves is near it at the later blue notification,
and Seraphine at the earlier one. These agree with their final individual
dragon credits, but do not establish a general individual-killer decoder.

Original replay notification timestamps (seconds):
`402.442898 RED`, `767.132833 BLUE`, `1093.803009 BLUE`,
`1418.763… RED`, `1749.739… RED`, `2078.976703 RED`.
The precise raw timestamps and all 18 payload fixtures are preserved in
`samples/dragon-packets.json`; normalized timestamps retain six decimals.
The original replay has **six** dragon kills: Naafiri 4, Graves 1, Seraphine 1.

UNKNOWN: the vector at object `+0x18`, elemental subtype/hash mapping,
individual killer, Elder behavior and notification-to-death delay at finer
than game tick precision. No subtype, player ID or map coordinate is invented.
Baron, Herald and structure notifications remain unsupported.

Production emits `OBJECTIVE_KILL / DRAGON` with team, stable payload-derived
ID, timestamp and source confidence. It validates final team totals and fails
closed on disagreement. This is notification time; it is not claimed to be
an independently measured exact damage/death instant. Existing timeline and
feed support provide the ten-second review lead-in. Coverage adds optional
`dragons: true`; `objectives: false` continues to mean incomplete coverage of
the full objective category. Decoder tag advances to `16.18-review-v3`.

### Assist credit: an additional attractive heuristic rejected

`0x003B` deserializer `0x10D1D90`–`0x10D215D`, constructor
`0xE8BF10`–`0xE8BFE9`, yields a float at object `+0x10` and participant entity
at `+0x14` (last four-byte writes). LIKELY: a gold-award notification. At the
first kill it awards Syndra 400 and Shaco approximately 106.142. It also
appears for ordinary small awards, including approximately 1.02, outside kills.
No victim or award-reason field has been established.

A research-only rule taking opposing-team, non-killer recipients of awards
greater than 2 at the same kill timestamp perfectly matches all ten final
assist totals in the original replay. Independent fixtures falsify it:

- 5640893952: Jax candidate 2, metadata 1.
- 5640901584: all aggregate totals match (still not per-event proof).
- 5640933743: Twisted Fate candidate 13, metadata 12.
- 5640962900: Naafiri 13 vs 14, Amumu 6 vs 7, Jinx 18 vs 19.

It both overcounts and misses credits. Simultaneous kills and unrelated gold
awards make time-only association ambiguous. The threshold is a deliberately
tested heuristic, not a protocol field. `assistingPlayerIds` remains omitted
and coverage remains false. `samples/assist-award-evidence.json` records the
five comparisons; `tools/audit_assist_awards.py` reproduces them from private
probe dumps. Next: establish an explicit stat/credit increment or award reason
and victim association, and verify individual events across this corpus.

Other probes: `0x023D` has notification-like hashes and a team, but no verified
assist list; `0x00A9` has two floats and an entity, with unrelated later updates.
The `0x03E4` emulator probe requires an unresolved runtime memory dependency;
it was stopped and none of its output accepted. No arbitrary memory stub was
added to make that candidate appear to work.

Reproduce a candidate using the existing cached research profile:

```powershell
python tools/probe_packet.py --opcode 0x2d --entry 0xf1e520 --constructor-anchor 0xea0127 --constructor-start 0xea0120 --constructor-end 0xea0228 --all --replay 'C:\path\replay.rofl' --output samples/local/dragon-probe.json
python tools/probe_packet.py --opcode 0x3b --entry 0x10d1d90 --constructor-anchor 0xe8bf17 --constructor-start 0xe8bf10 --constructor-end 0xe8bfe9 --all --replay 'C:\path\replay.rofl' --at-events samples/local/replay.json --output samples/local/gold-probe.json
python tools/audit_assist_awards.py samples/local/replay.json samples/local/gold-probe.json
```

`--at-events` uses a two-microsecond tolerance because normalized timestamps
are rounded to six decimals; decimal-bucket equality can drop genuine matches.
Candidate probes stop at their first decoding error. They never update the
production profile automatically.

## Reproduce the offline comparison

Install `requirements-dev.txt`. Clone the two reference repositories only if
you want to read their source; the following scripts use the installed dependency.
After producing `samples/local/probe.json` with `tools/probe_replay.py`:

```powershell
.\.venv\Scripts\python.exe -m rofllens profile-skeleton 'C:\Riot Games\League of Legends\Game\League of Legends.exe' --client-version 16.18.817.5716 --protocol-digest f6a10af08504a7ee --output-root samples/local/profiles
.\.venv\Scripts\python.exe tools/probe_decoder.py
.\.venv\Scripts\python.exe tools/extract_candidate_paths.py 'C:\path\NA1-5640196741.rofl'
```

These deliberately separate research scripts use the single profile under
`samples/local/profiles` and hard-coded, documented 16.18 candidate addresses.
Do not point them at another build. `probe_decoder.py` writes a local candidate
profile to permit research observation; it does not change the production profile
or upstream's installed files. The extraction script writes path evidence and
reports parity assertions as failures, not verified movement.
