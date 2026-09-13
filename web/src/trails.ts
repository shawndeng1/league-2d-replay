import type {GameEvent,PositionSample,WorldPoint} from '../../shared/replay';
import {samplePlayerPosition} from './life';
/** Bounded display geometry, not new replay observations. At most 241 vertices. */
export function recentTrail(samples:readonly PositionSample[],time:number,seconds:number,lifeEvents:readonly GameEvent[]=[]){
  const start=Math.max(samples[0]?.timestamp??0,time-seconds),points:(WorldPoint&{age:number;breakBefore:boolean})[]=[];
  for(let t=start;t<=time;t+=.5){const p=samplePlayerPosition(samples,t,lifeEvents);if(!p)continue;const previous=points.at(-1);points.push({x:p.x,y:p.y,age:(time-t)/seconds,breakBefore:!previous||Math.hypot(p.x-previous.x,p.y-previous.y)>2000});}
  return points;
}
