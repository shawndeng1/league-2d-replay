import type {GameEvent,Player} from '../../shared/replay';
import {currentScore} from './events';
import {formatTime} from './math';
import {playerLifeAt} from './life';
interface Props {player:Player;time:number;events:GameEvent[];lifeEvents:GameEvent[];lifeVerified:boolean;verified:boolean;follow:boolean;trail:boolean;trailSeconds:number;onFollow:(v:boolean)=>void;onTrail:(v:boolean)=>void;onTrailSeconds:(v:number)=>void}
export function PlayerInspector({player,time,events,lifeEvents,lifeVerified,verified,follow,trail,trailSeconds,onFollow,onTrail,onTrailSeconds}:Props){
  const score=currentScore(events,time,player.id),final=player.finalStats;
  const life=playerLifeAt(lifeEvents,time);
  return <section className="review-panel player-inspector" aria-label="Player inspector"><h2>{player.championName}</h2>{player.displayName&&<p>{player.displayName}</p>}<p className={player.team.toLowerCase()}>{player.team} · {player.role}</p>
    <h3>Current replay state — {formatTime(time)}</h3><p className="score">{verified?`${score.kills} kills / ${score.deaths} deaths`:'Re-upload this replay to decode kills and deaths.'}</p><small>Current assists, HP, level, gold and items are not decoded.</small>
    {lifeVerified?<p className={`life-state ${life.dead?'dead':'alive'}`} aria-label="Player life state">{life.dead?life.respawnAt!==undefined?`Dead · respawns in ${Math.max(0,Math.ceil(life.respawnAt-time))}s`:'Dead · no respawn before match end':'Alive'}</p>:<p className="support-note">Re-upload this replay to decode dead/alive state.</p>}
    {final&&<><h3>Final match stats</h3><p className="score">{final.kills??'—'} / {final.deaths??'—'} / {final.assists??'—'} <small>K / D / A</small></p><p>{final.level!==undefined&&`Level ${final.level} · `}{final.totalGold!==undefined&&`${final.totalGold.toLocaleString()} total gold`}</p>{final.minionKills!==undefined&&<p>{final.minionKills+(final.neutralMinionKills??0)} CS</p>}</>}
    <button aria-pressed={follow} onClick={()=>onFollow(!follow)}>Follow{follow?' on':''}</button><small className="support-note">Full-map view: Follow strengthens the highlight.</small>
    <label className="review-toggle"><input type="checkbox" checked={trail} onChange={e=>onTrail(e.target.checked)}/> Show trail</label><label>Trail length <select value={trailSeconds} onChange={e=>onTrailSeconds(Number(e.target.value))}>{[30,60,120].map(s=><option key={s} value={s}>{s}s</option>)}</select></label>
  </section>;
}
