"""Exact-build neutral identity prefix, not a complete 0x0287 decoder.

The bounded decoder stops after the unit-name field succeeds, before the
unsupported tail. See docs/rofl-format.md for the instruction/field evidence.
"""
import hashlib
import math
import struct
from collections import Counter, defaultdict
from .events import last_plain_u32
from .map_entities import decoded_string
from .patch_16_18 import PLAYER_ENTITY_START

NEUTRAL_CREATE = 0x0287
UNIT_DEATH = 0x043C
ENTITY_OFFSET = 0x2C
INSTANCE_NAME_OFFSET = 0x38
UNIT_NAME_OFFSET = 0xA0
POSITION_X_OFFSET = 0x60
POSITION_Z_OFFSET = 0x68  # Client x/height/z -> normalized planar x/y.


def decode_neutral_identity(block, engine, *, unit_filter=None):
    obs=engine.observe_decoder('neutralIdentityPrefix',block.payload)
    # The prefix stop is within the function, after the successful unit-name
    # branch. A normal early failure RET also reaches the emulator stop address
    # (its synthetic return address), but has a different stack pointer. Five
    # pushes plus sub rsp,0x20 in the verified prologue reserve exactly 0x48.
    import unicorn.x86_const as x86
    expected_stack=engine.STACK_BASE+engine.STACK_SIZE-0x1000-0x48
    if (engine._uc.reg_read(x86.UC_X86_REG_RSP)!=expected_stack or
            engine._uc.reg_read(x86.UC_X86_REG_RIP)!=engine.profile['imageBase']+0xF19037):
        raise ValueError('Neutral identity prefix did not complete')
    unit=decoded_string(obs,UNIT_NAME_OFFSET,engine)
    # Other unit classes can use unestablished envelope-ID semantics. Their
    # identity/position fields are irrelevant to the grub adapter.
    if unit_filter is not None and unit!=unit_filter:return None
    entity=last_plain_u32(obs,ENTITY_OFFSET)
    if entity!=block.param:raise ValueError('Neutral identity disagrees with block entity')
    instance=decoded_string(obs,INSTANCE_NAME_OFFSET,engine)
    def floating(offset):return struct.unpack('<f',struct.pack('<I',last_plain_u32(obs,offset)))[0]
    point={'x':floating(POSITION_X_OFFSET),'y':floating(POSITION_Z_OFFSET)}
    if any(not math.isfinite(v) or not -500<=v<=15500 for v in point.values()):
        raise ValueError('Invalid neutral entity coordinates')
    return {'entityId':entity,'unitName':unit,'instanceName':instance,**point}


def extract_grub_entities(reader, engine, players, participants, duration, announced_events):
    sightings=defaultdict(list)
    for block in reader.iter_blocks(streams={'gameChunk','keyframe'},opcodes={NEUTRAL_CREATE},include_payload=True):
        identity=decode_neutral_identity(block,engine,unit_filter='SRU_Horde')
        if identity is None:continue
        if not identity['instanceName'].startswith('SRU_Horde.'):
            raise ValueError('Conflicting Void Grub instance name')
        if not (3500<identity['x']<6500 and 8500<identity['y']<12000):
            raise ValueError('Void Grub identity is outside its pit')
        if not 0<=block.timestamp<=duration:raise ValueError('Invalid grub observation time')
        sightings[block.param].append((block.timestamp,identity))
    deaths=defaultdict(list)
    for block in reader.iter_blocks(streams={'gameChunk'},opcodes={UNIT_DEATH},include_payload=True):
        if block.param in sightings:deaths[block.param].append(block)
    events=[];entities=[]
    for entity,observations in sightings.items():
        observations.sort(key=lambda row:row[0]);start,identity=observations[0]
        if len(deaths[entity])!=1:raise ValueError('Missing or repeated individual grub death')
        block=deaths[entity][0]
        if not start<=block.timestamp<=duration:raise ValueError('Invalid individual grub lifetime')
        if any(t>block.timestamp+.000002 for t,_ in observations):raise ValueError('Grub observed after death')
        killer=last_plain_u32(engine.observe_decoder('unitDeath',block.payload),0x1C)
        player_id=killer-PLAYER_ENTITY_START
        identifier=f'objective-{entity:x}'
        point={'x':identity['x'],'y':identity['y']}
        terminal={'timestamp':round(block.timestamp,6),'state':'DESPAWNED'}
        if 0<=player_id<len(players):
            digest=hashlib.sha256(block.payload).hexdigest()[:12]
            event={'id':f'void-grub-{round(block.timestamp*1000)}-{entity:x}-{digest}',
                   'timestamp':round(block.timestamp,6),'type':'OBJECTIVE_KILL','objective':'VOID_GRUB',
                   'killerPlayerId':player_id,'killerTeam':players[player_id]['team'],'mapEntityId':identifier,
                   'source':{'opcode':'0x043c','packetSize':len(block.payload),'rawTimestamp':block.timestamp,
                             'entityId':entity,'killerEntityId':killer,'confidence':'VERIFIED',
                             'corroboratingOpcode':'0x0287'}}
            # First-observed position locates the persistent marker, not an
            # asserted death location: monsters can move during combat.
            events.append(event)
            terminal={'timestamp':event['timestamp'],'state':'DESTROYED','eventId':event['id']}
        elif killer!=entity:
            raise ValueError('Unidentified individual Void Grub killer')
        entities.append({'id':identifier,'kind':'VOID_GRUB','name':identity['instanceName'],**point,
                         'source':{'identityOpcode':'0x0287','positionOpcode':'0x0287','confidence':'VERIFIED',
                                   'presenceStart':'FIRST_OBSERVATION'},
                         'states':[{'timestamp':start,'state':'OBSERVED'},terminal]})
    actual=Counter(e['killerPlayerId'] for e in events)
    for player in players:
        if actual[player['id']]!=int(participants[player['id']].get('HORDE_KILLS','0')):
            raise ValueError('Individual Void Grub kills disagree with final metadata')
    indexed={e['id']:e for e in events}
    for announced in announced_events:
        event=indexed.get(announced['id'])
        if event is None or event['killerPlayerId']!=announced['killerPlayerId']:
            raise ValueError('Individual grub death disagrees with camp announcement')
    return sorted(events,key=lambda e:(e['timestamp'],e['id'])),entities
