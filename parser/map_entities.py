"""Persistent entities from exact-build keyframes, separate from kill events.

0x456 identifies towers, 0x181 supplies planar positions. Objective presence is
bounded by observed snapshots and a corroborated kill, never a guessed timer.
See docs/rofl-format.md for the intentionally incomplete lifecycle coverage.
"""
import re
import struct
from collections import defaultdict
from .events import last_plain_u32

TOWER_IDENTITY = 0x0456
ENTITY_POSITION = 0x0181
NEUTRAL_SNAPSHOT = 0x0287
NEUTRAL_REMOVAL = 0x0039


def decoded_string(obs, offset, engine):
    pointer, length = struct.unpack_from('<QI', obs.output_snapshot, offset)
    if length == 0:return ''
    start = pointer - engine.HEAP_BASE
    if not 0 < length <= 128 or not 0 <= start <= len(obs.heap_snapshot)-length:
        raise ValueError('Invalid map entity string')
    return obs.heap_snapshot[start:start+length].decode('ascii')


def decode_tower(block, engine):
    obs = engine.observe_decoder('towerIdentity', block.payload)
    if last_plain_u32(obs, 0x18) != block.param:
        raise ValueError('Tower identity disagrees with block entity')
    # Decoded object contains two client strings: gameplay tier and map name.
    tier = decoded_string(obs, 0x30, engine)
    name = decoded_string(obs, 0x40, engine)
    match = re.fullmatch(r'Turret_T(Order|Chaos)_L([012])_P([0-5])_\d+_0', name)
    if tier not in ('SR_Outer','SR_Inner','SR_Inhibitor','SR_Nexus'):
        return None  # Fountain lasers and unknown tower classes are not inferred.
    if not match:
        raise ValueError('Unsupported tower map name')
    team, lane, _ = match.groups()
    return {'id':f'tower-{block.param:x}', 'kind':'TOWER',
            'team':'BLUE' if team=='Order' else 'RED',
            'lane':{'0':'BOTTOM','1':'MIDDLE','2':'TOP'}[lane],
            'tier':tier.removeprefix('SR_').upper(), 'name':name,
            'source':{'identityOpcode':'0x0456','positionOpcode':'0x0181','confidence':'VERIFIED'}}


def decode_position(block, engine):
    obs = engine.observe_decoder('entityPosition', block.payload)
    if last_plain_u32(obs, 0x34) != block.param:
        raise ValueError('Position identity disagrees with block entity')
    # Object +0x10/+0x14 are plaintext f32 planar coordinates. +0x18 is
    # the snapshot time; these are not the attacker's death-packet coordinates.
    x,y = struct.unpack_from('<ff', obs.output_snapshot, 0x10)
    if not (-500 <= x <= 15500 and -500 <= y <= 15500):
        raise ValueError('Invalid map entity coordinates')
    return {'x':x,'y':y}


def extract_map_entities(reader, engine, events, neutral_removals):
    deaths=defaultdict(list)
    for event in events:
        if event.get('structure')=='TOWER':deaths[event['source']['entityId']].append(event)
    objectives={e['source']['entityId']:e for e in events
                if e.get('objective') in ('BARON','RIFT_HERALD')}
    # 0x0039's envelope parameter is correlated, not an assumed payload field.
    # Require a unique same-timestamp removal and a neutral keyframe at the pit.
    for event in events:
        if event.get('objective')!='DRAGON':continue
        matches=[entity for timestamp,entity in neutral_removals
                 if abs(timestamp-event['timestamp'])<.000002]
        if len(matches)==1:objectives[matches[0]]=event
    towers={}; positions={}; sightings={}; neutral=set()
    for block in reader.iter_blocks(streams={'keyframe'},
                                   opcodes={TOWER_IDENTITY,ENTITY_POSITION,NEUTRAL_SNAPSHOT},include_payload=True):
        if block.packet_id==TOWER_IDENTITY and block.timestamp==0:
            tower=decode_tower(block,engine)
            if tower:towers[block.param]=tower
        elif block.packet_id==NEUTRAL_SNAPSHOT and block.param in objectives:
            neutral.add((block.param,block.timestamp))
        elif block.packet_id==ENTITY_POSITION:
            if block.param in towers and block.timestamp==0:
                positions[block.param]=decode_position(block,engine)
            elif block.param in objectives and block.timestamp < objectives[block.param]['timestamp']:
                if (block.param,block.timestamp) in neutral:
                    sightings.setdefault(block.param,[]).append((block.timestamp,decode_position(block,engine)))
    result=[]
    if len(towers)!=22 or len(positions)!=22:
        raise ValueError('Expected 22 named tower positions in initial keyframe')
    for entity,tower in towers.items():
        transitions=[{'timestamp':0,'state':'ALIVE'}]
        for death in sorted(deaths.get(entity,[]),key=lambda e:e['timestamp']):
            if death['destroyedTeam']!=tower['team']:
                raise ValueError('Tower map name disagrees with death team')
            # Nexus towers can rebuild (observed repeated destruction in 93952).
            # Do not report them as permanently dead without a rebuild decoder.
            transitions.append({'timestamp':death['timestamp'],'state':'UNKNOWN' if tower['tier']=='NEXUS' else 'DESTROYED','eventId':death['id']})
            death.update(positions[entity],lane=tower['lane'],tier=tower['tier'],mapEntityId=tower['id'])
            death['source'].update(coordinateSource='initial-keyframe-0x0181',coordinateTimestamp=0,coordinateConfidence='VERIFIED')
        result.append({**tower,**positions[entity],'states':transitions})
    if set(deaths)-set(towers):raise ValueError('Unidentified tower death')
    for entity,event in objectives.items():
        observations=sightings.get(entity,[])
        if not observations:continue
        start,point=observations[0]
        # Independent spatial check on correlated neutral IDs. Summoner's Rift
        # pit neighborhoods are broad validation bounds, not invented positions.
        dragon=event['objective']=='DRAGON'
        if not ((8500 < point['x'] < 11500 and 3000 < point['y'] < 6500) if dragon else
                (3500 < point['x'] < 6500 and 8500 < point['y'] < 12000)):
            raise ValueError('Objective snapshot is outside its pit')
        identifier=f"objective-{entity:x}"
        result.append({'id':identifier,'kind':event['objective'],'name':event['objective'],**point,
                       'source':{'identityOpcode':event['source']['opcode'],'positionOpcode':'0x0181',
                                 'confidence':'LIKELY' if dragon else 'VERIFIED','presenceStart':'FIRST_KEYFRAME_OBSERVATION'},
                       'states':[{'timestamp':start,'state':'OBSERVED'},
                                 {'timestamp':event['timestamp'],'state':'DESTROYED','eventId':event['id']}]})
        event.update(point,mapEntityId=identifier)
        event['source'].update(coordinateSource='first-neutral-keyframe-0x0181',coordinateTimestamp=start,coordinateConfidence='VERIFIED')
    return result
