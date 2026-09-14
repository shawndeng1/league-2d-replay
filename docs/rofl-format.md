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
Unit-death decoder: RVA F09E20–F0A39D; constructor E8AAF0–E8AC33. All offsets
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


## Display-only route reconciliation (2026-09-14)

NA1-5640962900 has frequent differences between the prior route's predicted
position at the next update and that update's recorded origin. Median errors for
short intervals are about 7–10 world units, with 95th percentiles around 32–43.
These produce small repeated visual snaps despite a smoothly running ticker.
No binary fields, timestamps, or normalized samples were changed.

For moving paths with multiple points and a next observation within two seconds,
the viewer linearly distributes the end residual over that interval when its
length is at most min(100, max(48, speed * interval * 0.5 + 8)) world units.
This bounded visual heuristic preserves route bends and arrives exactly at the
next real origin. It is not a claim of exact intermediate game simulation. Zero
speed, single-point paths and larger errors are not reconciled by this short-interval rule.
Life-state overrides still apply. Of 2,520 moving short intervals with at least
30 units of boundary error in this replay, 2,197 qualify; 323 larger differences
remain discontinuous pending actual movement/protocol evidence. Fixtures and
continuity tests cover three real champions; input JSON is never modified.

### Long-route timing: Master Yi and Ashe

VERIFIED from actual normalized observations in NA1-5640962900:

| Champion | Earlier time | Next time | Gap | Predicted progress | Observed route progress | Off-route error |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Master Yi | 21.937561 | 25.545068 | 3.607507s | 2846.77 | 2693.33 | 10.05 |
| Ashe | 17.127561 | 26.414068 | 9.286507s | 7447.69 | 7007.57 | 9.36 |

Distances are world units. Holding the earlier recorded speed constant overshoots
by roughly 154 and 440 units, then snaps backward at the next observation.
The prior two-second reconciliation limit missed both examples. UNKNOWN: exact
speed-change times and intermediate speed curve. No new protocol fields or
particular movement buffs are asserted by this change.

The viewer projects the next real origin onto the previous polyline. For gaps
in (2, 15] seconds, a projection within 32 units, more than 32 units from either
route endpoint, and observed/predicted progress ratio in [0.5, 1.25], it
interpolates observed distance along the route and a bounded lateral residual.
This is a display heuristic, not verified intermediate simulation. Finished
routes are excluded so idle time is not stretched into slow movement. Stops,
off-route relocations, and gaps outside these gates retain previous behavior.

Real sample pairs are stored in web/src/long-route-gaps.fixture.json. Tests step
both intervals at 60 Hz and assert forward progress without backward snaps,
boundary continuity, exact recorded endpoints, and unchanged input. Additional
cases cover route bends, finished routes, off-route relocations, and zero speed.
Existing Malphite coverage now expects observed-progress interpolation too.
No cache rebuild or backend restart is needed.

## Cross-replay movement audit (2026-09-14)

The offline TypeScript auditor imports the same samplePosition and
samplePlayerPosition functions as the viewer. It measures the visible jump
immediately before/at each unique observation timestamp, records corrections
of at least 30 world units, and separates known life transitions. Duplicate
timestamps use the renderer's last-update rule. A negative dot product against
the preceding 50ms of movement labels a backward correction. Predicted holds
use route length and recorded speed, not asserted game inactivity.

| Cached replay SHA prefix | Boundaries | Candidates outside known life transitions |
| --- | ---: | ---: |
| 09ed9f33cc67 | 37,955 | 702 |
| 3a968c92f7c5 | 35,696 | 542 |
| 971d3811c614 | 59,736 | 946 |
| a3657dbd88f3 | 37,593 | 406 |
| d2758074c6c5 | 56,422 | 897 |

VERIFIED: 227,402 boundaries examined; 3,493 remaining non-life candidates.
These are not confirmed defects. The largest corrections often follow roughly
eight-second holds and travel over 13,000 world units. LIKELY: many are recalls.
UNKNOWN: a packet-confirmed recall identity/timing for each case. No blanket
smoothing or recall events were introduced. The audit does not detect GPU frame
drops, speed discontinuities without a position jump, or every possible freeze.
Known life coverage can also be incomplete; non-life is a diagnostic category,
not proof that a transition was unrelated to a death.

