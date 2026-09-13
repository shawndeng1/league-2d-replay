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
export function samplePosition(samples: readonly PositionSample[], time: number) {
  const index = findFrameAtTime(samples, time);
  if (index < 0) return null;
  const a = samples[index], b = samples[Math.min(index+1, samples.length-1)];
  if (a.path?.length) {
    // Follow the recorded route at its recorded speed until the next update.
    // A long packet gap means no new command, not necessarily no movement.
    // Exhausted routes stay at their endpoint; never extrapolate beyond it.
    let distance = Math.max(0, time-a.timestamp) * Math.max(0, a.speed ?? 0);
    let point = a.path[0];
    for (let waypoint = 1; waypoint < a.path.length; waypoint++) {
      const next = a.path[waypoint];
      const length = Math.hypot(next.x-point.x, next.y-point.y);
      if (length > 0 && distance < length) {
        const fraction = distance/length;
        return {x:point.x+(next.x-point.x)*fraction,y:point.y+(next.y-point.y)*fraction,previous:a.timestamp,next:b.timestamp};
      }
      distance -= length;
      point = next;
    }
    return {x:point.x,y:point.y,previous:a.timestamp,next:b.timestamp};
  }
  // Do not glide across recalls/respawns or long missing intervals. These are
  // display heuristics, not claims of decoded death or teleport events.
  const hold = a.speed === 0 || b.timestamp-a.timestamp > 10 || Math.hypot(b.x-a.x, b.y-a.y) > 2000;
  return { ...(hold ? {x:a.x,y:a.y} : interpolatePosition(a,b,time)), previous:a.timestamp, next:b.timestamp };
}
export function formatTime(time: number) { const seconds = Math.max(0, Math.floor(time)); return `${Math.floor(seconds/60).toString().padStart(2,'0')}:${(seconds%60).toString().padStart(2,'0')}`; }
