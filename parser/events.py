"""Exact-build champion deaths. Evidence and field confidence: docs/rofl-format.md.

Offsets describe the client's *decoded object*, never guessed payload byte indexes.
The final four-byte write is plaintext; subsequent byte writes re-obfuscate it.
"""
import hashlib
import math
import struct
from bisect import bisect_right
from collections import Counter
from pathlib import Path
from rofllens.decoders.emulator import UnicornDecoderEngine
from rofllens.errors import SemanticDecodeError
from .patch_16_18 import PLAYER_ENTITY_START

DEATH_OPCODE = 0x0475
RESPAWN_OPCODE = 0x01B3
DRAGON_OPCODE = 0x002D
# Plaintext writes in the exact-build respawn notification's decoded object.
# All 71 packets place these coordinates at the correct team's spawn; the
# notification follows the independently decoded death timer (see format docs).
RESPAWN_X_OFFSET = 0x10
RESPAWN_Y_OFFSET = 0x14
VICTIM_ENTITY_OFFSET = 0x30
VICTIM_NAME_POINTER_OFFSET = 0x38
KILLER_ENTITY_OFFSET = 0x58

def last_plain_u32(observation, offset):
    values = [value & 0xffffffff for address,size,value in observation.output_writes
              if address == offset and size == 4]
    if not values:
        raise ValueError(f'Missing decoded death field at object+{offset:#x}')
    return values[-1]

class DeathDecoder:
    def __init__(self, client_exe):
        # Runtime always checks the user's executable and section hashes. No cached
        # code, game process attachment, or modifications to the installed client.
        self.engine = UnicornDecoderEngine(Path(__file__).parent/'profiles/16.18-events.json', client_exe)

    def decode_dragon(self, block):
        """Team dragon notification; no inferred killer, elemental type or position.

        Decoded object+0x10 is a u16 team, read before byte re-obfuscation.
        All 18 occurrences across five replays match final team dragon totals.
        Object+0x18's vector and +0x28 are not participant/assist fields.
        See docs/rofl-format.md for the independent observations and limits.
        """
        if not math.isfinite(block.timestamp) or block.timestamp < 0:
            raise ValueError('Invalid dragon timestamp')
        observation = self.engine.observe_decoder('dragonNotification',block.payload)
        values=[v for a,s,v in observation.output_writes if a==0x10 and s==2]
        if not values or values[-1] not in (100,200):
            raise ValueError('Unknown dragon notification team')
        team='BLUE' if values[-1]==100 else 'RED'
        timestamp=round(block.timestamp,6)
        digest=hashlib.sha256(block.payload).hexdigest()[:12]
        return {'id':f'dragon-{round(timestamp*1000)}-{team.lower()}-{digest}',
                'timestamp':timestamp,'type':'OBJECTIVE_KILL','objective':'DRAGON','killerTeam':team,
                'source':{'opcode':'0x002d','packetSize':len(block.payload),
                          'rawTimestamp':block.timestamp,'confidence':'VERIFIED'}}

    def decode(self, block, players):
        if not math.isfinite(block.timestamp) or block.timestamp < 0:
            raise ValueError('Invalid event timestamp')
        observation = self.engine.observe_decoder('championDeath', block.payload)
        victim = last_plain_u32(observation, VICTIM_ENTITY_OFFSET)
        killer = last_plain_u32(observation, KILLER_ENTITY_OFFSET)
        pointer,length = struct.unpack_from('<QI', observation.output_snapshot, VICTIM_NAME_POINTER_OFFSET)
        start = pointer-self.engine.HEAP_BASE
        if not 0 < length <= 256 or start < 0 or start+length > len(observation.heap_snapshot):
            raise ValueError('Invalid death victim name range')
        name = observation.heap_snapshot[start:start+length].decode('utf-8')
        victim_id = victim-PLAYER_ENTITY_START
        if not 0 <= victim_id < len(players) or players[victim_id]['championName'] != name:
            raise ValueError('Death victim identity disagrees with participant mapping')
        killer_id = killer-PLAYER_ENTITY_START
        if 0 <= killer_id < len(players) and players[killer_id]['team'] == players[victim_id]['team']:
            raise ValueError('Champion kill has same-team killer and victim')
        timestamp = round(block.timestamp,6)
        digest = hashlib.sha256(block.payload).hexdigest()[:12]
        event = {'id':f'kill-{round(timestamp*1000)}-{victim_id}-{digest}',
                 'timestamp':timestamp,'type':'CHAMPION_KILL','victimPlayerId':victim_id,
                 'source':{'opcode':'0x0475','packetSize':len(block.payload),'rawTimestamp':block.timestamp,
                           'victimEntityId':victim,'killerEntityId':killer,'confidence':'VERIFIED'}}
        if 0 <= killer_id < len(players): event['killerPlayerId']=killer_id
        # Context entities are NOT verified assists. Omission means unavailable.
        return event

    def decode_respawn(self, block, players):
        player_id = block.param-PLAYER_ENTITY_START
        if not 0 <= player_id < len(players):
            raise ValueError('Respawn entity is outside the verified participant range')
        if not math.isfinite(block.timestamp) or block.timestamp < 0:
            raise ValueError('Invalid respawn timestamp')
        observation = self.engine.observe_decoder('championRespawn',block.payload)
        def coordinate(offset):
            return struct.unpack('<f',struct.pack('<I',last_plain_u32(observation,offset)))[0]
        x,y=coordinate(RESPAWN_X_OFFSET),coordinate(RESPAWN_Y_OFFSET)
        if not all(math.isfinite(v) and 0<=v<=15000 for v in (x,y)):
            raise ValueError('Invalid respawn coordinates')
        at_spawn=(x<1000 and y<1000) if players[player_id]['team']=='BLUE' else (x>13500 and y>13500)
        if not at_spawn: raise ValueError('Respawn location disagrees with team spawn region')
        timestamp=round(block.timestamp,6)
        digest=hashlib.sha256(block.payload).hexdigest()[:12]
        return {'id':f'respawn-{round(timestamp*1000)}-{player_id}-{digest}',
                'timestamp':timestamp,'type':'CHAMPION_RESPAWN','playerId':player_id,'x':x,'y':y,
                'source':{'opcode':'0x01b3','packetSize':len(block.payload),'rawTimestamp':block.timestamp,
                          'entityId':block.param,'confidence':'VERIFIED','coordinateSource':'respawn notification',
                          'coordinateConfidence':'VERIFIED'}}

