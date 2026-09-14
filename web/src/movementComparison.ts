import type {Replay} from '../../shared/replay';
import {auditMovement} from './movementAudit';

/** Run both populations through the current renderer. Historical reports may
 * use different interpolation rules and are not a controlled comparison. */
export function compareSupplementalPositions(replay:Replay){
  const baseline={...replay,tracks:replay.tracks.map(t=>({...t,samples:t.samples.filter(s=>!s.positionOnly)}))};
  const before=auditMovement(baseline),after=auditMovement(replay);
  const key=(c:typeof before.candidates[number])=>`${c.playerId}:${c.timestamp}`;
  const original=new Map(before.candidates.filter(c=>!c.lifeRelated).map(c=>[key(c),c]));
  const updated=new Map(after.candidates.filter(c=>!c.lifeRelated).map(c=>[key(c),c]));
  const compact=(c:typeof before.candidates[number])=>({playerId:c.playerId,champion:c.champion,
    timestamp:c.timestamp,jumpWorldUnits:c.jumpWorldUnits,holdSeconds:c.predictedHoldSeconds,classification:c.classification,url:c.url});
  return {replayId:after.replayId,before:before.nonLifeCandidates,after:after.nonLifeCandidates,
    supplementalSamples:replay.tracks.reduce((n,t)=>n+t.samples.filter(s=>s.positionOnly).length,0),
    added:[...updated].filter(([k])=>!original.has(k)).map(([,c])=>compact(c)),
    removed:[...original].filter(([k])=>!updated.has(k)).map(([,c])=>compact(c)),
    changed:[...updated].flatMap(([k,c])=>{const previous=original.get(k);
      return previous&&(Math.abs(previous.jumpWorldUnits-c.jumpWorldUnits)>.01||Math.abs(previous.predictedHoldSeconds-c.predictedHoldSeconds)>.001)
        ?[{before:compact(previous),after:compact(c)}]:[];}),
    note:'Added flags can be earlier observations of an unresolved relocation, not new defects. Removed flags do not prove a decoded trajectory.'};
}
