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

## Baron, Herald and structures: review-v4

This section supersedes the earlier unsupported-status notes for Baron, Herald,
towers and inhibitors. Movement and life-state decoding are unchanged.

### Independently identified name hashes

`0x023D` announcement decoded object fields are four-byte plaintext writes:
actor name hash `+0x10`, category identifier `+0x18`, target name hash `+0x1C`,
and acting team `+0x20`. The hashes use lowercase ASCII SDBM:
`h = (h * 65599 + byte) mod 2^32`, starting at zero. This reproduces champion
names (Syndra `0x404673AB`, Ashe `0xDA1E294F`, TwistedFate `0xD04DE692`)
and independently identifies `SRU_Baron = 0x68AC12C9`,
`SRU_RiftHerald = 0xDDAF53D2`, `Turret = 0x07B471D0`.
These name identities are VERIFIED; most category strings remain UNKNOWN.
The final byte-obfuscated object snapshot must not be read as plaintext.

### VERIFIED objective credits, paired notifications

`0x0119` is a generic script-event envelope. Object `+0x20` identifies the
observed neutral-death script (`0x60FD8A21`), `+0x10` points to its byte vector,
`+0x18` gives logical length, and `+0x28` gives its credited entity. Other
script identifiers are ignored. The relevant script's 124-byte decoded body
has a `0x1D7` tag, repeated dead entity IDs at `+4` and `+12`, the SDBM unit-name
hash at `+108`, and credited entity at `+120`. These are offsets in the
deserialized script body, not the ROFL payload. All range, tag and duplicated
identity checks precede normalization.

Production requires a same-tick `0x023D` announcement matching target hash,
killer champion name and killer team. Four Baron kills and four Herald kills
across five real replays match every participant's independent `BARON_KILLS`
and `RIFT_HERALD_KILLS` metadata. On the primary fixture, a separate research
decode of generic unit-death opcode `0x043C` also matches each objective's
dead entity, killer entity and timestamp. Its deserializer is
`0xF09E20`–`0xF0A39D`, constructor `0xE8AAF0`–`0xE8AC33`; it is not needed
in production, avoiding emulation of thousands of unrelated unit deaths.

Primary Herald: approximately 1080.885 seconds, Naafiri. Primary Baron:
approximately 1470.800 and 1917.455 seconds, both Naafiri. Their recorded
notification times are preserved; no more precise damage instant is claimed.
Map coordinates and exact pit positions are not decoded or invented.

Important negative fixture: `5640901584` includes a Herald self-removal at
1185.214593 seconds near match end. Script killer equals the dead neutral
entity; the matching announcement's actor equals its target and its team is
300. This is excluded from captures, consistent with zero Herald credits.
The script and announcement must agree before this exclusion applies.

An earlier two-occurrence candidate, `0x02F3`, actually decodes the name
`SRU_Crab`; its frequency is not evidence of Baron kills and it is not enabled.

### VERIFIED tower and inhibitor destruction

Tower normalization correlates three sources:

- `0x0463`: destroyed tower is the block parameter, actual final-hit entity
  is decoded object `+0x1C`.
- `0x0406`: credited entity at object `+0x10`, destroyed tower at `+0x14`.
- `0x023D`: target name hash `Turret`, acting team. Destroyed team is the
  opposite blue/red team, verified against `FRIENDLY_TURRET_LOST` for each team.

The actual final hitter and credited participant can differ. At 1040.206s in
`5640962900`, a minion finishes a tower but `0x0406` credits Vladimir. All
53 tower notifications match team loss totals; separate credit IDs match all
50 participant `TURRETS_KILLED` totals. No player credit is inferred from gold.

Inhibitor normalization pairs `0x0431` with `0x023D` category `0x18564B76`.
The category's original string is UNKNOWN; its inhibitor interpretation is
VERIFIED by the independent evidence below. `0x0431` uses its block parameter
for building identity, object `+0x10` for credited entity and `+0x14` for final
hitter. This opcode also occurs for the nexus, so **it alone is not an
inhibitor event**. Only the correlated inhibitor announcement enables emission.

All ten inhibitor events across five matches match each player's
`BARRACKS_KILLED` total. In the original replay, Syndra receives the first
credit at 1815.491852s while a minion is the final hitter. The same building
entity `0x40000091` changes state again at 2115.466361s (approximately 300s
later), then is destroyed again at 2162.175973s. The corresponding `0x03CD`
state packets independently support destruction/respawn behavior; unknown
state encoding is not exported as a guessed inhibitor lifecycle.