### Ashe rapid direction changes, NA1-5640962900, 9-12 seconds

VERIFIED: a fresh gameChunk window contains 364 packets, including 29 packets
of 0x004c and 23 movement records for player 8 / entity 0x400000b6. All 23
timestamps (rounded as in production), routes, and speeds match the cached
normalized track exactly. Evidence is generated by tools/export_movement_window.py;
the inspected local dump is samples/local/movement-audit/ashe-packets.json.

At 9.110561 the recorded origin is (14482,14354), speed 806.875, route endpoint
(14312,14266). At 9.278561 the origin is (14450,14326) and a new route points
back toward (14572,14356). Constant-speed traversal predicts too much progress;
the viewer's bounded correction deliberately leaves a 94.81-unit backward snap.
Similar remaining corrections occur at 9.411561, 9.712561, and 10.280561.

UNKNOWN: whether movement start delays, turn handling, or separate speed state
explain the timing. Packet frequency alone does not identify these fields.
The window includes 0x0425 (132), 0x03ab (111), 0x0118 (22), and other packets;
none is newly labeled as speed/dash data. Next protocol step: compare the client
handlers and the currently unnamed 0x004c header fields across these observed
direction changes and ordinary straight movement. Establish field semantics
before changing sample timestamps or emitting additional movement state.

## Movement header investigation (2026-09-14, follow-up)

The matching local deserializer at RVA 0x104f430 writes a u32 at object +0x10
and a u16 at +0x14 before the vector at +0x18. Inline selectors for the u32 are
2 -> 2, 5 -> 0, 1 -> 1, 3 -> 0xffffffff; for the u16 they are 2 -> 65535,
6 -> 1, 4 -> 2, 3 -> 0. Other selectors consume the existing encoded varint.
These branches were inspected at 0x104f49e..637 and 0x104f644..7d3.

**VERIFIED:** the u16 equals the number of decoded records in every one of
195,041 gameChunk movement packets across the five replays below. It includes
all records, before filtering to champion entities. The production adapter now
checks this count, including empty buffers. Disagreement becomes the existing
MOVEMENT_DECODE_FAILED error instead of silently accepting a structurally valid
but incomplete path list. decode_movement_buffer remains available to older
callers; decode_movement_packet exposes the count and the unnamed u32 internally.
The normalized replay schema and playback timing are unchanged.

**UNKNOWN:** the u32's gameplay meaning. It never decreases in these files, but
monotonicity does not establish a clock. Treating u32 deltas as milliseconds
produced substantially worse route predictions on identical comparison sets:

| Replay | Packets/count matches | Comparisons | Transport median error | u32/1000 median error |
| --- | ---: | ---: | ---: | ---: |
| NA1-5640962900 | 35,346 | 23,764 | 7.31 | 103.74 |
| NA1-5640196741 | 51,264 | 36,847 | 7.03 | 103.88 |
| NA1-5640893952 | 31,271 | 23,118 | 7.85 | 97.50 |
| NA1-5640901584 | 27,944 | 24,426 | 6.83 | 91.90 |
| NA1-5640933743 | 49,216 | 40,134 | 6.96 | 96.67 |

Errors are world units. Comparisons require a moving multipoint route, transport
gap 0.03-1s, and candidate-header gap in (0,1]s; both predictors use exactly the
same pairs and the earlier recorded speed. Large errors are retained. This
rejects the tested clock interpretation, not every possible interpretation of
the field. No alternative timestamps are emitted. The 9-12s Ashe examples alone
were misleading: u32 values rise from 7747 to 10414 and superficially resemble
milliseconds, while full-match deltas drift far from transport time.

Reproduce with `python -m tools.movement_timing <replay.rofl> [more.rofl ...]`.
The ignored output is samples/local/movement-audit/timing.json; `--output` and
`--client` are configurable. A small real-packet fixture is committed at
samples/movement-header-fixture.json. Tests cover inline selector constants,
varint bounds/truncation, real decoded header values and record counts, empty
buffers, and count disagreement. No client executable bytes/tables are included.

