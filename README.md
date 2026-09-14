# Rift Replay

A browser-based 2D League of Legends replay viewer, driven by movement decoded
from an actual `.rofl` file. Upload a replay, watch all ten champions, pause,
scrub, and change playback speed. No League simulation or invented trajectories.

**Experimental MVP:** validated on `NA1-5640196741.rofl`, client
`16.18.817.5716`. Its 51,264 movement packets yield 56,432 champion-origin
samples over 36:33.710. Other client builds fail with an unsupported-version
error instead of silently applying the wrong decoder.

**Objective and structure review:** five real replays provide 18 dragon,
4 Baron, 4 Herald, 12 Void Grub, 53 tower and 10 inhibitor events. The original replay now
has 177 events in total: 75 kills, 71 respawns, 6 dragons, 2 Barons, 1 Herald,
3 Void Grubs, 15 towers and 4 inhibitors. They appear in the existing event feed and timeline.
Click Objectives or Structures to filter; click an event for a ten-second
objective or eight-second structure lead-in. Event URLs preserve that selection.
Re-upload older cached replay JSON to add these events.
Baron, Herald and Void Grubs include verified player credit. Dragon killer/subtype and
inhibitor coordinates and complete objective/structure respawn state remain unavailable.

**Persistent map markers:** re-upload a replay (or reload one of the five locally
refreshed matches) to see all 22 towers at decoded positions. Ordinary towers
become faded/slashed at their destruction time; nexus towers fade to an explicit
unknown rebuild state because their respawn decoding is incomplete. Hover a marker
for its team, lane, tier and state. The Map entities checkbox hides this layer.
Tower events now include lane/tier and map highlights at the actual tower position.

Baron, Herald and corroborated dragons remain visible from their first matching
keyframe until the recorded kill. These are observed-presence intervals, not exact
spawn timers: unseen objectives and some dragons are not yet covered. The primary
match has 22 towers, two Baron intervals, one Herald interval and four of its six
dragon intervals. All three Void Grubs also have individual observed-placement
markers and recorded death/cleanup transitions. Inhibitor map placement remains unsupported pending a reliable
link between replay entity IDs and visual anchors. No timer-based spawns are invented.

The timeline/feed retain their eight local vector icons, legend and event seeking.
Assist-credit candidates were tested across all five matches and rejected for
inconsistent totals; current assists are still omitted. See
[`docs/rofl-format.md`](docs/rofl-format.md) for the evidence and next decoding steps.

Run `.\.venv\Scripts\python.exe -m pytest -q` from the root, and
`npm test` / `npm run build` in `web` (57 Python tests, 36 frontend tests, plus production build).
`ROFL_TEST_DIR` optionally points to the directory containing all five private
fixtures; missing local replays or the exact client cause integration skips.
Small real packet fixtures are included in `samples/dragon-packets.json` and
`samples/notification-packets.json`. Full private replays and client binaries
remain local and are not committed.

## Run locally

Requirements: Python 3.11–3.13, Node.js 22.12+ (tested with 22.13), Git, and
your own **exact matching** `League of Legends.exe`. Installation requires
Internet access. The supplied replay's map and ten champion icons are cached
in the repository, so playback itself does not need an API key or Riot login.

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:LEAGUE_CLIENT_EXE = 'C:\Riot Games\League of Legends\Game\League of Legends.exe'
.\.venv\Scripts\python.exe -m uvicorn server.app:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd web
npm ci
npm run dev
```

Open [the viewer](http://127.0.0.1:5173). Click **Open replay**, select
`NA1-5640196741.rofl`, and wait for **Replay ready**. Press Play, drag the
timeline, or select 0.25×, 0.5×, 1×, 2×, or 4×. Select a roster entry to
highlight that champion. Space toggles playback; left/right seek ten seconds
when focus is outside a form control.

The default executable path above is used if `LEAGUE_CLIENT_EXE` is unset.
On Linux/macOS, use `.venv/bin/python` and point the environment variable at
a locally available matching Windows executable. The parser reads it as data;
it never starts League, attaches to a process, or changes the executable.

**Riot updates overwrite the installed executable.** Preserve your own matching
copy locally if you need to keep decoding this build. Do not commit game binaries.

## Architecture

```text
.rofl
  │
  ▼
rofl-parser  [Python adapter]
  ├── RoflLens: ROFL v2 container + network block framing
  └── exact-build profile: gameChunk movement packet decoding
  │
  ▼
NormalizedReplay v1
  │
  ▼
Replay API  [FastAPI + local JSON storage]
  │
  ▼