Team ownership is derived from the verified opposing acting team, not from a
guessed entity-ID range. Lane, tier, structure position and complete structure
respawn state remain UNKNOWN. Source coordinates in shared death objects can
describe the killer; they are deliberately not plotted as structure locations.

| Fixture | Baron | Herald | Towers | Inhibitors |
| --- | ---: | ---: | ---: | ---: |
| NA1-5640196741 | 2 | 1 | 15 | 4 |
| NA1-5640893952 | 0 | 1 | 12 | 3 |
| NA1-5640901584 | 0 | 0 | 3 | 0 |
| NA1-5640933743 | 2 | 1 | 12 | 1 |
| NA1-5640962900 | 0 | 1 | 11 | 2 |

### Exact-build functions and maintained boundaries

| Decoder | Constructor RVA range | Deserializer RVA range |
| --- | --- | --- |
| Announcement `0x023D` | `0xEAF430–0xEAF5CD` | `0x1039D00–0x103A5B0` |
| Script envelope `0x0119` | `0xEA1170–0xEA11F5` | `0x101DAB0–0x101E23A` |
| Tower death `0x0463` | `0xE8A9A0–0xE8AAE3` | `0xF098A0–0xF09E1D` |
| Tower credit `0x0406` | `0xE96C90–0xE96D34` | `0xF7B950–0xF7BF03` |
| Building death `0x0431` | `0xE86BE0–0xE86C73` | `0x10BA740–0x10BAC75` |

`parser/notifications.py` models the decoded structures with named dataclasses,
uses the existing hash-checked emulator, and normalizes only corroborated events.
No frontend ROFL dependency or raw packet dump is introduced. Normalized v1
events already support these types; source provenance adds credited entity and
corroborating/credit opcode fields. The decoder tag becomes `16.18-review-v4`;
objective and structure coverage become true for these supported categories.
Assists remain unavailable and are not inferred from the newly found credits.

Unknown semantic kinds are skipped. Recognized events with missing, conflicting
or ambiguous evidence fail closed. Simultaneous identical-actor tower events
that cannot be uniquely paired are unsupported rather than arbitrarily assigned.
IDs include type, timestamp, entity and payload digest, so a later destruction
of the same structure is a separate stable event.

`samples/notification-packets.json` contains small real payloads, timestamps,
hashes and the minimal final metadata needed to reproduce the five-match checks;
no player display names or client executable bytes are included. Recreate it
from the ignored research dumps with `python -m tools.export_notification_evidence`.
`tests/test_notifications.py` checks exact name hashes, normalization, credits,
negative self-removal, truncated packets, unknown kinds and missing/duplicate
evidence. Existing real-corpus tests exercise the complete parser pipeline.

## Event icon rendering and schematic annotations

`web/public/assets/events` contains original SVG line icons, with no external
icon service dependency. `eventIcons.ts` centralizes category, asset and color
selection; React uses the SVGs as masks and Pixi loads the same assets as three
cached objective sprites. The timeline preserves descriptive accessible button
names, keyboard focus, tooltips and review offsets. A text legend explains the
distinct shapes rather than relying on color alone.

Objective event rings use image annotations measured on the bundled 512×512
`map11.png`: dragon pit center `(343,360)`, shared Baron/Herald pit center
`(170,148)`. These are schematic image coordinates, **not decoded Riot world
coordinates**, and are never inserted into normalized replay JSON. They scale
with map size; the small icon badge is offset 36 render units above the ring
to avoid covering the champion cluster. Recorded event coordinates, when present,
take precedence over schematic anchors.

Badges are visible only during the 2.5 replay seconds following an actual
normalized objective kill. Pausing and seeking use replay time, including
backward seeks; this is not an alive/dead state or a guessed spawn timer.
The existing binary-search event-window helper remains responsible for lookup.
No structure locations are inferred: events without positions that are not
objectives receive no map annotation. Full structure map icons/state remain
pending reliable entity-to-location decoding.

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

## Persistent map entities: keyframe evidence (2026-09-13)

The important change is reading **keyframe packets**, in addition to the existing
`gameChunk` event decoder. Container framing and champion movement are unchanged.
`parser/map_entities.py` exports optional `mapEntities` in normalized schema v1;
the browser sees IDs, positions and timestamped state observations, not packets.
The decoder identifier is now `rofl-v2/16.18-review-v5`.

### VERIFIED: tower identity and position

