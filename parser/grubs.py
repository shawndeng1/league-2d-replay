"""Partial Void Grub coverage: only kills with a camp announcement.

Never expands one camp notification into three kills. See rofl-format.md.
"""
import hashlib
import struct
from .events import last_plain_u32
from .notifications import name_hash
from .patch_16_18 import PLAYER_ENTITY_START

HORDE_HASH = name_hash('SRU_Horde')
HORDE_CATEGORY = 0xCB5A3F01
UNIT_DEATH = 0x043C


def normalize_grub_notifications(notices, blocks, engine, players, participants, duration):
    events=[]
    for notice in notices:
        if notice.category != HORDE_CATEGORY:
            continue  # Different semantics must be investigated separately.
        if notice.team == 'NEUTRAL':
            continue  # Corpus contains a timed neutral cleanup, not a capture.
        actors=[p for p in players if name_hash(p['championName'])==notice.actor_hash and p['team']==notice.team]
        if len(actors)!=1:raise ValueError('Ambiguous Void Grub announcement actor')
        player=actors[0]
        # Neutral-death script confirms the dying network ID. For grubs this
        # payload has no unit-name hash and reports self-removal, so it CANNOT
        # supply killer credit. That comes from the separate unit-death packet.
        removals=set()
        for block in blocks:
            if block.packet_id!=0x0119 or abs(block.timestamp-notice.block.timestamp)>=.000002:continue
            obs=engine.observe_decoder('scriptEvent',block.payload)
            if last_plain_u32(obs,0x20)!=0x60FD8A21 or last_plain_u32(obs,0x18)!=124:continue
            pointer=struct.unpack_from('<Q',obs.output_snapshot,0x10)[0]-engine.HEAP_BASE
            if not 0<=pointer<=len(obs.heap_snapshot)-124:raise ValueError('Invalid grub script vector')
            data=obs.heap_snapshot[pointer:pointer+124]
            tag,entity=struct.unpack_from('<II',data)
            if (tag==0x1d7 and entity==struct.unpack_from('<I',data,12)[0]
                    and entity==struct.unpack_from('<I',data,120)[0]==last_plain_u32(obs,0x28)):
                removals.add(entity)
        candidates=[]
        for block in blocks:
            if block.packet_id!=UNIT_DEATH or block.param not in removals:continue
            if abs(block.timestamp-notice.block.timestamp)>=.000002:continue
            obs=engine.observe_decoder('unitDeath',block.payload)
            # Same shared death-object killer field as towerDeath. Verified
            # against announcement champion hashes and final HORDE_KILLS.
            if last_plain_u32(obs,0x1c)==PLAYER_ENTITY_START+player['id']:
                candidates.append(block)
        if len(candidates)!=1:raise ValueError('Missing or ambiguous Void Grub death')
        if int(participants[player['id']].get('HORDE_KILLS','0'))<1:
            raise ValueError('Void Grub credit disagrees with final metadata')
        block=candidates[0]
        if not 0<=block.timestamp<=duration:raise ValueError('Invalid Void Grub timestamp')
        digest=hashlib.sha256(block.payload).hexdigest()[:12]
        events.append({'id':f'void-grub-{round(block.timestamp*1000)}-{block.param:x}-{digest}',
                       'timestamp':round(block.timestamp,6),'type':'OBJECTIVE_KILL','objective':'VOID_GRUB',
                       'coverage':'CAMP_ANNOUNCED_KILL_ONLY','killerPlayerId':player['id'],'killerTeam':notice.team,
                       'source':{'opcode':'0x043c','packetSize':len(block.payload),'rawTimestamp':block.timestamp,
                                 'entityId':block.param,'killerEntityId':PLAYER_ENTITY_START+player['id'],
                                 'corroboratingOpcode':'0x023d','confidence':'VERIFIED'}})
    if len({e['id'] for e in events})!=len(events):raise ValueError('Duplicate Void Grub notification')
    return sorted(events,key=lambda e:(e['timestamp'],e['id']))
