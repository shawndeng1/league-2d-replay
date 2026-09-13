import type {GameEvent,PositionSample} from '../../shared/replay';
import {eventUpperBound} from './events';
import {samplePosition} from './math';
/** Input is a player's sorted deaths and respawns, not their kills/assists. */
export function playerLifeAt(events:readonly GameEvent[],time:number){
  const index=eventUpperBound(events,time)-1,event=events[index];
  if(event?.type==='CHAMPION_KILL'){
    const next=events[index+1];
    return {dead:true,event,respawnAt:next?.type==='CHAMPION_RESPAWN'?next.timestamp:undefined};
  }
  return {dead:false,event:event?.type==='CHAMPION_RESPAWN'?event:undefined,respawnAt:undefined};
}
export function samplePlayerPosition(samples:readonly PositionSample[],time:number,lifeEvents:readonly GameEvent[]=[]){
  const life=playerLifeAt(lifeEvents,time);
  const position=samplePosition(samples,life.dead&&life.event?life.event.timestamp:time);
  if(!position)return null;
  // A recorded respawn may precede the next movement sample by one server tick.
  // Use its actual spawn notification rather than showing the old corpse route.
  if(life.event&&(life.dead||position.previous<life.event.timestamp)&&life.event.x!==undefined&&life.event.y!==undefined)
    return {...position,x:life.event.x,y:life.event.y};
  return position;
}
export function indexLifeEvents(events:readonly GameEvent[],playerIds:readonly number[]){
  const result=new Map<number,GameEvent[]>(playerIds.map(id=>[id,[]]));
  for(const event of events){const id=event.type==='CHAMPION_KILL'?event.victimPlayerId:event.type==='CHAMPION_RESPAWN'?event.playerId:undefined;if(id!==undefined)result.get(id)?.push(event);}
  for(const values of result.values())values.sort((a,b)=>a.timestamp-b.timestamp||a.id.localeCompare(b.id));
  return result;
}