The rapid-direction-change stutter is still unresolved. This investigation
rules out replacing replay timestamps with u32/1000 and adds a structural check;
it does not establish a speed-change, dash, recall, or movement-start-delay field.
The next useful evidence is the client consumer of the route records (rather
than only the deserializer), correlated with the known direction-change window.

The sanitized five-replay measurements are saved in
samples/movement-timing-report.json. Re-running all five through the production
count check produced identical timing reports and accepted all 195,041 packets.
Final targeted parser run: 39 tests passed, including the full original real-replay
movement integration. Unicorn emitted native access-violation diagnostics during
emulation, but this run completed successfully (exit 0); these diagnostics should
be investigated separately and are not claimed to be resolved by the header change.

## Rapid turns: bounded display correction (2026-09-14)

Static client tracing did not establish the movement-application function.
The 0x004c packet constructor at 0xebcc70 references vtable 0x1b8a928; its
0x3938c0 method returns object size 0x28 and 0x3891a0 frees the vector/object.
Neither is the movement consumer. A literal 0x4c near 0xc74036 led to a
boolean callback at 0xc53a00 rather than validated route application. These are
rejected leads; shared immediate values are not packet-handler identity evidence.
The exact turn timing remains UNKNOWN. No new movement packet is decoded here.

Independently of that unknown, the actual origin pairs establish an avoidable
display overshoot. Ashe's next origin at 9.278561 is near the earlier commanded
route, but constant-speed prediction travels beyond it before the new opposing
command arrives. The display can interpolate between observed origins without
claiming an exact turn-delay model.

The new rule requires all of the following:

- A moving multipoint route and next multipoint command within (0, 0.25]s.
- The next origin projects onto the earlier route interior within 16 world units.
- Observed progress is positive but less than the constant-speed prediction.
- The predicted endpoint differs from the observed origin by at most 100 units.
- The new command opposes the local previous-route direction (negative dot product).

For those intervals only, travel distance follows observed progress along the
polyline, with a bounded lateral residual to reach the real origin. This is
display interpolation, not a decoded motion state or newly fabricated samples.
Stopped/single-point commands, off-route corrections, and larger displacements
remain under the existing rules. Input samples are unchanged; seeking is stateless.

The full before/after boundary audit found:

| Replay SHA prefix | Non-life flags before | After | Removed |
| --- | ---: | ---: | ---: |
| 09ed9f33cc67 | 702 | 677 | 25 |
| 3a968c92f7c5 | 542 | 523 | 19 |
| 971d3811c614 | 946 | 917 | 29 |
| a3657dbd88f3 | 406 | 393 | 13 |
| d2758074c6c5 | 897 | 844 | 53 |

There were zero newly flagged boundaries and no increased jump among retained
flags. All removed jumps were at most 100 units. This audit measures positional
continuity, not exact gameplay fidelity or GPU frame timing. The remaining 3,354
candidates are not all defects. Summarized results: samples/rapid-turn-audit.json.

web/src/rapid-turns.fixture.json contains six raw-verified Ashe pairs and one
actual corrected pair from each of the other four replays (Camille, Yasuo,
Caitlyn, Malphite). Tests check monotonic progress without overshooting the next
origin, exact start/end positions, continuity and unchanged input, plus rejection
of larger/off-route reversals. Existing Yi/Ashe long-route and relocation tests
still pass. The frontend suite now has 44 passing tests.

## Holds and relocation evidence (2026-09-14)

The hold audit separates geometry from unsupported gameplay labels. Of 462
non-life HOLD_THEN_RELOCATION candidates across five replays, 95 have corrections
of at most 100 units, 274 arrive within 300 units of the player's own decoded
respawn positions, 21 leave that region, and 72 remain unexplained. If no decoded
respawn position is available, the audit does not assume one. These are diagnostic
categories; arrival at spawn does not establish a recall packet or channel time.
Long review links now include the hold, capped at 15 seconds of lead-in.
Summary: samples/hold-audit-summary.json. Local report:
samples/local/movement-audit/holds/report.md.