PixiJS Viewer  [React + TypeScript + Vite]
```

```text
parser/       Public ReplayParser interface, CLI, 16.18 movement decoder
server/       Upload/read HTTP endpoints
shared/       Normalized TypeScript contract and Riot champion catalog
web/          React controls, Pixi scene, interpolation, cached static assets
tests/        Parser, real-file integration, and API workflow tests
tools/        Reproducible transport and offline decoder research scripts
samples/      Sanitized evidence; local/ contains ignored private outputs
docs/         Format research, decoder evidence, and limitations
```

Python was chosen for the initial parser because RoflLens immediately provided
working v2 transport and offline decoder research tools. The `ReplayParser`
adapter and language-neutral JSON contract allow replacing it with Rust without
changing rendering or controls. No raw ROFL packet types enter the frontend.

## Parser and normalized format

`ReplayParser.parse(path)` returns `schemaVersion`, `metadata`, `players`,
`tracks`, `events`, and `diagnostics`. See [the contract](shared/replay.ts).
Each player has a stable replay-local ID, champion name/ID, team, and role.
Each track stores ordered `{timestamp, x, y, speed, path}` samples in seconds and
world units. `x/y` are observed path origins; `path` contains the recorded commanded
route, including that origin. Destinations are not synthetic timestamped samples.
Player display names are included when available; account IDs are omitted.

The parser checks the replay client version and protocol digest, then SHA-256
checks the local executable before reading a 256-byte lookup table. The 16.18
decoder consumes opcode `0x004C`; `0x022C` is absent from this fixture. The direct
decoder was compared with the matching client's offline deserializer on 81
packets spread across the match. All 51,264 movement payloads parse completely.
See [ROFL research and evidence](docs/rofl-format.md).

Unknown opcodes are counted and skipped. Corrupt movement packets fail clearly,
since dropping them silently could misrepresent movement. Generic container
inspection is available even when positional decoding is unsupported:

```powershell
.\.venv\Scripts\python.exe -m parser 'C:\path\match.rofl' --inspect
.\.venv\Scripts\python.exe -m parser 'C:\path\match.rofl' --output samples/local/replay.json
.\.venv\Scripts\python.exe tools/probe_replay.py 'C:\path\match.rofl'
```

`--client-exe` overrides the CLI environment setting. `samples/local` and all
`.rofl` files are gitignored. The original supplied replay remains in its original
location. Uploads are temporary; only normalized JSON persists after parsing.

## API

| Method | Path | Result |
|---|---|---|
| POST | `/api/replays` | Multipart `file`; returns ID, metadata, sample count |
| GET | `/api/replays/{id}` | Complete normalized JSON |
| GET | `/api/replays/{id}/data` | Complete normalized JSON |
| GET | `/api/replays/{id}/metadata` | Metadata, roster, diagnostics |
| GET | `/api/health` | Server status and supported build |

IDs are the source replay's SHA-256. `REPLAY_STORE` optionally changes storage
from `samples/local/replays`. One parse runs at a time; concurrent requests get
503. Files exceeding 128 MB are rejected. The server is intended for local
development and binds only to localhost in the documented commands. Vite proxies
`/api` to port 8000. Interactive API docs are at [localhost:8000/docs](http://127.0.0.1:8000/docs).

## Rendering and coordinate checks

Pixi maintains one map sprite and ten champion containers, with optional debug
labels/grid. A ticker moves sprites; React updates the control display at 10 Hz.
Seeking uses binary search independently on each champion's track. The renderer
follows each recorded route at its recorded speed until the next update, stopping
at the route endpoint. Long gaps between commands no longer freeze normal travel.
The next observed origin corrects the position; recorded deaths/respawns interrupt routes. Recall completion remains undecoded.

`worldToMap()` centrally maps world `[0,14716] × [0,14824]` onto the image and
inverts the vertical axis. **Debug** shows raw/world and map coordinates, previous
and next timestamps, time, FPS, and patch. See the calibration notes in
[the format document](docs/rofl-format.md#coordinates-and-sampling).

## Tests and build

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:ROFL_TEST_FILE = 'C:\Users\tom-d\OneDrive\Documents\League of Legends\Replays\NA1-5640196741.rofl'
.\.venv\Scripts\python.exe -m pytest -q
cd web
npm test
npm run build
```

The real-file tests assert the version, exact ten champions, 113 chunks, stream
counts, histogram, sample counts, finite coordinates, monotonic timestamps,
and upload → disk JSON → API response. Private-fixture tests skip when the replay
is unavailable; semantic tests additionally require the matching executable.
Frontend tests cover interpolation, binary search, coordinate transforms, and
display discontinuities. The production build can be served with `npm run preview`
while the same API server runs.

