import type {Replay,PositionSample,WorldPoint} from '../../shared/replay';
import {samplePosition} from './math';
import {indexLifeEvents,playerLifeAt,samplePlayerPosition} from './life';
import {findEventsNearTimestamp} from './events';

const distance=(a:WorldPoint,b:WorldPoint)=>Math.hypot(a.x-b.x,a.y-b.y);
/** Spatial evidence only: does not claim a recall, teleport, or dash opcode. */
export function classifyHold(a:WorldPoint,b:WorldPoint,jump:number,spawns:readonly WorldPoint[]){
  if(jump<=100)return 'SMALL_CORRECTION_AFTER_HOLD';
  const fromSpawn=spawns.some(p=>distance(a,p)<=300),toSpawn=spawns.some(p=>distance(b,p)<=300);
  if(toSpawn&&!fromSpawn)return 'ARRIVES_AT_OBSERVED_SPAWN';
  if(fromSpawn&&!toSpawn)return 'LEAVES_OBSERVED_SPAWN';
  return 'UNEXPLAINED_RELOCATION';
}
/** Offline diagnostics using the SAME interpolation and life overrides as PixiJS.
 * Flags are review candidates, not decoded dashes, recalls, or proven defects.
 */
export function auditMovement(replay:Replay){
  const events=[...replay.events].sort((a,b)=>a.timestamp-b.timestamp);
  const life=indexLifeEvents(replay.metadata.eventCoverage?.respawns?events:[],replay.players.map(p=>p.id));
  const candidates=[];
  let boundaries=0,maskedByLife=0,duplicates=0;
  for(const track of replay.tracks){
    const samples=track.samples,player=replay.players.find(p=>p.id===track.playerId);
    for(let i=0;i<samples.length;i++){
      if(!Number.isFinite(samples[i].timestamp)||i>0&&samples[i].timestamp<samples[i-1].timestamp)
        throw new Error(`Unsorted/nonfinite time for player ${track.playerId}`);
    }
    const playerLife=life.get(track.playerId)??[];
    const personalSpawns=playerLife.flatMap(e=>e.type==='CHAMPION_RESPAWN'?[{x:e.x,y:e.y}]:[]);
    // A player may have no recorded personal respawns. Same-team decoded respawns
    // still provide spatial evidence; never use an opponent's spawn or infer a
    // recall/teleport event. Keep the evidence source explicit in diagnostics.
    const teamIds=new Set(replay.players.filter(p=>player?.team && p.team===player.team).map(p=>p.id));
    const teamSpawns=replay.metadata.eventCoverage?.respawns?events.flatMap(e=>e.type==='CHAMPION_RESPAWN'&&teamIds.has(e.playerId)?[{x:e.x,y:e.y}]:[]):[];
    const spawns=personalSpawns.length?personalSpawns:teamSpawns;
    const spawnEvidence=personalSpawns.length?'PLAYER_RESPAWNS':teamSpawns.length?'TEAM_RESPAWNS':'NONE';
    for(let i=1;i<samples.length;i++){
      // At coincident timestamps the renderer uses the last update. Audit once.
      if(samples[i].timestamp===samples[i-1].timestamp){duplicates++;continue;}
      const a=samples[i-1];let end=i;
      while(end+1<samples.length&&samples[end+1].timestamp===samples[i].timestamp)end++;
      const b=samples[end],span=b.timestamp-a.timestamp;
      const epsilon=Math.min(1e-6,span/4),beforeTime=b.timestamp-epsilon;
      const before=samplePosition(samples,beforeTime)!,after=samplePosition(samples,b.timestamp)!;
      const visibleBefore=samplePlayerPosition(samples,beforeTime,playerLife)!;
      const visibleAfter=samplePlayerPosition(samples,b.timestamp,playerLife)!;
      const jump=distance(visibleBefore,visibleAfter),rawJump=distance(before,after);
      boundaries++;
      if(rawJump>=30&&jump<30)maskedByLife++;
      const earlier=samplePlayerPosition(samples,Math.max(a.timestamp,b.timestamp-.05),playerLife)!;
      const dx=visibleBefore.x-earlier.x,dy=visibleBefore.y-earlier.y;
      const backwards=jump>=30&&Math.hypot(dx,dy)>1e-3&&dx*(visibleAfter.x-visibleBefore.x)+dy*(visibleAfter.y-visibleBefore.y)<0;
      let routeLength=0;
      for(let k=1;k<(a.path?.length??0);k++)routeLength+=distance(a.path![k-1],a.path![k]);
      const holdSeconds=a.positionOnly ? span : a.path?.length ? Math.max(0,span-((a.speed??0)>0?routeLength/a.speed!:0)) : a.speed===0||span>10||distance(a,b)>2000?span:0;
      const lifeRelated=playerLife.some(e=>e.timestamp>=a.timestamp&&e.timestamp<=b.timestamp)||playerLifeAt(playerLife,beforeTime).dead;
      if(jump<30)continue;
      candidates.push({playerId:track.playerId,champion:player?.championName??String(track.playerId),timestamp:b.timestamp,
        gapSeconds:span,jumpWorldUnits:jump,rawJumpWorldUnits:rawJump,backwards,
        predictedHoldSeconds:holdSeconds,lifeRelated,spawnEvidence,
        holdContext:holdSeconds>=2?classifyHold(visibleBefore,visibleAfter,jump,spawns):undefined,
        classification:lifeRelated?'LIFE_TRANSITION':holdSeconds>=2?'HOLD_THEN_RELOCATION':backwards?'BACKWARD_CORRECTION':'POSITION_CORRECTION',
        url:`/replay/${replay.metadata.sourceSha256}?t=${Math.max(0,holdSeconds>=2?Math.max(a.timestamp,b.timestamp-15):b.timestamp-3).toFixed(3)}&player=${track.playerId}`,
        nearbyEvents:findEventsNearTimestamp(events,b.timestamp+2,4).map(e=>({id:e.id,type:e.type,timestamp:e.timestamp})),
        samples:[a,b] as PositionSample[]});
    }
  }
  candidates.sort((a,b)=>b.jumpWorldUnits-a.jumpWorldUnits||a.timestamp-b.timestamp||a.playerId-b.playerId);
  return {replayId:replay.metadata.sourceSha256,patch:replay.metadata.patch,decoder:replay.metadata.decoder,
    boundaries,duplicates,maskedByLife,flagged:candidates.length,
    nonLifeCandidates:candidates.filter(c=>!c.lifeRelated).length,candidates};
}