The longest hold in the affected replay is Diana's 106.646-226.693 interval,
ending with only a roughly 43-unit correction near spawn. It is not evidence of
120 seconds of missing walking. Other large relocations occur both toward and
away from spawn; they are intentionally not interpolated across the whole map.

### Amumu at 340.498318-344.142318 in NA1-5640962900

VERIFIED: fresh 0x004c decoding contains a single-point path at (7726,7412),
then no intervening movement sample for entity 0x400000b0 before (8216,7942).
Other packet types continue arriving during this interval. The bounded packet
export covers 338-346s, with 4,319 packets and 13 Amumu movement observations.
This is a gap in the supported position source, not proof of packet loss.

0x0062 (deserializer 0x103f6c0, constructor 0xeb72f0) writes three floats at
decoded-object +0x10/+0x14/+0x18 and an entity-like u32 at +0x1c. At 341.567318,
the planar floats are (8210.081,7934.297), entity 0x400000b5. Diana's recorded
origin is (8210,7934). At 342.939318 the floats are (8222.716,7982.593), again
0x400000b5, versus Diana's (8222,7982). LIKELY: target coordinates and target
entity. UNKNOWN: exact packet semantics. These are not accepted as Amumu's position.

0x04b5 (0xfe9950 / constructor 0xe8b940) yields an opaque 52-byte buffer in
four probed packets. No position or movement semantics were established.

### Candidate origin fields in 0x02c4

Deserializer 0x10d0760 (constructor 0xe8a8f0) produces scalar writes at:

| Decoded object fields | Observation | Confidence |
| --- | --- | --- |
| +0x5c, +0x6c | Match envelope champion entity in 200 sampled records | VERIFIED correlation; broader semantics UNKNOWN |
| +0x104/+0x108/+0x10c | Origin-like world triplet | LIKELY cast-related origin; not verified current champion position |
| +0x130/+0x134/+0x138 | Separate target-like triplet | LIKELY target, not a champion sample |
| +0x110 | Time-like float; can predate packet arrival | LIKELY action time; not a replacement replay clock |

At 340.498318, the origin-like planar values are (7726.394,7410.062), target-like
values (8470.953,8219.772), with time-like value about 340.499. Later records at
342.001318, 342.335318, and 342.806318 have origin-like values (8210,7934), inside
the movement gap. These promising examples were not sufficient for production.

A deterministic sample of 200 packets spanning the affected match covers all
ten champions. All 200 source identity pairs match the envelope. Of 100 packets
within 2ms of a recorded movement origin, only 75 origin candidates are within
4 world units. Counterexamples include Diana at 1511.131 (~401 units), Jarvan IV
at 980.064 (~401 units), and Thresh at 1306.192 (~459 units, candidate clock
about 2.037s earlier). Maximum absolute candidate-clock offset is 2.171s.
This rejects unconditional injection of these fields into champion tracks.
Potential stale cast origins, spell-specific offsets, and ordering remain UNKNOWN.

Research is isolated in tools/research_cast_origins.py. Reproduce with
`python -m tools.research_cast_origins <replay.rofl> --profile <packet-02c4.json> --output <research.json>`.
The research profile is generated by tools/probe_packet.py using the exact
addresses above. No unverified profile is added to production. The small
samples/cast-origin-research-fixture.json preserves relevant observed writes;
samples/cast-origin-correlation-summary.json records the broad result. Tests
ensure origin/target separation, reading scalar writes before byte obfuscation,
and rejection of incomplete/nonfinite fields. Next step is resolving action
type, origin semantics, and timing before accepting any supplemental samples.

## Embedded action time and variant correlation (2026-09-14)

The candidate embedded time (+0x110) was compared with actual movement origins,
without route extrapolation. Corroboration requires an observation within 2ms
and planar error at most 4 world units. This explicitly avoids treating a distant
sample during a gap as ground truth. In each replay, 200 deterministically spaced
0x02c4 packets span all ten players, with 200/200 source identity matches.