## Phase 2: interactive review

Re-upload an existing replay once to regenerate it with event data. The supplied
fixture produces **75 verified champion kills/deaths and 71 respawns**. Click a timeline marker
or event-feed row to seek eight seconds before the kill. Hover or keyboard-focus
a marker for victim/killer information. The collapsible feed supports category
and selected-player filters. Objectives and structures are included where decoding is verified.

Respawn events have their own filter and seek three seconds before the recorded
return. Enable **Respawn markers** to show all returns on the timeline; a selected
respawn always appears. The player inspector shows Alive or Dead with a countdown to the actual
respawn event. Dead icons are dimmed and marked with a cross; their previous
movement command stops at the death location. Trails do not connect corpses to
spawn. Four champions never respawn before this match ends, and stay marked dead.
Reload or re-upload older normalized replays to obtain this data. No return is
invented from a death timer. Current life state is enabled only when the backend
reports verified respawn coverage.

Click a champion on the map or in the roster to open its inspector. Current
kills/deaths are derived from the timeline. **Final match stats** separately shows
metadata K/D/A, level, total gold and CS. Current assists and other unsupported
fields are labeled unavailable. Follow strengthens the highlight in the existing
full-map view. Show Trail draws a fading 30/60/120-second route using bounded Pixi
geometry; it does not add artificial observations to the replay model.

Manual seeking, event review and player selection update the URL with
`history.replaceState`, without page reloads or animation-frame URL updates:

```text
/replay/<source-sha256>?t=842&player=4
/replay/<source-sha256>?event=<stable-event-id>
```

An event link takes precedence over `t` and applies the review lead-in. Links
work where the same local backend has that replay JSON; this is not cloud sharing.
In Debug mode, select an event to inspect its normalized record, raw timestamp,
opcode, packet size, network IDs and field confidence.

The additive v1 model now includes typed events, optional `Player.finalStats`,
and `metadata.eventCoverage`. Old movement-only JSON still plays, but must be
re-uploaded for current kill/death statistics. New frontend modules are
`EventReview`, `PlayerInspector`, `events`, `urlState`, and `trails`; the existing
Pixi ticker still owns animation. Sorted event indexes support binary-search
lookups. The 16.18 death adapter uses Unicorn (now a runtime requirement) behind
the existing parser interface; movement decoding is preserved. The additional
`parser/notifications.py` layer models and correlates announcements, script
events and building death/credit records before normalization. It validates
per-player objective/structure credits and per-team tower losses. Neutral
Herald self-removal is excluded, and final-hit entities are distinguished from
credited participants. Decoder `16.18-review-v4` enables these existing event
types; normalized schema version 1 remains compatible. Debug provenance shows
the entity IDs and corroborating packet opcodes without exposing raw payloads.

Print the actual decoded event feed with
`python -m tools.dump_events samples/local/review.json` after producing that JSON
with the parser CLI. Use the existing pytest, npm test, and npm run build commands
above to test the phase, including real-packet, stable-ID and final-total assertions.

