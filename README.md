# Rift Replay

A browser-based 2D League of Legends replay viewer, driven by movement decoded
from an actual `.rofl` file. Upload a replay, watch all ten champions, pause,
scrub, and change playback speed. No League simulation or invented trajectories.

**Experimental MVP:** validated on `NA1-5640196741.rofl`, client
`16.18.817.5716`. Its 51,264 movement packets yield 56,432 champion-origin
samples over 36:33.710. Other client builds fail with an unsupported-version
error instead of silently applying the wrong decoder.

**Dragon review update:** five real replays now pass integration checks. The
parser extracts 18 team dragon notifications across them; the original replay
has six. They appear in the existing event feed and timeline with a ten-second
review lead-in. Re-upload older cached replay JSON to add these events.
Individual dragon killer, elemental type, Baron and Herald remain unavailable.
Assist-credit candidates were tested across all five matches and rejected for
inconsistent totals; current assists are still omitted. See
[`docs/rofl-format.md`](docs/rofl-format.md) for the evidence and next decoding steps.

Run `.\.venv\Scripts\python.exe -m pytest -q` from the root (37 tests), and
`npm test` / `npm run build` in `web` (27 tests plus production build).
`ROFL_TEST_DIR` optionally points to the directory containing all five private
fixtures; missing local replays or the exact client cause integration skips.
The small real dragon packet fixtures are included in `samples/dragon-packets.json`.

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
The next observed origin corrects the position; death/recall events remain undecoded.

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
and selected-player filters. Objectives and structures remain explicitly unsupported.

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
the existing parser interface; movement decoding is preserved.

Print the actual decoded event feed with
`python -m tools.dump_events samples/local/review.json` after producing that JSON
with the parser CLI. Use the existing pytest, npm test, and npm run build commands
above to test the phase, including real-packet, stable-ID and final-total assertions.

On Windows, pytest's fault handler may print an access-violation diagnostic during
Unicorn memory initialization even when the run completes successfully. This was
observed here with all 30 Python tests passing; normal CLI and HTTP uploads also
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
- Champion kills/deaths are verified against all ten metadata totals. Dragon
  notifications include team credit, checked against final team totals. Assists,
  Baron, Herald and structures are not decoded. Death highlight locations
  use nearby observed movement origins where available, labeled approximate.
- Fog of war, minions, projectiles, abilities, attacks, cooldowns, and combat
  simulation are postponed. Only the all-player view is exposed.
- The official Data Dragon map is a schematic minimap, not the detailed in-game
  terrain texture. Uncached champion icons use the official Data Dragon CDN.

Next: identify an explicit assist-credit source and Baron/Herald notifications.
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
