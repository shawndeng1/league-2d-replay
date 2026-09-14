import {describe,it,expect} from 'vitest';
import {auditMovement,classifyHold} from './movementAudit';
import {samplePosition} from './math';
import type {Replay,PositionSample,GameEvent} from '../../shared/replay';
import unresolved from './movement-audit.fixture.json';
import corrected from './long-route-gaps.fixture.json';
import teamSpawn from './team-spawn.fixture.json';
import {compareSupplementalPositions} from './movementComparison';
function replay(samples:PositionSample[],events:GameEvent[]=[]):Replay{
  return {metadata:{sourceSha256:'fixture',patch:'test',decoder:'test',eventCoverage:{respawns:true}},
    players:[{id:0,championName:'Test'}],tracks:[{playerId:0,samples}],events} as Replay;
}
describe('offline movement audit',()=>{
  it('uses actual teammate respawns when no personal spawn was recorded',()=>{
    expect(teamSpawn.cases).toHaveLength(5);
    for(const c of teamSpawn.cases){
      const input={...replay(c.samples),players:[teamSpawn.player,teamSpawn.teammate],
        tracks:[{playerId:1,samples:c.samples}],events:[teamSpawn.respawn]} as Replay;
      const candidate=auditMovement(input).candidates[0];
      expect(candidate.holdContext).toBe('ARRIVES_AT_OBSERVED_SPAWN');
      expect(candidate.spawnEvidence).toBe('TEAM_RESPAWNS');
      const opponent={...input,players:[teamSpawn.player,{...teamSpawn.teammate,team:'RED'}]} as Replay;
      expect(auditMovement(opponent).candidates[0].holdContext).toBe('UNEXPLAINED_RELOCATION');
      const uncovered={...input,metadata:{...input.metadata,eventCoverage:{...input.metadata.eventCoverage!,respawns:false}}};
      expect(auditMovement(uncovered).candidates[0].spawnEvidence).toBe('NONE');
    }
  });
  it('counts a position-only hold even without a speed or route',()=>{
    const samples=[{timestamp:0,x:100,y:100,positionOnly:true},{timestamp:3,x:300,y:100}];
    const candidate=auditMovement(replay(samples)).candidates[0];
    expect(candidate.predictedHoldSeconds).toBe(3);
    expect(candidate.classification).toBe('HOLD_THEN_RELOCATION');
  });
  it('reports an earlier real observation without claiming the jump disappeared',()=>{
    const input=replay([{timestamp:0,x:0,y:0,speed:0},
      {timestamp:2,x:500,y:500,positionOnly:true},
      {timestamp:4,x:504,y:502}]);
    const original=JSON.stringify(input),report=compareSupplementalPositions(input);
    expect(report.before).toBe(1);expect(report.after).toBe(1);
    expect(report.added.map(c=>c.timestamp)).toEqual([2]);
    expect(report.removed.map(c=>c.timestamp)).toEqual([4]);
    expect(report.supplementalSamples).toBe(1);
    expect(JSON.stringify(input)).toBe(original);
    expect(compareSupplementalPositions(replay(input.tracks[0].samples.filter(s=>!s.positionOnly))).added).toEqual([]);
  });
  it('separates spawn proximity from unverified relocation semantics',()=>{
    const spawn={x:394,y:462},field={x:8000,y:8000};
    expect(classifyHold(field,spawn,10000,[spawn])).toBe('ARRIVES_AT_OBSERVED_SPAWN');
    expect(classifyHold(spawn,field,10000,[spawn])).toBe('LEAVES_OBSERVED_SPAWN');
    expect(classifyHold(field,spawn,10000,[])).toBe('UNEXPLAINED_RELOCATION');
    expect(classifyHold(spawn,{x:420,y:470},28,[spawn])).toBe('SMALL_CORRECTION_AFTER_HOLD');
    expect(classifyHold(field,{x:8100,y:8600},610,[spawn])).toBe('UNEXPLAINED_RELOCATION');
  });
  it('includes the hold in review links without seeking arbitrarily far back',()=>{
    const a={timestamp:20,x:0,y:0,speed:0};
    const b={timestamp:24,x:900,y:0};
    expect(auditMovement(replay([a,b])).candidates[0].url).toContain('?t=20.000');
    expect(auditMovement(replay([a,{...b,timestamp:100}])).candidates[0].url).toContain('?t=85.000');
  });
  it('does not flag the corrected actual Yi/Ashe routes',()=>{
    for(const c of corrected.cases)expect(auditMovement(replay(c.samples)).flagged,c.champion).toBe(0);
  });
  it('retains suspicious real boundaries from all five replays for review',()=>{
    expect(new Set(unresolved.cases.map(c=>c.replayId)).size).toBe(5);
    for(const c of unresolved.cases){
      const original=JSON.stringify(c.samples),r=auditMovement(replay(c.samples)),[a,b]=c.samples;
      expect(r.candidates.length,c.champion).toBe(1);
      expect(r.candidates[0].classification).toBe(c.kind);
      expect(r.candidates[0].url).toContain('&player=0');
      for(const t of [b.timestamp,a.timestamp,(a.timestamp+b.timestamp)/2]){
        const p=samplePosition(c.samples,t)!;
        expect(Number.isFinite(p.x)&&Number.isFinite(p.y)).toBe(true);
      }
      expect(samplePosition(c.samples,b.timestamp)).toMatchObject({x:b.x,y:b.y});
      expect(JSON.stringify(c.samples)).toBe(original);
    }
  });
  it('separates corrections hidden by verified death state',()=>{
    const source={opcode:'test',packetSize:0,rawTimestamp:0,confidence:'VERIFIED' as const};
    const samples=[{timestamp:0,x:0,y:0,speed:0},{timestamp:4,x:5000,y:5000}];
    const events:GameEvent[]=[{id:'death',timestamp:1,type:'CHAMPION_KILL',victimPlayerId:0,x:0,y:0,source}];
    const r=auditMovement(replay(samples,events));
    expect(r.maskedByLife).toBe(1);expect(r.flagged).toBe(0);
  });
  it('audits coincident updates once and rejects time reversal',()=>{
    const samples=[{timestamp:0,x:0,y:0,speed:0},{timestamp:1,x:50,y:0},{timestamp:1,x:100,y:0}];
    const r=auditMovement(replay(samples));
    expect(r.boundaries).toBe(1);expect(r.duplicates).toBe(1);
    expect(r.candidates[0].jumpWorldUnits).toBe(100);
    expect(()=>auditMovement(replay([...samples].reverse()))).toThrow('Unsorted');
  });
});
