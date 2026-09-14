import {createServer} from 'vite';
import {readFile,readdir,mkdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const input=resolve(process.argv[2]??'../samples/local/replays');
const output=resolve(process.argv[3]??'../samples/local/movement-audit');
const server=await createServer({configFile:false,server:{middlewareMode:true,watch:null},appType:'custom'});
try{
  const {auditMovement}=await server.ssrLoadModule('/src/movementAudit.ts');
  const {compareSupplementalPositions}=await server.ssrLoadModule('/src/movementComparison.ts');
  const reports=[],comparisons=[];
  for(const file of (await readdir(input)).filter(f=>f.endsWith('.json')).sort()){
    const replay=JSON.parse(await readFile(resolve(input,file),'utf8'));
    if(!Array.isArray(replay.tracks))continue;
    reports.push(auditMovement(replay));
    comparisons.push(compareSupplementalPositions(replay));
  }
  if(!reports.length)throw new Error(`No normalized replays in ${input}`);
  await mkdir(output,{recursive:true});
  await writeFile(resolve(output,'report.json'),JSON.stringify(reports,null,2));
  await writeFile(resolve(output,'supplemental-comparison.json'),JSON.stringify(comparisons,null,2));
  const lines=['# Movement review candidates','','These are interpolation discontinuities, not confirmed game/protocol defects. Life-related transitions are separated. Distances are world units.',''];
  for(const r of reports){
    lines.push(`## ${r.replayId}`,`Patch ${r.patch}; ${r.boundaries} boundaries; ${r.flagged} flags; ${r.nonLifeCandidates} outside known life transitions; ${r.maskedByLife} masked by life state.`,'', '| Champion | Time | Jump | Gap | Classification | Review |','| --- | ---: | ---: | ---: | --- | --- |');
    // Include each class so large recall-like relocations cannot bury jitter.
    for(const kind of ['BACKWARD_CORRECTION','POSITION_CORRECTION','HOLD_THEN_RELOCATION'])
      for(const c of r.candidates.filter(c=>!c.lifeRelated&&c.classification===kind).slice(0,10))lines.push(`| ${c.champion} | ${c.timestamp.toFixed(3)} | ${c.jumpWorldUnits.toFixed(1)} | ${c.gapSeconds.toFixed(3)} | ${c.classification} | [Open](http://127.0.0.1:5173${c.url}) |`);
    lines.push('');
    const holds=r.candidates.filter(c=>!c.lifeRelated&&c.classification==='HOLD_THEN_RELOCATION');
    const categories=['SMALL_CORRECTION_AFTER_HOLD','ARRIVES_AT_OBSERVED_SPAWN','LEAVES_OBSERVED_SPAWN','UNEXPLAINED_RELOCATION'];
    lines.push('### Hold context','', 'Spawn labels mean proximity to this player’s actual decoded respawn positions (300 world units), not verified recall/teleport events. Small corrections are at most 100 units. Links include up to 15 seconds of the hold.','');
    for(const category of categories)lines.push(`- ${category}: ${holds.filter(c=>c.holdContext===category).length}`);
    lines.push('', '| Champion | Time | Hold seconds | Jump | Unexplained hold review |','| --- | ---: | ---: | ---: | --- |');
    for(const c of holds.filter(c=>c.holdContext==='UNEXPLAINED_RELOCATION').sort((a,b)=>b.predictedHoldSeconds-a.predictedHoldSeconds).slice(0,20))
      lines.push(`| ${c.champion} | ${c.timestamp.toFixed(3)} | ${c.predictedHoldSeconds.toFixed(2)} | ${c.jumpWorldUnits.toFixed(1)} | [Open](http://127.0.0.1:5173${c.url}) |`);
    lines.push('');
    console.log(`${r.replayId.slice(0,12)}: ${r.boundaries} boundaries, ${r.nonLifeCandidates} non-life candidates`);
  }
  await writeFile(resolve(output,'report.md'),lines.join('\n'));
  console.log(`Report: ${output}`);
}finally{await server.close();}
