"""Narrow 16.18 Amumu origin observations; never decode general spell movement.

0x02c4 object +0x118 fingerprint 0x0a85b9cd (Tantrum hypothesis), origin at
+0x104/+0x10c and embedded time +0x110. All 323 candidates across three replays
have consistent identities/time. 253/262 coincident origins match within 4 units;
the other nine match the next observation 33-67ms later. Prefer movement within
100ms; only supplement already exhausted/stopped routes. See docs/rofl-format.md.
"""
import math
import struct
from bisect import bisect_left, bisect_right
from .patch_16_18 import PLAYER_ENTITY_START

ACTION_OPCODE=0x02c4
TANTRUM_FINGERPRINT=0x0a85b9cd
SOURCE_KIND='AMUMU_ACTION_ORIGIN'


def position_from_writes(writes,timestamp,entity):
    values={a:v&0xffffffff for a,s,v in writes if s==4}
    if values.get(0x118)!=TANTRUM_FINGERPRINT:return None
    if values.get(0x5c)!=entity or values.get(0x6c)!=entity:
        raise ValueError('Amumu action origin identity mismatch')
    def scalar(offset):
        if offset not in values:raise ValueError('Missing action origin scalar')
        value=struct.unpack('<f',struct.pack('<I',values[offset]))[0]
        if not math.isfinite(value):raise ValueError('Nonfinite action origin')
        return value
    x,y,clock=scalar(0x104),scalar(0x10c),scalar(0x110)
    if not math.isfinite(timestamp) or timestamp<0 or abs(clock-timestamp)>.002:
        raise ValueError('Amumu action origin time mismatch')
    if not 0<=x<=14716 or not 0<=y<=14824:raise ValueError('Action origin outside map')
    return {'timestamp':round(timestamp,6),'x':x,'y':y,'positionOnly':True,
            'positionSource':SOURCE_KIND}


def decode_action_position(engine,block,players):
    player=block.param-PLAYER_ENTITY_START
    if not 0<=player<len(players) or players[player]['championName']!='Amumu':return None
    observation=engine.observe_decoder('amumuActionOrigin',block.payload)
    sample=position_from_writes(observation.output_writes,block.timestamp,block.param)
    return None if sample is None else (player,sample)


def supplement_track(track,candidates,life_events):
    """Prefer original samples, never truncate an active route or a dead interval.

Position-only samples hold until the next observation/command. No speed or path
is fabricated. Compare against original commands, not previously inserted points.
"""
    times=[s['timestamp'] for s in track]
    life=sorted(life_events,key=lambda e:e['timestamp'])
    life_times=[e['timestamp'] for e in life]
    inserted={}
    for sample in sorted(candidates,key=lambda s:s['timestamp']):
        t=sample['timestamp'];index=bisect_left(times,t)
        if index==0 or index==len(track):continue
        a,b=track[index-1],track[index]
        if min(t-a['timestamp'],b['timestamp']-t)<=.1:continue
        state=bisect_right(life_times,t)-1
        if state>=0 and life[state]['type']=='CHAMPION_KILL':continue
        path=a.get('path',[])
        if not path:continue  # Do not interpret an unknown command as a stop.
        length=sum(math.hypot(q['x']-p['x'],q['y']-p['y']) for p,q in zip(path,path[1:]))
        speed=a.get('speed',0)
        if speed>0 and length>speed*(t-a['timestamp']):continue
        held=path[-1] if speed>0 else path[0]
        if math.hypot(sample['x']-held['x'],sample['y']-held['y'])<=4:continue
        inserted[t]=sample
    return sorted([*track,*inserted.values()],key=lambda s:s['timestamp'])
