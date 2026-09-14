import type { PositionSample, WorldBounds } from '../../shared/replay';

export const DEFAULT_BOUNDS: WorldBounds = {minX: 0, maxX: 14716, minY: 0, maxY: 14824};
export function worldToMap(x: number, y: number, width = 800, height = 800, bounds = DEFAULT_BOUNDS) {
  return {x: (x-bounds.minX)/(bounds.maxX-bounds.minX)*width, y: (bounds.maxY-y)/(bounds.maxY-bounds.minY)*height};
}
/** Last sample at or before time, or -1 for an empty track. O(log n). */
export function findFrameAtTime(samples: readonly PositionSample[], time: number): number {
  if (!samples.length) return -1;
  let lo = 0, hi = samples.length;
  while (lo < hi) { const mid = (lo+hi) >>> 1; if (samples[mid].timestamp <= time) lo = mid+1; else hi = mid; }
  return Math.max(0, lo-1);
}
export function interpolatePosition(a: PositionSample, b: PositionSample, time: number) {
  const span = b.timestamp-a.timestamp;
  const t = span <= 0 ? 0 : Math.max(0, Math.min(1, (time-a.timestamp)/span));
  return {x: a.x+(b.x-a.x)*t, y: a.y+(b.y-a.y)*t};
}
/** Route prediction stays bounded by its recorded endpoint. */
function routePositionAtDistance(a:PositionSample,distance:number){
  let point=a.path![0];
  for(let i=1;i<a.path!.length;i++){
    const next=a.path![i];
    const length=Math.hypot(next.x-point.x,next.y-point.y);
    if(length>0&&distance<length){const f=distance/length;return {x:point.x+(next.x-point.x)*f,y:point.y+(next.y-point.y)*f};}
    distance-=length;point=next;
  }
  return {x:point.x,y:point.y};
}
function routePosition(a:PositionSample,elapsed:number){
  return routePositionAtDistance(a,Math.max(0,elapsed)*Math.max(0,a.speed??0));
}
/** Locate a later observation on the commanded polyline, retaining its bends. */
function projectOntoRoute(a:PositionSample,b:PositionSample){
  let total=0,best={distance:0,error:Infinity,x:a.x,y:a.y};
  for(let i=1;i<a.path!.length;i++){
    const p=a.path![i-1],q=a.path![i],dx=q.x-p.x,dy=q.y-p.y;
    const length=Math.hypot(dx,dy);if(!length)continue;
    const t=Math.max(0,Math.min(1,((b.x-p.x)*dx+(b.y-p.y)*dy)/(length*length)));
    const x=p.x+dx*t,y=p.y+dy*t,error=Math.hypot(b.x-x,b.y-y);
    if(error<best.error)best={distance:total+t*length,error,x,y};
    total+=length;
  }
  return {...best,total};
}
export function samplePosition(samples: readonly PositionSample[], time: number) {
  const index = findFrameAtTime(samples, time);
  if (index < 0) return null;
  const a = samples[index], b = samples[Math.min(index+1, samples.length-1)];
  if(a.positionOnly)return {x:a.x,y:a.y,previous:a.timestamp,next:b.timestamp};
  if (a.path?.length) {
    // Follow the recorded route at its recorded speed until the next update.
    // A long packet gap means no new command, not necessarily no movement.
    // Exhausted routes stay at their endpoint; never extrapolate beyond it.
    let point=routePosition(a,time-a.timestamp);
    const span=b.timestamp-a.timestamp;
    // A recorded speed is instantaneous, not a promise for the entire gap.
    // Yi at 25.545s and Ashe at 26.414s in 5640962900 otherwise overshoot
    // by ~154/440 units, then jump backwards. When the next real origin is
    // near the interior of this same route, pace traversal by observed progress.
    // This is average-speed interpolation; exact speed changes remain unknown.
    if(a.path.length>1&&(a.speed??0)>0&&span>2&&span<=15){
      const target=projectOntoRoute(a,b),ratio=target.distance/(a.speed!*span);
      // Do not stretch a route that finished before a later idle update, or
      // turn a recall/off-route relocation into travel across the map.
      if(target.error<=32&&target.distance>32&&target.distance<target.total-32&&ratio>=.5&&ratio<=1.25){
        const fraction=Math.max(0,Math.min(1,(time-a.timestamp)/span));
        point=routePositionAtDistance(a,target.distance*fraction);
        point.x+=(b.x-target.x)*fraction;point.y+=(b.y-target.y)*fraction;
      }
    }
    // Replay origins periodically correct route/speed prediction. Blend only
    // small corrections across short moving intervals, reaching the next real
    // origin exactly. This is display interpolation, not new replay samples.
    // Large relocations and explicit stops retain raw behavior; long gaps
    // qualify only for the separate route-progress check above.
    if(a.path.length>1&&(a.speed??0)>0&&span>0&&span<=2){
      const end=routePosition(a,span),dx=b.x-end.x,dy=b.y-end.y;
      const limit=Math.min(100,Math.max(48,(a.speed??0)*span*.5+8));
      if(Math.hypot(dx,dy)<=limit){
        const fraction=Math.max(0,Math.min(1,(time-a.timestamp)/span));
        point.x+=dx*fraction;point.y+=dy*fraction;
      }
    }
    // Rapid reversal: the real next origin can lag the constant-speed prediction
    // even though it lies on this route. Ashe at 9.278561/9.411561 in 5640962900
    // exposes 95/69-unit backward snaps. Only reconcile small, short, on-route
    // observations followed by an opposing command. This interpolates observed
    // progress; it does NOT infer a turn delay, change speed data, or decode a dash.
    if(a.path.length>1&&b.path&&b.path.length>1&&(a.speed??0)>0&&span>0&&span<=.25){
      const target=projectOntoRoute(a,b),end=routePosition(a,span);
      if(target.error<=16&&target.distance>0&&target.distance<target.total&&
         target.distance<(a.speed??0)*span&&Math.hypot(end.x-b.x,end.y-b.y)<=100){
        const behind=routePositionAtDistance(a,Math.max(0,target.distance-8));
        const nx=b.path[1].x-b.path[0].x,ny=b.path[1].y-b.path[0].y;
        if((target.x-behind.x)*nx+(target.y-behind.y)*ny<0){
          const fraction=Math.max(0,Math.min(1,(time-a.timestamp)/span));
          point=routePositionAtDistance(a,target.distance*fraction);
          point.x+=(b.x-target.x)*fraction;point.y+=(b.y-target.y)*fraction;
        }
      }
    }
    return {x:point.x,y:point.y,previous:a.timestamp,next:b.timestamp};
  }
  // Do not glide across recalls/respawns or long missing intervals. These are
  // display heuristics, not claims of decoded death or teleport events.
  const hold = a.speed === 0 || b.timestamp-a.timestamp > 10 || Math.hypot(b.x-a.x, b.y-a.y) > 2000;
  return { ...(hold ? {x:a.x,y:a.y} : interpolatePosition(a,b,time)), previous:a.timestamp, next:b.timestamp };
}
export function formatTime(time: number) { const seconds = Math.max(0, Math.floor(time)); return `${Math.floor(seconds/60).toString().padStart(2,'0')}:${(seconds%60).toString().padStart(2,'0')}`; }