| Replay | Arrival-time corroborated | Embedded-time corroborated | Embedded coincident mismatches | No close embedded-time observation |
| --- | ---: | ---: | ---: | ---: |
| NA1-5640962900 | 75 | 74 | 15 | 111 |
| NA1-5640196741 | 51 | 51 | 8 | 141 |

VERIFIED: Thresh records at 524.911 and 1306.192 have origin errors about
415/459 units at arrival, but under two units at their embedded times roughly
2.171/2.037 seconds earlier. A third earlier-position case is corroborated too.
This supports an earlier action origin for those records. It does not establish
that all candidate times can replace transport time. The aggregate does not improve;
the two comparison populations also differ because nearby observations are sparse.

Additional grouping keys were read from scalar writes at +0x118 and +0xd8.
Their general semantics remain UNKNOWN. A case-folded ELF-style string-hash
hypothesis maps +0x118 values as follows:

| Fingerprint | Name hypothesis | Evidence in affected replay's sample |
| --- | --- | --- |
| 0x06496ea8 | SummonerFlash | Three ~397-401 unit coincident mismatches across Jarvan IV and Diana |
| 0x07b05da5 | VladimirE | 13 records, three coincident mismatches, ten without close observations |
| 0x07b05db1 | VladimirQ | Ten records; seven corroborated, three sparse |
| 0x0a85b9cd | Tantrum | Eight Amumu records; seven corroborated, one sparse |

LIKELY: action fingerprints and action-dependent origins. The name mapping is
a research hypothesis; hash matches can collide and the client consumer has not
been traced to prove these identities. In particular +0xd8 is not established
as a summoner-spell slot (its observed values must not be presented as such).
The Flash-like cases could describe a pre-relocation origin, while other actions
can retain older origins. Exact ordering and charged-action behavior remain UNKNOWN.

The evidence rejects unconditional origin injection and unconditional shifting
to the candidate timestamp. Even seven corroborated Tantrum observations do not
justify an action-specific production decoder without wider validation during
movement gaps and interpretation of the action origin. No normalized position,
event, schema, timing, or viewer behavior changed in this follow-up.

Reproduction: tools/research_cast_origins.py now retains the two grouping fields;
tools/analyze_origin_timing.py compares the two timelines and emits grouped results.
samples/origin-timing-summary.json contains both summaries, and
samples/origin-timing-fixture.json contains five real counterexample cases with
their relevant observed movement windows. Five focused tests cover earlier versus
coincident mismatching origins, hash hypotheses, sparse evidence, input immutability,
scalar-write handling, and invalid fields. The local readable report is
samples/local/movement-audit/origin-timing-review.md.

Regression fixtures include a backward correction and a held relocation from
each of the five replays. Tests require finite positions under backward seeking,
exact observed endpoints, preserved unresolved discontinuities, no input mutation,
life-state masking, duplicate handling, and continued Yi/Ashe long-gap continuity.

### Scoped Amumu action positions (2026-09-14, decoder v8)

The wider validation requested above is now complete for the Amumu envelope
entity and fingerprint `0x0a85b9cd` only. This supersedes the earlier provisional
decision for that combination; general `0x02c4` origins remain unsupported.

VERIFIED within the three tested 16.18.817.5716 replays:

| Replay | Fingerprint records | Coincident movement observations (within 2 ms) | Origins within 4 world units | Added gap observations |
| --- | ---: | ---: | ---: | ---: |
| NA1-5640962900 | 85 | 66 | 66 | 3 |
| NA1-5640901584 | 73 | 60 | 56 | 2 |
| NA1-5640933743 | 165 | 136 | 131 | 2 |

All 323 records have matching envelope/source identities and embedded times
within 0.501 ms of packet time. Of 262 coincident observations, 253 agree within
4 units. The other nine agree within approximately 2 units with the next movement
observation 33–67 ms later. These demonstrate stream ordering differences, so
the adapter gives original movement observations precedence within 100 ms.
The 61 records without coincident movement evidence are not independently
position-verified merely by belonging to this fingerprint; their use is supported
by the scoped population evidence and conservative gap guards.

