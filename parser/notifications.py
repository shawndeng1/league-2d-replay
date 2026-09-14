"""Exact 16.18 review notifications; offsets refer to decoded client objects.

Evidence, cross-packet correlations and unknown fields: docs/rofl-format.md.
Unknown notification kinds are ignored, never converted into guessed events.
"""
import hashlib
import math
import struct
from collections import Counter
from dataclasses import dataclass
from .events import last_plain_u32
from .patch_16_18 import PLAYER_ENTITY_START

ANNOUNCEMENT_OPCODE=0x023D
SCRIPT_EVENT_OPCODE=0x0119
TOWER_DEATH_OPCODE=0x0463
BUILDING_DEATH_OPCODE=0x0431
TOWER_CREDIT_OPCODE=0x0406
NOTIFICATION_OPCODES={ANNOUNCEMENT_OPCODE,SCRIPT_EVENT_OPCODE,TOWER_DEATH_OPCODE,BUILDING_DEATH_OPCODE,TOWER_CREDIT_OPCODE}

def name_hash(name):
    """Case-insensitive SDBM name hash, verified with champion and unit names."""
    value=0
    for byte in name.lower().encode('ascii'):
        value=(value*65599+byte)&0xffffffff
    return value

OBJECTIVES={name_hash('SRU_Baron'):'BARON',name_hash('SRU_RiftHerald'):'RIFT_HERALD'}
TURRET_HASH=name_hash('Turret')
# Decoded announcement category, established by matching every BARRACKS_KILLED
# credit and the building death packet. The original category string is unknown.
INHIBITOR_CATEGORY=0x18564B76
NEUTRAL_DEATH_SCRIPT=0x60FD8A21

@dataclass
class Announcement:
    block: object
    actor_hash: int
    category: int
    target_hash: int
    team: str

@dataclass
class ObjectiveNotice:
    block: object
    target_hash: int
    entity: int
    killer: int

@dataclass
class StructureDeath:
    block: object
    credited: int
    killer: int

@dataclass
class TowerCredit:
    block: object
    credited: int
    entity: int

