import {expect,it} from 'vitest';
import type {GameEvent} from '../../shared/replay';
import {objectiveMapAnchor} from './eventIcons';
import {eventLabel,getEventReviewStart,findEventsNearTimestamp} from './events';

const source={opcode:'fixture',packetSize:0,rawTimestamp:100,confidence:'VERIFIED' as const};
const dragon:GameEvent={id:'dragon',type:'OBJECTIVE_KILL',objective:'DRAGON',timestamp:100,source};
it('scales image annotations without creating structure positions or modifying replay data',()=>{
  expect(objectiveMapAnchor(dragon,512,512)).toEqual({x:343,y:360});
  expect(objectiveMapAnchor({...dragon,objective:'BARON'},1024,1024)).toEqual({x:340,y:296});
  expect(objectiveMapAnchor({...dragon,objective:'RIFT_HERALD'},512,512)).toEqual({x:170,y:148});
  expect(objectiveMapAnchor({id:'tower',type:'STRUCTURE_DESTROYED',structure:'TOWER',destroyedTeam:'BLUE',timestamp:100,source},512,512)).toBeUndefined();
  expect(dragon.x).toBeUndefined();expect(dragon.y).toBeUndefined();
});
it('shows objective flashes only in the event window, including backward seeks',()=>{
  expect(findEventsNearTimestamp([dragon],99,2.5)).toEqual([]);
  expect(findEventsNearTimestamp([dragon],100,2.5)).toEqual([dragon]);
  expect(findEventsNearTimestamp([dragon],103,2.5)).toEqual([]);
  expect(findEventsNearTimestamp([dragon],101,2.5)).toEqual([dragon]);
});

it('labels partial grub coverage and seeks ten seconds before its verified kill',()=>{
  const grub:GameEvent={...dragon,objective:'VOID_GRUB',coverage:'CAMP_ANNOUNCED_KILL_ONLY',killerTeam:'BLUE'};
  expect(getEventReviewStart(grub)).toBe(90);
  expect(eventLabel(grub,[])).toContain('camp notification; partial coverage');
  expect(objectiveMapAnchor(grub,512,512)).toEqual({x:170,y:148});
});