| Source | Decoded object fields | Evidence |
| --- | --- | --- |
| Keyframe `0x0456` | `+0x18` entity; string `+0x30` tier; string `+0x40` map name | Embedded entity agrees with block parameter; 22 regular towers plus two excluded fountain lasers in every initial snapshot |
| Keyframe `0x0181` | plaintext f32 `+0x10/+0x14` world x/y; last u32 `+0x34` entity | Independent 0s, 60s and 120s snapshots agree on every tower position across five matches |
| Existing `0x0463` + credit/announcement correlation | destroyed tower entity and time | Every destruction maps to a named tower; destroyed team agrees with the map name |

The name `Turret_TOrder_L0_P2_3812066093_0` identifies blue bottom inner tower
`0x40000088`, at `(6919,1483)`. Order/Chaos identify blue/red. L0/L1/L2 map to
bottom/middle/top, corroborated by the decoded positions. Tier strings are
`SR_Outer`, `SR_Inner`, `SR_Inhibitor` (the tower guarding an inhibitor), and
`SR_Nexus`. Each team has three outer, three inner, three inhibitor towers and
two nexus towers. The two empty-tier fountain lasers are excluded.

Exact-build functions added to the checked profile:

| Packet | Constructor | Deserializer |
| --- | --- | --- |
| `0x0456` | `0xE95DC0–0xE96027` | `0xF19970–0xF1A81E` |
| `0x0181` | `0xE9BC50–0xE9BDD1` | `0x100DA00–0x100E2CB` |

Ordinary towers start alive in the initial keyframe and become destroyed at their
recorded event. **Nexus rebuild state is UNKNOWN after destruction**: replay
5640893952 destroys entity 0x40000094 at 1131.467261s and again at 1318.361826s.
Treating all towers as permanently destroyed would be false. Nexus icons therefore
fade with an explicit unknown-rebuild tooltip after the first destruction. Both
destruction events retain their individual IDs and map association.

### Objective observations, not simulated spawn timers

For Baron/Herald, verified kill entity IDs are matched to `0x0287` keyframe
records and same-entity `0x0181` positions. The full `0x0287` payload is **not**
claimed decoded. These matches establish observed presence before the known kill.
The marker starts at its first recorded keyframe and ends at the exact kill;
first observation is **not the exact spawn timestamp**. Positions are actual
keyframe coordinates, not schematic pit annotations. Pit neighborhoods are used
only as sanity checks. No objective that lacks corroborating observations is
manufactured, and no live marker is backdated from a kill alone.

For dragons, matching `0x0039` envelope parameters at the exact team-notification
time, followed by the keyframe identity/position checks, supplies 16 observed
entities across the five matches. This identity correlation is **LIKELY**, while
the sampled coordinates themselves are VERIFIED. Two of the original replay's
six dragons lack this complete corroboration and remain event-only. Elemental
subtype, unseen/un-killed objective presence, precise spawn/respawn instants and
presence before the first matching keyframe remain UNKNOWN.

| Match | Persistent towers | Observed dragons | Heralds | Barons |
| --- | ---: | ---: | ---: | ---: |
| 5640196741 | 22 | 4 | 1 | 2 |
| 5640893952 | 22 | 3 | 1 | 0 |
| 5640901584 | 22 | 2 | 0 | 0 |
| 5640933743 | 22 | 4 | 1 | 2 |
| 5640962900 | 22 | 3 | 1 | 0 |

### Unresolved inhibitor identity and research tools

`0x03CD` decodes a u16 at object +0x10 and bytes at +0x12/+0x13. The primary
inhibitor's known death has last plaintext +0x13=0; its later return candidate
has +0x13=1 and +0x10=300. However, keyframes use IDs such as 0x40000191 while
some game-stream deaths use 0x40000091. No generic alias rule is established.
Similarly, `0x04DA` on the rebuilt nexus tower changes bit masks, but sometimes
uses 0x40000194 instead of 0x40000094. These observations are research evidence,
not normalized lifecycle events. Resolve this identity relationship before adding
inhibitor placement or nexus rebuild transitions.