On Windows, pytest's fault handler may print an access-violation diagnostic during
Unicorn memory initialization even when the run completes successfully. This was
observed here with all 51 Python tests passing; normal CLI and HTTP uploads also
completed. See [Unicorn's Windows exception FAQ](https://github.com/unicorn-engine/unicorn/blob/master/docs/FAQ.md#i-debug-my-application-but-soon-get-an-access-violation-inside-unicorn).
Check the final test result and process exit code; actual parse errors are not ignored.

## Known limitations and roadmap

- One exact build and five real replays are validated. Wider compatibility needs
  additional fixtures and independently validated profiles.
- Participant order → entity mapping follows the established parser convention
  and matches this fixture's teams/laning; a dedicated hero-spawn identity decoder
  is still desirable. Map ID 11 is a current profile assumption, not a decoded
  map-selection field. Other maps are unsupported.
- Positions are network path origins with recorded routes and speeds. This is
  not an exact continuous simulation: changing movement buffs, recalls, deaths,
  and dashes may still cause corrections or snaps. HP is not decoded; death and respawn notifications control life state.
- Champion kills/deaths, Baron/Herald credits and structure credits are checked
  against metadata totals. Dragon notifications include verified team credit.
  Current assists and inhibitor positions are not decoded. Death highlight locations
  use nearby observed movement origins where available, labeled approximate.
- Fog of war, minions, projectiles, abilities, attacks, cooldowns, and combat
  simulation are postponed. Only the all-player view is exposed.
- The official Data Dragon map is a schematic minimap, not the detailed in-game
  terrain texture. Uncached champion icons use the official Data Dragon CDN.

Next: resolve inhibitor entity identity and exact objective/nexus respawn records.
Five 16.18 fixtures now provide independent validation; nearby 16.17 replays
remain unsupported. Improve path timing
and profile tooling for later patches. Port stable parser layers to Rust when it
offers a clear maintenance benefit.

## Credits and assets

Transport uses [RoflLens](https://github.com/ss26367098/rofllens); local path-record parsing adapts its layout with signed waypoint deltas
(MIT), pinned to commit `62a475a8f05e7dfa94df5990758be2156c892496`.
[ROFL-X](https://github.com/Toastaspiring/ROFL-X) and
[Mowokuma/ROFL](https://github.com/Mowokuma/ROFL) informed the research.
Champion and schematic map assets come from Riot Data Dragon `16.18.1`;
`tools/fetch_assets.py` reproduces the cache. Riot assets retain Riot's rights.

Rift Replay is not endorsed by Riot Games and does not reflect the views or
opinions of Riot Games or anyone officially involved in producing or managing
Riot Games properties. Riot Games and all associated properties are trademarks
or registered trademarks of Riot Games, Inc.


### Void Grubs

All three Void Grubs now have persistent markers at their decoded initial
positions. Each disappears at its own death or recorded cleanup, and seeking
backward restores the appropriate markers. Individual kill events include player
and team credit, a distinct timeline icon, and a 10-second review lead-in.

All five integration replays identify three grubs. Per-player kill counts match
final HORDE_KILLS exactly: three kills in four matches, and zero in the match
where the camp is cleaned up. Existing camp-event links remain valid.

Markers begin at the first actual entity observation (around 7:53 in these
matches), not an assumed targetable spawn time. They show initial placement,
not monster combat movement. The parser decodes a validated identity/position
prefix of 0x0287; its trailing fields remain unsupported. Evidence and limitations
are documented in `docs/rofl-format.md`.

Refresh an existing cache with `python -m tools.enrich_map_entities <actual.rofl> <cached.json>`. New uploads use v7 after restarting the backend; reload the viewer
after updating a cache. Run `python -m pytest tests/test_neutral_entities.py -q`
and the normal frontend tests/build to verify this feature.


### Movement jitter correction

The viewer reconciles small route-prediction errors with the next recorded origin
across moving intervals of at most two seconds. Corrections are bounded to 48–100
world units (depending on speed and interval); explicit stops, single-point paths,
and large relocations retain their prior behavior. Raw replay
samples are unchanged. This is stateless display interpolation, so pausing and
backward seeking produce the same position. No re-upload is required after this
frontend update—reload the page. Unsupported gaps and incompletely decoded movement
mechanics may still cause visible jumps.

`movement-boundaries.fixture.json` contains actual consecutive observations from
NA1-5640962900 for Vladimir, Naafiri, and Amumu. Tests verify continuity at the
sample boundary, exact recorded endpoints, unchanged input, and discontinuity
preservation. Memoized event feed/timeline components also avoid rebuilding their
unchanged markers at each playback-clock update.

Long moving intervals (over 2 and up to 15 seconds) use observed progress along
the recorded route when the next origin is within 32 world units of its interior
and implies 0.5-1.25 times the earlier speed. This addresses Master Yi (25.545s)
and Ashe (26.414s) in NA1-5640962900: constant-speed prediction overshot their
next recorded positions. Completed routes and off-route relocations retain their
prior behavior. Timing between observations is interpolated; exact speed changes
are not decoded. `long-route-gaps.fixture.json` contains both real sample pairs.
The frontend suite has 38 passing tests. Reload; no re-upload is required.

### Auditing movement across replays

From `web`, run `npm run audit:movement`. It reads all normalized JSON files in
`samples/local/replays` and writes `samples/local/movement-audit/report.md` and
`report.json`. Optional arguments specify input and output directories:
`npm run audit:movement -- <input-directory> <output-directory>`.
The Markdown report links directly to each champion and review timestamp.
JSON retains sample pairs, nearby events, correction distances, and classifications.
It uses the viewer's actual interpolation and death/respawn overrides, runs
offline, and adds no per-frame work to the map.

The five-replay baseline covers 227,402 boundaries, with 3,493 corrections of
at least 30 world units outside known life transitions. These are candidates
for review, not 3,493 confirmed bugs: real relocations intentionally remain
discontinuous. Ten actual pairs from all five replays now guard against blindly
smoothing those cases. The frontend suite has 42 passing tests.

To inspect original packets around a candidate, from the repository root run:
`python -m tools.export_movement_window <replay.rofl> --start 9 --end 12 --player 8`.
It requires the matching local client executable (`--client` can override its
path). The default evidence output is `samples/local/movement-window.json`.
This research command labels only the existing decoded movement records; unknown
packets stay unlabeled. See `docs/rofl-format.md` for the current findings.

Movement-header follow-up: all 195,041 packets across the five replays confirm
the u16 header field is the decoded record count. The parser now checks it.
The unnamed u32 is not a validated clock: using its delta as milliseconds makes
prediction substantially worse, so existing timestamps remain unchanged. Run
`python -m tools.movement_timing <replay.rofl> [more.rofl ...]` for the repeatable
comparison and `python -m pytest tests/test_movement_header.py tests/test_movement.py -q`
for focused checks. This is parser validation and research, not a fix for the
remaining rapid-direction-change stutters. No re-upload is needed for existing
cached replays; restart the backend to apply validation to new uploads.

Rapid-turn follow-up: the viewer now reconciles a small overshoot when an update
arrives within 0.25s, lies within 16 world units of the interior of the previous
route, and the next command points back against that route. The maximum correction
is 100 world units. It interpolates observed progress; it does not decode turn
delays or change replay timestamps. Ten real pairs across five replays cover the
new behavior, including six Ashe turns at 9-12 seconds in NA1-5640962900.
The five-replay audit removed 139 flags with no new flagged boundaries, leaving
3,354 non-life review candidates. Remaining candidates can include real relocations.
All 44 frontend tests pass. Reload the viewer to apply this display-only change;
existing replay caches work without re-uploading.

Hold review now distinguishes small corrections, arrival/departure near a player's
observed respawn positions, and unexplained relocations. Run `npm run audit:movement`
from `web`; review links include up to 15 seconds before a held relocation.
The five-replay baseline contains 462 non-life holds: 95 small corrections,
274 arrivals near spawn, 21 departures near spawn, and 72 unexplained relocations.
These are spatial diagnostic labels, not decoded recalls or teleports.

Research into Amumu's 5:40-5:44 gap found origin-like fields in 0x02c4, but wider
checks rejected unconditional use as champion positions. Those candidate fields
remain research-only. The movement data and playback behavior are unchanged by
this investigation. The frontend suite has 46 passing tests; two focused Python
tests cover the research field extraction.

Action-origin timing research now compares raw movement observations at both
packet arrival and the embedded candidate time. On two 200-packet samples,
shifting all origins to the embedded time did not improve overall corroboration.
Three Thresh records match earlier positions; other mismatches cluster around
fingerprints matching SummonerFlash and VladimirE. Those names are hash hypotheses,
not newly supported spell events. General action-origin supplementation remains disabled;
the narrowly validated Amumu exception below is now enabled.
Reproduce the correlation with `python -m tools.analyze_origin_timing <research.json> <normalized.json> --output <report.json>`;
run `python -m pytest tests/test_cast_origin_research.py tests/test_origin_timing.py -q`
for the five focused checks. Results are in `samples/origin-timing-summary.json`.

Amumu follow-up (decoder v8): validation across three real replays now permits
position observations from Amumu's Tantrum-fingerprint records. Only stopped or
exhausted-route gaps are supplemented, with existing movement samples taking
precedence within 100 ms. The viewer holds these observed positions until the
next update; it does not invent a dash route. Seven observations were added across
the three local caches, including three in NA1-5640962900. At 5:42.335 this replay
now shows the observed location instead of waiting until 5:44.142.

Reload the viewer to load the refreshed caches. Restart the backend to use the
updated parser for new uploads. Other matching caches can be upgraded with
`python -m tools.enrich_action_positions <replay.rofl> <cached.json>` (using the
project virtual environment and supported installed League client). This verifies
the replay identity and saves a `.before-amumu.bak` backup before replacing JSON.
Run `python -m pytest tests/test_action_positions.py -q` for the scoped decoder
and real-replay integration checks, and `npm test` in `web` for playback checks.
This reduces a specific stale-position interval; other unexplained relocations
and missing dash trajectories remain unresolved.


Movement review follow-up: the controlled five-replay comparison is documented in
[the movement review report](docs/movement-review-2026-09-14.md). Seven earlier
observations replace five old jump flags, leaving 3,356 review candidates versus
3,354 in the same-renderer baseline. This is not a claim that the relocations
became smooth. The audit now counts position-only holds correctly and recognizes
same-team observed spawn coordinates when personal respawn evidence is absent.
Run `npm run audit:movement` in `web` for the report and controlled comparison.
Three champions share a promising action-target relocation pattern; it remains
research-only pending completion/cancellation and cross-replay validation.