The exact-client decoder is registered as `amumuActionOrigin`: deserializer
RVA `0x10d0760` through `0x10d0a43`, constructor `0xe8a8f0` through `0xe8a991`.
The last four-byte scalar writes provide source IDs at object offsets `+0x5c`
and `+0x6c`, planar origin at `+0x104` / `+0x10c`, time at `+0x110`, and fingerprint
at `+0x118`. These are decoded-object offsets, not wire payload offsets. The
existing exact-client profile validation still applies. Height `+0x108`, target
coordinates, and the opaque `+0xd8` grouping value are not used for positioning.

LIKELY: the fingerprint identifies Tantrum, based on the case-folded ELF hash.
The name is still a hypothesis, not a normalized spell event. UNKNOWN: general
action-origin semantics, cast ordering, and missing dash trajectories. This is
not evidence that Flash, Vladimir E, Thresh actions, or other champions can use
this adapter.

`parser/action_positions.py` checks identity, finite map coordinates, and time
agreement before considering a sample. It only inserts inside existing tracks,
outside known dead intervals, when the original route has stopped or exhausted
and the observation differs by more than four units. Active routes and nearby
original observations are preserved. Normalized samples carry `positionOnly`
and `positionSource: AMUMU_ACTION_ORIGIN`, with no fabricated speed or path.
The frontend holds these samples until the next record, including after seeking.

The three accepted observations in NA1-5640962900 are at 342.335318, 933.029361,
and 1035.553428 seconds. The first is (8210, 7934), about 1.807 seconds before
the next movement update at 344.142318. The different action at 342.001 is
excluded. Existing events, map entities, and original samples in all three
refreshed caches were compared against backups and remain unchanged.

Reproduce the population scan with `tools/research_cast_origins.py --champion
Amumu --all` and its replay/profile arguments. Local reports are under
`samples/local/movement-audit/amumu-all-*.json`. The portable scalar-write fixture
is `samples/cast-origin-research-fixture.json`. Tests cover scoped rejection,
identity/time/finite-value guards, nearby movement precedence, active routes,
dead intervals, idempotence, and the exact three additions in the real Amumu
replay. Frontend tests check holding, endpoints, and backward seeking. The
real-replay test skips when the private fixture or supported client is absent.


### Target-correlated relocation cluster (2026-09-14)

The controlled movement audit and evidence are in
[movement-review-2026-09-14.md](movement-review-2026-09-14.md). A 990�1010 second
window from NA1-5640196741 contains three `0x02c4` actions with fingerprint
`0x008fa255` for Twisted Fate, Syndra, and Malphite. VERIFIED observations:
source IDs match envelope entities; decoded origin `+0x104/+0x10c` matches each
stopped movement origin within 2.1 units; decoded target `+0x130/+0x138` is within
28.2 units of the next real movement origin 6.012�6.291 seconds later. The
companion fingerprint `0x0a9306a0` has a self-target and fails target correlation.

LIKELY: a shared target-correlated relocation mechanism. UNKNOWN: gameplay name,
completion time, interruption/cancellation rules, and travel trajectory. The
candidate is not mapped to a teleport spell based on packet timing alone. The
repeated intermediate opcode sequence (`0x0345`, `0x0268`, `0x03d6`, `0x01c1`,
`0x0129`, `0x016b`) occurs about three seconds after the action. Another sequence
including `0x021c` and `0x028d` precedes the next movement sample by about 33 ms.
These packets remain unlabeled; proximity is not semantic proof.

`tools/analyze_relocation_candidates.py` applies explicit research gates (150 ms
stop alignment, 4-unit origin tolerance, 64-unit target tolerance, a stopped gap
at least two seconds and displacement at least 2,000 units, matching identities,
and embedded time within 2 ms). These gates select candidates, not supported
normalized events. Tests and portable fixtures preserve all three matches and
self-target counterexamples. Next: scan complete matches and additional replays,
include cancelled actions, then trace the relevant client consumers. No position
samples or events are emitted from this research tool.
