"""ROFL adapter -> versioned normalized model; never exports raw protocol bytes."""
import hashlib
import json
import logging
import math
from collections import Counter
from pathlib import Path

from rofllens import ReplayReader
from .movement import parse_movement_payloads
from .events import DeathDecoder, DEATH_OPCODE, RESPAWN_OPCODE, validate_deaths, attach_observed_locations, merge_life_events
from .events import DRAGON_OPCODE, validate_dragons
from .notifications import ReviewNotifications, NOTIFICATION_OPCODES
from .neutral_entities import extract_grub_entities
from .grubs import normalize_grub_notifications, UNIT_DEATH
from .map_entities import extract_map_entities, NEUTRAL_REMOVAL
from rofllens.errors import RoflParseError, SemanticDecodeError
from .patch_16_18 import (CLIENT_VERSION, PROTOCOL_DIGEST, PLAYER_ENTITY_START,
                          MOVEMENT_OPCODE, PatchDecoder)

log = logging.getLogger(__name__)
CATALOG = json.loads((Path(__file__).resolve().parents[1] / 'shared/champions.json').read_text(encoding='utf-8'))


class ParseError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class ReplayParser:
    """Replace this adapter to add a Rust parser or another patch decoder."""
    def __init__(self, client_exe: str | Path):
        self.client_exe = Path(client_exe)

    def inspect(self, path: str | Path) -> dict:
        try:
            with ReplayReader.open(path) as reader:
                return {'container': reader.summary().as_dict(), 'players': self._players(reader)}
        except (RoflParseError, ValueError, OSError) as exc:
            raise ParseError('INVALID_REPLAY', str(exc)) from exc

    @staticmethod
    def _players(reader: ReplayReader) -> list[dict]:
        players = []
        for i, player in enumerate(reader.metadata.participants):
            if player.get('TEAM') not in ('100', '200') or not player.get('SKIN'):
                raise ValueError('Missing champion/team participant metadata.')
            players.append({'id': i, 'championName': player['SKIN'],
                            'championId': CATALOG.get(player['SKIN'], {}).get('id'),
                            'team': 'BLUE' if player['TEAM']=='100' else 'RED',
                            'role': player.get('TEAM_POSITION', ''),
                            **({'displayName':player.get('RIOT_ID_GAME_NAME') or player['NAME']} if player.get('RIOT_ID_GAME_NAME') or player.get('NAME') else {}),
                            'finalStats': {key:int(player[field]) for key,field in
                                [('kills','CHAMPIONS_KILLED'),('deaths','NUM_DEATHS'),('assists','ASSISTS'),
                                 ('level','LEVEL'),('totalGold','GOLD_EARNED'),('minionKills','MINIONS_KILLED'),
                                 ('neutralMinionKills','NEUTRAL_MINIONS_KILLED')]
                                if field in player and str(player[field]).isdigit()}})
        return players

    def parse(self, path: str | Path) -> dict:
        try:
            return self._parse(Path(path))
        except ParseError:
            raise
        except (RoflParseError, SemanticDecodeError, ValueError, OSError) as exc:
            raise ParseError('INVALID_REPLAY', str(exc)) from exc

    def _parse(self, path: Path) -> dict:
        with ReplayReader.open(path) as reader:
            if (reader.header.client_version, reader.header.protocol_digest) != (CLIENT_VERSION, PROTOCOL_DIGEST):
                raise ParseError('UNSUPPORTED_VERSION', f'Movement decoding supports {CLIENT_VERSION} / {PROTOCOL_DIGEST}; this replay is {reader.header.client_version} / {reader.header.protocol_digest}.')
            players = self._players(reader)
            chunks = tuple(reader.chunks())
            if any(c.raw_size > 64*1024*1024 for c in chunks) or sum(c.raw_size for c in chunks) > 512*1024*1024:
                raise ParseError('REPLAY_TOO_LARGE', 'Replay exceeds the MVP decompressed-size limit.')
            if len(players) != 10 or Counter(p['team'] for p in players) != {'BLUE': 5, 'RED': 5}:
                raise ParseError('UNSUPPORTED_MAP', 'The current profile supports ten-player Summoner’s Rift replays.')
            try:
                decoder = PatchDecoder(self.client_exe)
            except (OSError, ValueError) as exc:
                raise ParseError('CLIENT_REQUIRED', f'{exc} Set LEAGUE_CLIENT_EXE to the matching local League of Legends.exe.') from exc
            samples = [[] for _ in players]
            death_decoder = DeathDecoder(self.client_exe)
            notifications = ReviewNotifications(death_decoder.engine)
            events = []
            respawns = []
            dragons = []
            neutral_removals = []
            opcodes = Counter()
            movement_packets = 0
            for block in reader.iter_blocks(streams={'gameChunk'}, include_payload=True):
                opcodes[f'0x{block.packet_id:04x}'] += 1
                if block.packet_id == NEUTRAL_REMOVAL:
                    neutral_removals.append((block.timestamp,block.param))
                if block.packet_id in NOTIFICATION_OPCODES:
                    try:
                        notifications.accept(block)
                    except (ValueError,SemanticDecodeError) as exc:
                        raise ParseError('EVENT_DECODE_FAILED',f'Notification at {block.timestamp:.3f}s: {exc}') from exc
                if block.packet_id == DRAGON_OPCODE:
                    try:
                        dragons.append(death_decoder.decode_dragon(block))
                    except (ValueError,SemanticDecodeError) as exc:
                        raise ParseError('EVENT_DECODE_FAILED',f'Dragon at {block.timestamp:.3f}s: {exc}') from exc
                if block.packet_id == DEATH_OPCODE:
                    try:
                        events.append(death_decoder.decode(block, players))
                    except (ValueError, SemanticDecodeError) as exc:
                        raise ParseError('EVENT_DECODE_FAILED', f'Death at {block.timestamp:.3f}s: {exc}') from exc
                if block.packet_id == RESPAWN_OPCODE:
                    try:
                        respawns.append(death_decoder.decode_respawn(block,players))
                    except (ValueError,SemanticDecodeError) as exc:
                        raise ParseError('EVENT_DECODE_FAILED',f'Respawn at {block.timestamp:.3f}s: {exc}') from exc
                if block.packet_id != MOVEMENT_OPCODE:
                    continue  # Unknown packet types do not break transport parsing.
                movement_packets += 1
                if not math.isfinite(block.timestamp) or block.timestamp < 0:
                    raise ParseError('INVALID_TIMESTAMPS', 'Movement timestamp is not finite and nonnegative.')
                try:
                    raw = decoder.decode_movement_buffer(block.payload)
                    paths = parse_movement_payloads(raw) if raw else []
                except (ValueError, SemanticDecodeError) as exc:
                    raise ParseError('MOVEMENT_DECODE_FAILED', f'Movement packet at {block.timestamp:.3f}s is invalid: {exc}') from exc
                for entity, speed, waypoints in paths:
                    index = entity - PLAYER_ENTITY_START
                    if not 0 <= index < 10:
                        continue
                    # First waypoint is an observed origin, not a future destination.
                    point = waypoints[0]
                    if not all(-500 <= point[axis] <= 15500 for axis in ('x', 'y')):
                        raise ParseError('INVALID_COORDINATES', f'Implausible champion origin at {block.timestamp:.3f}s.')
                    sample = {'timestamp': round(block.timestamp, 6), 'x': point['x'], 'y': point['y'], 'speed': round(speed, 4), 'path': waypoints}
                    track = samples[index]
                    if track and sample['timestamp'] < track[-1]['timestamp']:
                        raise ParseError('INVALID_TIMESTAMPS', 'Champion timestamps move backwards.')
                    if track and sample['timestamp'] == track[-1]['timestamp']:
                        track[-1] = sample  # Last update wins at an identical timestamp.
                    else:
                        track.append(sample)
            if any(len(track) < 2 for track in samples):
                raise ParseError('MISSING_MOVEMENT', 'Not all ten champion entities have positional samples.')
            duration = reader.metadata.game_length / 1000 if reader.metadata.game_length else max(t[-1]['timestamp'] for t in samples)
            if duration <= 0 or any(t[-1]['timestamp'] > duration + 1 for t in samples):
                raise ParseError('INVALID_DURATION', 'Sample timestamps disagree with replay duration.')
            with path.open('rb') as handle:
                source_hash = hashlib.file_digest(handle, 'sha256').hexdigest()
            attach_observed_locations(events,samples)
            life_events=merge_life_events(validate_deaths(events,players,duration),respawns,duration)
            objective_events=validate_dragons(dragons,reader.metadata.participants,duration)
            review_events=notifications.normalize(players,reader.metadata.participants,duration)
            grub_blocks=[b for b in reader.iter_blocks(streams={'gameChunk'},opcodes={UNIT_DEATH,0x0119},include_payload=True)
                         if any(abs(b.timestamp-n.block.timestamp)<.000002 for n in notifications.grubs)]
            grub_events=normalize_grub_notifications(notifications.grubs,grub_blocks,death_decoder.engine,players,reader.metadata.participants,duration)
            grub_events,grub_entities=extract_grub_entities(reader,death_decoder.engine,players,reader.metadata.participants,duration,grub_events)
            all_events=sorted(life_events+objective_events+review_events+grub_events,key=lambda e:(e['timestamp'],e['id']))
            map_entities=extract_map_entities(reader,death_decoder.engine,all_events,neutral_removals)+grub_entities
            log.info('Decoded %s: %d movement packets, %d champion samples', source_hash[:12], movement_packets, sum(map(len, samples)))
            return {'schemaVersion': 1,
                    'metadata': {'patch': CLIENT_VERSION, 'mapId': 11, 'duration': duration,
                                 'sourceSha256': source_hash, 'decoder': 'rofl-v2/16.18-review-v7',
                                 'eventCoverage': {'championKills': True, 'respawns': True, 'assists': False, 'objectives': True, 'dragons': True, 'structures': True, 'voidGrubs': 'INDIVIDUAL_KILLS'},
                                 'positionSource': 'movement-path-origin-with-route',
                                 'entityMapping': 'patch-profile participant order',
                                 'worldBounds': {'minX': 0, 'maxX': 14716, 'minY': 0, 'maxY': 14824}},
                    'players': players,
                    'tracks': [{'playerId': i, 'samples': track} for i, track in enumerate(samples)],
                    'events': all_events,
                    'mapEntities': map_entities,
                    'diagnostics': {'movementPackets': movement_packets, 'sampleCount': sum(map(len, samples)), 'opcodeHistogram': dict(opcodes)}}