def validate_dragons(events, participants, duration):
    """Fail closed if the supported notification does not cover metadata totals."""
    if len({e['id'] for e in events}) != len(events):
        raise ValueError('Duplicate dragon identifiers')
    if any(not 0 <= e['timestamp'] <= duration for e in events):
        raise ValueError('Dragon outside replay duration')
    counts=Counter(e['killerTeam'] for e in events)
    for team,raw_team in [('BLUE','100'),('RED','200')]:
        roster=[p for p in participants if p['TEAM']==raw_team]
        if any('DRAGON_KILLS' not in p for p in roster):
            raise ValueError('Missing dragon metadata for validation')
        if counts[team]!=sum(int(p['DRAGON_KILLS']) for p in roster):
            raise ValueError(f'Dragon notifications disagree with {team} final metadata')
    return events

def validate_deaths(events, players, duration):
    events.sort(key=lambda e:(e['timestamp'],e['id']))
    if len({e['id'] for e in events}) != len(events):
        raise ValueError('Duplicate death event identifiers')
    kills=Counter(e.get('killerPlayerId') for e in events)
    deaths=Counter(e['victimPlayerId'] for e in events)
    for event in events:
        if not 0 <= event['timestamp'] <= duration: raise ValueError('Death outside replay duration')
    for p in players:
        for field,counts in [('kills',kills),('deaths',deaths)]:
            expected=p.get('finalStats',{}).get(field)
            if expected is not None and counts[p['id']] != expected:
                raise ValueError(f"Decoded {field} disagree with final metadata for {p['championName']}")
    return events

def attach_observed_locations(events, tracks):
    """Nearby observed movement origins only; not coordinates in the death packet."""
    times=[[s['timestamp'] for s in track] for track in tracks]
    for event in events:
        player=event['victimPlayerId']
        index=bisect_right(times[player],event['timestamp'])-1
        if index < 0: continue
        sample=tracks[player][index]
        if event['timestamp']-sample['timestamp'] <= .5:
            event.update(x=sample['x'],y=sample['y'])
            event['source'].update(coordinateSource='prior movement origin',coordinateTimestamp=sample['timestamp'],coordinateConfidence='LIKELY')

def merge_life_events(deaths,respawns,duration):
    """Pair actual notifications, never manufacture respawns from a timer.

    Four fixture champions stay dead at match end. Absence of a later respawn
    is preserved, rather than extending gameplay past the recorded duration.
    """
    events=sorted([*deaths,*respawns],key=lambda e:(e['timestamp'],e['id']))
    pending={}
    if len({e['id'] for e in events})!=len(events):raise ValueError('Duplicate life event IDs')
    for event in events:
        if not 0<=event['timestamp']<=duration:raise ValueError('Life event outside replay duration')
        if event['type']=='CHAMPION_KILL':
            player=event['victimPlayerId']
            if player in pending:raise ValueError('Champion died again without a recorded respawn')
            pending[player]=event
        else:
            player=event['playerId']
            death=pending.pop(player,None)
            if death is None or event['timestamp']<=death['timestamp']:
                raise ValueError('Respawn has no preceding champion death')
            event['deathEventId']=death['id']
    return events
