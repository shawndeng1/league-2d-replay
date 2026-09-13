import {describe,it,expect} from 'vitest';
import type {GameEvent} from '../../shared/replay';
import {getEventReviewStart,findEventsNearTimestamp,filterEvents,indexEvents,currentScore} from './events';
import {parseReplayUrlState,serializeReplayUrlState} from './urlState';
import {recentTrail} from './trails';
const source={opcode:'test fixture',packetSize:0,rawTimestamp:858,confidence:'VERIFIED' as const};
const kill:GameEvent={id:'kill-test',type:'CHAMPION_KILL',timestamp:858,killerPlayerId:1,victimPlayerId:7,source};
const objective:GameEvent={id:'objective-test',type:'OBJECTIVE_KILL',timestamp:900,objective:'DRAGON',source};
describe('review event helpers',()=>{
 it('seeks eight seconds before 14:18, and ten before objectives',()=>{expect(getEventReviewStart(kill)).toBe(850);expect(getEventReviewStart(objective)).toBe(890);expect(getEventReviewStart({...kill,timestamp:4})).toBe(0);});
 it('finds inclusive nearby events after forward and backward seeks',()=>{expect(findEventsNearTimestamp([kill,objective],861)).toEqual([kill]);expect(findEventsNearTimestamp([kill,objective],901)).toEqual([objective]);expect(findEventsNearTimestamp([kill,objective],0)).toEqual([]);expect(findEventsNearTimestamp([kill,objective],858)).toEqual([kill]);});
 it('filters categories and involved players without inventing assists',()=>{expect(filterEvents([kill,objective],'Kills')).toEqual([kill]);expect(filterEvents([kill,objective],'Objectives')).toEqual([objective]);expect(filterEvents([kill,objective],'Structures')).toEqual([]);expect(filterEvents([kill,objective],'All',7)).toEqual([kill]);expect(filterEvents([kill],'All',3)).toEqual([]);});
 it('indexes events and calculates time-relative counts',()=>{expect(indexEvents([objective,kill],[]).sorted).toEqual([kill,objective]);expect(currentScore([kill],857,1)).toEqual({kills:0,deaths:0});expect(currentScore([kill],858,1)).toEqual({kills:1,deaths:0});expect(currentScore([kill],858,7)).toEqual({kills:0,deaths:1});});
});
describe('replay links',()=>{
 it('round trips replay, time, player zero and event IDs',()=>{const state={replayId:'a'.repeat(64),time:842.25,player:0,event:'kill & test'};expect(parseReplayUrlState(serializeReplayUrlState(state))).toEqual(state);});
 it('rejects invalid timestamps and participant IDs',()=>{expect(parseReplayUrlState('/?t=Infinity&player=-1')).toEqual({time:0,replayId:undefined});expect(parseReplayUrlState('/?t=-2&player=1.5').time).toBe(0);});
});
describe('trails',()=>{it('bounds geometry and breaks across discontinuities',()=>{const points=recentTrail([{timestamp:0,x:0,y:0,speed:0},{timestamp:10,x:10000,y:10000,speed:0}],120,120);expect(points.length).toBeLessThanOrEqual(241);expect(points.find(p=>p.x===10000)?.breakBefore).toBe(true);});});