Local patch-matched map assets were inspected using CommunityDragon Toolbox
(https://github.com/CommunityDragon/CDTB, research-only installation). The public
map configuration is at
https://raw.communitydragon.org/16.18/game/data/maps/shipping/map11/map11.bin.json.
The installed Map11 WAD contains `data/maps/mapgeometry/map11/base_srx.materials.bin`
with six named inhibitor visual-effect anchors, but no verified binding to the
replay IDs. Those anchors are not shipped as invented structure positions.

`tools/probe_packet.py` now accepts stream/entity filters and explicit research
runtime initialization. Its optional MSVC guard/TLS, stack-probe and logging
experiments affect private emulator memory only, never the installed executable.
Some candidates (notably complete neutral creation) still fail; none of those
experimental stubs is enabled in production map decoding. The production additions
use the existing hash-checked engine unchanged.

`tools/export_map_entity_evidence.py` generates `samples/map-entity-packets.json`
from the five private replays. Tests check all initial tower identities, teams,
tiers, stable IDs, later coordinate snapshots, event associations, monotonic
transitions and failure on missing/mismatched identity. Full replays, player
names, map binaries and executable code are not included in this small fixture.

To refresh a previously normalized replay without redoing movement decoding:
`python -m tools.enrich_map_entities <actual.rofl> <cached.json>`.
The tool checks source SHA-256 and exact replay/client build before replacing JSON.
Normal uploads also populate map entities. Pixi uses one small container per
entity, updates state at 10 Hz with binary search, and keeps champion animation
on its ticker. Hover labels, map-entity visibility and backward seeking are supported.


## Void Grubs: partial camp-announcement coverage (2026-09-13)

**VERIFIED:** exact-build `0x023D` decoded announcement target +0x1c is
SDBM(`SRU_Horde`) = `0x8b8ab483`; category +0x18 is `0xcb5a3f01`.
Actor +0x10 and team +0x20 match the credited champion/team. Four corpus
announcements coincide with a `0x043C` unit death whose decoded +0x1c is that
champion's network ID. The dying entity is the death block's envelope parameter.
An independent `0x0119` neutral-death script at the same timestamp repeats that
entity at vector +4/+12/+120 and decoded object +0x28. This script describes
self-removal and has no usable target-name hash: it must NOT supply killer credit.
The existing neutral script tag/length checks apply (0x1d7, 124 bytes).
Unit-death decoder: RVA F09E20�F0A39D; constructor E8AAF0�E8AC33. All offsets
are decoded client-object fields, not raw packet offsets. Exact client hash remains required.

| Replay suffix | Time (seconds) | Dying entity | Credited participant (zero based) |
|---|---:|---|---:|
| 196741 | 652.348090 | 0x40005310 | 1 (Graves) |
| 893952 | 535.992147 | 0x400041f3 | 1 |
| 901584 | 533.004874 | 0x40003a21 | 6 |
| 933743 | 885.022018 | neutral cleanup | none; excluded |
| 962900 | 532.142000 | 0x40003dc1 | 1 |

The last match has four simultaneous generic death packets. Matching the script
entity is essential; timestamp and killer alone are ambiguous. Every credited
participant has positive final HORDE_KILLS. This is a corroboration, not a claim
that the emitted events sum to final stats. Primary Graves has three final kills,
but only one camp-announced kill is currently normalized.

**LIKELY:** the announcement is issued when the camp resolves. Its full trigger
semantics are not established. We therefore label events `CAMP_ANNOUNCED_KILL_ONLY`
and do not call this a complete individual kill feed or assign a count of three.
A neutral team-300 announcement in 933743 is cleanup and never becomes a capture.

**UNKNOWN:** identification of earlier individual grub deaths, exact spawns and
positions. The four dying entities appear in `0x0287` keyframes (first observations
near 480 seconds) but have no matching `0x0181` position records. No persistent
grubs are emitted. The UI's brief pit flash is a labeled map-image annotation,
not decoded entity coordinates. Next: decode neutral creation identity/position
fields in `0x0287`, then correlate all individual `0x043C` deaths and reconcile
per-player HORDE_KILLS across the corpus before claiming complete coverage.

Correction to the earlier plan: do not assume two grub spawns. Riot removed the
second spawn in [patch 25.09](https://www.leagueoflegends.com/en-au/news/game-updates/patch-25-09-notes/).
No spawn timers from those notes are used to manufacture replay state.

Fixtures: `samples/grub-packets.json` contains relevant real announcement, script,
death, and neutral snapshot bytes from all five files, without participant names.
`tests/test_grubs.py` re-decodes them, tests ambiguity/missing evidence, verifies
stable IDs, excludes neutral cleanup, and asserts that missing position evidence
does not create live markers. `tools/discover_grubs.py` reproduces fixture export
from the existing private announcement research dumps and actual ROFL files.
Normalized decoder version is now `rofl-v2/16.18-review-v6`. The added optional
objective coverage field and `VOID_GRUB` category preserve schema version 1;
movement tracks and all previous event IDs are unchanged.


## Individual Void Grubs and persistent placement (v7, 2026-09-13)

This supersedes the partial-coverage limitations immediately above.

**VERIFIED identity/position prefix:** `0x0287` decoder entry F16B60 can run
without experimental runtime patches through F19037. That instruction is the
common successful continuation after the unit-name decoder and its success check
(F1902F test / F19031 failure branch). The later unsupported field at F192B4
calls E734D0 and enters client logging; the complete packet remains unsupported.
The production profile deliberately stops at F19037 and does NOT bypass that
later field or claim a successful complete decode. The wrapper checks RIP at the
boundary and RSP at the verified prologue depth (five pushes + 0x20 = 0x48).
Early failure returns to the emulator's synthetic stop address but has a different
stack depth, so it is rejected. Truncated prefixes and mismatched entity IDs are
tested. A valid prefix with an unexamined tail is intentionally not a full-packet
validity check. No TLS, logging, allocator, or game-client modifications were added.
The existing engine and exact executable hashes still gate this patch profile.

Decoded object fields:

| Offset | Meaning / confidence |
|---|---|
| +0x2c | VERIFIED network ID; must equal block parameter |
| +0x38 | VERIFIED instance-name string, e.g. SRU_Horde.12.1 |
| +0xa0 | VERIFIED unit-name string: SRU_Horde for grubs |
| +0x60 | VERIFIED position x (last plaintext f32 write) |
| +0x64 | LIKELY height; not exported |
| +0x68 | VERIFIED position z, exported as normalized planar y |
| +0x6c..+0x74 | UNKNOWN secondary vector; not used |

The x/z values match the separately decoded `0x0181` position records exactly
at matching timestamps for dragons, Herald, and Baron in the primary fixture.
This independently establishes axis order; no pit coordinates are manufactured.
Each corpus replay identifies these three separate units:

| Instance | Initial world x | Initial world y |
|---|---:|---:|
| SRU_Horde.12.1 | 4841.942871 | 10638.950195 |
| SRU_Horde.12.2 | 4790.000000 | 10182.446289 |
| SRU_Horde.12.3 | 5210.000000 | 10424.000000 |

**VERIFIED individual deaths:** match the `0x043C` envelope ID to those decoded
identities and read the established killer field +0x1c. Every player's emitted
kill count must equal final HORDE_KILLS, and prior camp-announced kills must be
an identical-ID/credit subset. Across the five matches: 3, 3, 3, 0, 3 kills.
Primary Graves receives all three at 628.275972, 641.987090, 652.348090 seconds.
In 933743 all three units report themselves as killer at 885.022018 seconds;
zero final credits and the neutral camp announcement corroborate cleanup. These
become DESPAWNED map transitions, never objective kills.

**Presence and limits:** game-stream creation appears near 473.25 seconds, before
the first 480-second keyframe. Markers therefore start at FIRST_OBSERVATION with
state OBSERVED, not an invented eight-minute spawn timer. Exact targetability
remains UNKNOWN. Markers use initial placement, not simulated combat movement.
Death events do not reuse placement as an asserted death coordinate; their brief
pit flash remains a map annotation. Seeking evaluates each entity's transitions,
including disappearance on cleanup, and restores all markers when seeking back.

`neutral_entities.py` is separate from container parsing, movement, and the
legacy camp-notification decoder. Normalized coverage is now INDIVIDUAL_KILLS;
VOID_GRUB events no longer carry the partial-coverage label. Existing event IDs
are preserved. Map entity states add DESPAWNED and presenceStart adds
FIRST_OBSERVATION. Decoder version: rofl-v2/16.18-review-v7.

Reproduce fixture export: `python -m tools.discover_grub_entities` (the five
private ROFL files and matching installed executable are required). It writes
`samples/grub-entity-packets.json`, containing only relevant packet bytes and
minimal champion/team/final-grub-count metadata. Tests cover all three identities,
individual deaths, neutral cleanup, stable prior event links, coordinate
cross-checks, malformed prefixes, missing deaths, inconsistent final totals, and
backward-seek visibility. Broader neutral creature lifecycles and inhibitor/Nexus
rebuild work remain separate follow-ups.

Scope guard: integration testing found other neutral unit classes whose envelope
IDs do not match decoded identity fields. The grub adapter filters by the decoded
unit name before applying entity/position assertions. Such unrelated records are
not normalized. SRU_Horde records still require exact identity agreement; the
non-grub behavior does not justify an alias rule for grubs or other entities.