class ReviewNotifications:
    def __init__(self,engine):
        self.engine=engine
        self.announcements=[]
        self.grubs=[]
        self.objectives=[]
        self.towers=[]
        self.buildings=[]
        self.tower_credits=[]

    def accept(self,block):
        if not math.isfinite(block.timestamp) or block.timestamp<0:
            raise ValueError('Invalid notification timestamp')
        if block.packet_id==ANNOUNCEMENT_OPCODE:
            obs=self.engine.observe_decoder('announcement',block.payload)
            actor=last_plain_u32(obs,0x10)
            category=last_plain_u32(obs,0x18)
            target=last_plain_u32(obs,0x1c)
            if target not in OBJECTIVES and target!=name_hash('SRU_Horde') and target!=TURRET_HASH and category!=INHIBITOR_CATEGORY:
                return
            team=last_plain_u32(obs,0x20)
            if team not in (100,200,300):raise ValueError('Unknown announcement team')
            (self.grubs if target==name_hash('SRU_Horde') else self.announcements).append(Announcement(block,actor,category,target,{100:'BLUE',200:'RED',300:'NEUTRAL'}[team]))
        elif block.packet_id==SCRIPT_EVENT_OPCODE:
            obs=self.engine.observe_decoder('scriptEvent',block.payload)
            if last_plain_u32(obs,0x20)!=NEUTRAL_DEATH_SCRIPT:return
            # Object+0x10 is a byte-vector pointer, +0x18 is its logical length.
            # The relevant script payload is a 124-byte serialized structure:
            # +4 and +12 repeat the dying entity; +108 is its SDBM unit-name
            # hash; +120 is the credited killer, repeated at object+0x28.
            pointer=struct.unpack_from('<Q',obs.output_snapshot,0x10)[0]
            length=last_plain_u32(obs,0x18)
            start=pointer-self.engine.HEAP_BASE
            if length!=124 or start<0 or start+length>len(obs.heap_snapshot):
                raise ValueError('Unsupported neutral-death script layout')
            data=obs.heap_snapshot[start:start+length]
            target=struct.unpack_from('<I',data,108)[0]
            if target not in OBJECTIVES:return
            tag,entity=struct.unpack_from('<II',data)
            duplicate=struct.unpack_from('<I',data,12)[0]
            killer=struct.unpack_from('<I',data,120)[0]
            if tag!=0x1d7 or entity!=duplicate or killer!=last_plain_u32(obs,0x28):
                raise ValueError('Neutral-death identity fields disagree')
            self.objectives.append(ObjectiveNotice(block,target,entity,killer))
        elif block.packet_id==TOWER_DEATH_OPCODE:
            obs=self.engine.observe_decoder('towerDeath',block.payload)
            # Shared death-object +0x1c is actual killer. Spatial fields in
            # this object describe the killer, not the destroyed structure.
            killer=last_plain_u32(obs,0x1c)
            self.towers.append(StructureDeath(block,killer,killer))
        elif block.packet_id==BUILDING_DEATH_OPCODE:
            obs=self.engine.observe_decoder('buildingDeath',block.payload)
            # Separate credited and physical killer IDs. In the primary match
            # Syndra receives one inhibitor credit for a minion's final hit.
            self.buildings.append(StructureDeath(block,last_plain_u32(obs,0x10),last_plain_u32(obs,0x14)))
        elif block.packet_id==TOWER_CREDIT_OPCODE:
            obs=self.engine.observe_decoder('towerCredit',block.payload)
            # Global notification: credited entity at +0x10, tower at +0x14.
            # 5640962900 at 1040.206s credits Vladimir despite a minion hit.
            self.tower_credits.append(TowerCredit(block,last_plain_u32(obs,0x10),last_plain_u32(obs,0x14)))

    def normalize(self,players,participants,duration):
        def player_id(entity):
            index=entity-PLAYER_ENTITY_START
            return index if 0<=index<len(players) else None
        def candidates(notice,rows):
            return [r for r in rows if abs(r.block.timestamp-notice.block.timestamp)<.000002]
        def one(rows):
            if len(rows)!=1:raise ValueError('Missing or ambiguous corroborating notification')
            return rows[0]
        def source(block,entity,killer,corroboration):
            return {'opcode':f'0x{block.packet_id:04x}','packetSize':len(block.payload),
                    'rawTimestamp':block.timestamp,'entityId':entity,'killerEntityId':killer,
                    'confidence':'VERIFIED','corroboratingOpcode':f'0x{corroboration.packet_id:04x}'}
        def base(block,prefix,entity):
            timestamp=round(block.timestamp,6)
            digest=hashlib.sha256(block.payload).hexdigest()[:12]
            return {'id':f'{prefix}-{round(timestamp*1000)}-{entity:x}-{digest}','timestamp':timestamp}

        events=[]
        for notice in self.objectives:
            pid=player_id(notice.killer)
            actor_hash=name_hash(players[pid]['championName']) if pid is not None else notice.target_hash
            ann=one([a for a in candidates(notice,self.announcements) if a.target_hash==notice.target_hash
                     and a.actor_hash==actor_hash])
            if pid is None:
                # 5640901584: Herald removes itself at match end. Both IDs are
                # the same neutral entity and the announcement team is 300.
                # Metadata correctly records zero Herald kills. Do not turn
                # this correlated self-removal into an objective capture.
                if notice.killer==notice.entity and ann.team=='NEUTRAL':continue
                raise ValueError('Objective credit is not a known participant')
            if ann.team!=players[pid]['team']:raise ValueError('Objective team disagrees with killer')
            kind=OBJECTIVES[notice.target_hash]
            events.append({**base(notice.block,kind.lower(),notice.entity),'type':'OBJECTIVE_KILL',
                           'objective':kind,'killerTeam':ann.team,'killerPlayerId':pid,
                           'source':source(notice.block,notice.entity,notice.killer,ann.block)})
        if len(self.objectives)!=sum(a.target_hash in OBJECTIVES for a in self.announcements):
            raise ValueError('Objective announcement and script counts disagree')

        used_towers=set()
        credits=Counter()
        for ann in self.announcements:
            kind='TOWER' if ann.target_hash==TURRET_HASH else 'INHIBITOR' if ann.category==INHIBITOR_CATEGORY else None
            if kind is None:continue
            if ann.team not in ('BLUE','RED'):raise ValueError('Unknown structure destruction team')
            deaths=candidates(ann,self.towers if kind=='TOWER' else self.buildings)
            # Known champion actor names disambiguate simultaneous notifications.
            deaths=[d for d in deaths if player_id(d.killer) is None or
                    name_hash(players[player_id(d.killer)]['championName'])==ann.actor_hash]
            death=one(deaths)
            if kind=='TOWER':
                if id(death) in used_towers:raise ValueError('Repeated tower correlation')
                used_towers.add(id(death))
                credit=one([r for r in candidates(death,self.tower_credits) if r.entity==death.block.param])
                credited_entity=credit.credited
            else:
                credited_entity=death.credited
            credited=player_id(credited_entity)
            if credited is not None:
                if players[credited]['team']!=ann.team:raise ValueError('Structure credit team disagrees')
                credits[kind,credited]+=1
            event={**base(death.block,kind.lower(),death.block.param),'type':'STRUCTURE_DESTROYED',
                   'structure':kind,'destroyedTeam':'RED' if ann.team=='BLUE' else 'BLUE',
                   'source':source(death.block,death.block.param,death.killer,ann.block)}
            # Keep credit in debug provenance; no unsupported lane or location.
            event['source']['creditedEntityId']=credited_entity
            if kind=='TOWER':event['source']['creditOpcode']='0x0406'
            events.append(event)
        if len(used_towers)!=len(self.towers) or len(self.tower_credits)!=len(self.towers):
            raise ValueError('Unmatched tower death or credit')
        for kind,field in [('BARON','BARON_KILLS'),('RIFT_HERALD','RIFT_HERALD_KILLS')]:
            counts=Counter(e.get('killerPlayerId') for e in events if e.get('objective')==kind)
            for p in players:
                if counts[p['id']]!=int(participants[p['id']][field]):
                    raise ValueError(f'{kind} credits disagree with final metadata')
        for kind,field in [('TOWER','TURRETS_KILLED'),('INHIBITOR','BARRACKS_KILLED')]:
            for p in players:
                if credits[kind,p['id']]!=int(participants[p['id']][field]):
                    raise ValueError(f'{kind} credits disagree with final metadata')
        for team,raw in [('BLUE','100'),('RED','200')]:
            totals={int(p['FRIENDLY_TURRET_LOST']) for p in participants if p['TEAM']==raw}
            count=sum(e.get('structure')=='TOWER' and e['destroyedTeam']==team for e in events)
            if totals!={count}:raise ValueError('Tower team losses disagree with metadata')
        if len({e['id'] for e in events})!=len(events) or any(not 0<=e['timestamp']<=duration for e in events):
            raise ValueError('Invalid notification event IDs or timestamps')
        return sorted(events,key=lambda e:(e['timestamp'],e['id']))
