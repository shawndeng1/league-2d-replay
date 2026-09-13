import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { GameEvent, Replay } from '../../shared/replay';
import { championAsset, championDisplayName } from './assets';
import { formatTime } from './math';
import { ReplayMap, type Playback } from './ReplayMap';
import {EventFeed,ReplayTimeline} from './EventReview';
import {PlayerInspector} from './PlayerInspector';
import {getEventReviewStart,indexEvents} from './events';
import {parseReplayUrlState,serializeReplayUrlState} from './urlState';
import './review.css';
import {indexLifeEvents} from './life';

async function responseJson(response: Response) {
  const body = await response.json();
  if(!response.ok) throw new Error(typeof body.detail==='string' ? body.detail : body.detail?.message ?? 'The replay could not be loaded.');
  return body;
}

export function App() {
  const [replay,setReplay]=useState<Replay|null>(null);
  const [name,setName]=useState('No replay loaded');
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  const [time,setTime]=useState(0),[playing,setPlaying]=useState(false),[speed,setSpeed]=useState(1);
  const [selected,setSelected]=useState<number|null>(null),[debug,setDebug]=useState(false);
  const [selectedEvent,setSelectedEvent]=useState<string|null>(null);
  const [follow,setFollow]=useState(false),[trail,setTrail]=useState(false),[trailSeconds,setTrailSeconds]=useState(30);
  const fileInput=useRef<HTMLInputElement>(null);
  const clock=useRef<Playback>({time:0,playing:false,speed:1,selected:null,debug:false,follow:false,trail:false,trailSeconds:30});
  const eventIndex=useMemo(()=>indexEvents(replay?.events??[],replay?.players??[]),[replay]);
  const lifeIndex=useMemo(()=>indexLifeEvents(replay?.metadata.eventCoverage?.respawns?replay.events:[],replay?.players.map(p=>p.id)??[]),[replay]);
  const selectedPlayer=replay?.players.find(p=>p.id===selected);
  const writeUrl=useCallback((t:number,player:number|null,event?:string)=>{if(replay)history.replaceState(null,'',serializeReplayUrlState({replayId:replay.metadata.sourceSha256,time:t,...(player!==null?{player}:{}),...(event?{event}:{})}));},[replay]);
  const onTime=useCallback((t:number,p:boolean)=>{setTime(t);setPlaying(p);},[]);
  const seek=useCallback((t:number)=>{clock.current.time=Math.max(0,Math.min(replay?.metadata.duration??0,t));setTime(clock.current.time);setSelectedEvent(null);writeUrl(clock.current.time,clock.current.selected);},[replay,writeUrl]);
  const review=useCallback((event:GameEvent)=>{seek(getEventReviewStart(event));setSelectedEvent(event.id);writeUrl(clock.current.time,clock.current.selected,event.id);},[seek,writeUrl]);
  const select=useCallback((playerId:number)=>{const id=clock.current.selected===playerId?null:playerId;setSelected(id);clock.current.selected=id;writeUrl(clock.current.time,id);},[writeUrl]);
  const installReplay=useCallback((data:Replay,filename:string,fromUrl=false)=>{
    if(data.schemaVersion!==1||data.players.length!==10||data.tracks.length!==10)throw new Error('The API returned an unsupported replay model.');
    const state=fromUrl?parseReplayUrlState(location.href):{time:0,player:undefined,event:undefined};
    const event=data.events.find(e=>e.id===state.event);
    const t=Math.min(data.metadata.duration,event?getEventReviewStart(event):state.time);
    const id=data.players.some(p=>p.id===state.player)?state.player!:null;
    clock.current={...clock.current,time:t,playing:false,selected:id};setTime(t);setPlaying(false);setSelected(id);setSelectedEvent(event?.id??null);setReplay(data);setName(filename);
    history.replaceState(null,'',serializeReplayUrlState({replayId:data.metadata.sourceSha256,time:t,...(id!==null?{player:id}:{}),...(event?{event:event.id}:{})}));
  },[]);
  useEffect(()=>{
    let request:AbortController|undefined;
    async function load(){const state=parseReplayUrlState(location.href);request?.abort();if(!state.replayId)return;request=new AbortController();const signal=request.signal;setBusy(true);setError('');clock.current.playing=false;setPlaying(false);
      try{const data:Replay=await responseJson(await fetch(`/api/replays/${state.replayId}/data`,{signal}));if(!signal.aborted)installReplay(data,`Replay ${state.replayId.slice(0,12)}`,true);}
      catch(reason){if(!signal.aborted)setError(reason instanceof Error?reason.message:'Replay link could not be loaded.');}
      finally{if(!signal.aborted)setBusy(false);}}
    void load();window.addEventListener('popstate',load);return()=>{request?.abort();window.removeEventListener('popstate',load);};
  },[installReplay]);
  const togglePlay=useCallback(()=>{if(!replay||busy)return;if(clock.current.time>=replay.metadata.duration)clock.current.time=0;clock.current.playing=!clock.current.playing;setPlaying(clock.current.playing);},[replay,busy]);
  useEffect(()=>{function key(e:KeyboardEvent){if(['INPUT','SELECT','BUTTON'].includes((e.target as HTMLElement).tagName))return;if(e.code==='Space'){e.preventDefault();togglePlay();}if(e.code==='ArrowRight'){e.preventDefault();seek(clock.current.time+10);}if(e.code==='ArrowLeft'){e.preventDefault();seek(clock.current.time-10);}}window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key);},[seek,togglePlay]);
  async function upload(file:File|undefined) {
    if(!file||busy)return;
    clock.current.playing=false;setPlaying(false);setBusy(true);setError('');
    try {
      const form=new FormData();form.append('file',file);
      const uploaded=await responseJson(await fetch('/api/replays',{method:'POST',body:form}));
      const data:Replay=await responseJson(await fetch(`/api/replays/${uploaded.id}/data`));
      installReplay(data,file.name);
    }catch(reason){setError(reason instanceof Error?reason.message:'Upload failed. Is the backend running?');}
    finally{setBusy(false);if(fileInput.current)fileInput.current.value='';}
  }
  return <div className="shell">
    <header><a href="/" className="brand"><span className="brand-mark">◈</span> RIFT<span>REPLAY</span><small>EARLY ACCESS</small></a><span className="header-note">A new perspective on your game</span><button className="upload-button" onClick={()=>fileInput.current?.click()} disabled={busy}><span>↥</span> {busy?'Parsing replay…':'Open replay'}</button><input ref={fileInput} hidden type="file" accept=".rofl" aria-label="Select replay file" onChange={e=>void upload(e.target.files?.[0])}/></header>
    <main>
      <div className="page-title"><div className="eyebrow">MATCH REPLAY <span>/</span> SUMMONER’S RIFT</div><div className="title-row"><div><h1>See the whole game.</h1><p>{replay?name:'Load a League replay and follow all ten champions across the map.'}</p></div><div className="patch-badge"><span className="status-dot"/> {replay?'REPLAY READY':'LOCAL REPLAY VIEWER'}<small>{replay?`PATCH ${replay.metadata.patch}`:'SUPPORTS PATCH 16.18'}</small></div></div></div>
      {error&&<div className="notice error" role="alert">{error}</div>}
      {busy&&<div className="notice" role="status"><span className="spinner"/> Reading replay and extracting champion movement. This usually takes a few seconds.</div>}
      <div className="workspace">
        <section className="viewer" aria-label="Replay viewer">
          <div className="viewer-toolbar"><span><span className="status-dot"/> {replay?'MATCH OVERVIEW':'AWAITING REPLAY'}</span><div><span className="view-pill">All players</span><button className={debug?'text-button active':'text-button'} aria-pressed={debug} onClick={()=>{clock.current.debug=!debug;setDebug(!debug);}}>⌗ Debug</button></div></div>
          <ReplayMap replay={replay} clock={clock} onTime={onTime} onSelect={select}/>
          <div className="playback">
            <div className="timeline-labels"><span>{formatTime(time)}</span><small>{replay?'MATCH TIMELINE':'OPEN A .ROFL TO BEGIN'}</small><span>{formatTime(replay?.metadata.duration??0)}</span></div>
            <input className="timeline" type="range" aria-label="Replay timeline" min="0" max={replay?.metadata.duration??1} step="0.05" value={time} disabled={!replay||busy} onChange={e=>seek(Number(e.target.value))} style={{'--progress':`${time/(replay?.metadata.duration||1)*100}%`} as React.CSSProperties}/>
            {replay&&<ReplayTimeline events={eventIndex.sorted} players={replay.players} duration={replay.metadata.duration} selectedEvent={selectedEvent} onReview={review}/>}
            <div className="controls"><div className="transport"><button aria-label="Back 10 seconds" disabled={!replay||busy} onClick={()=>seek(time-10)}>↶ <small>10</small></button><button className="play-button" aria-label={playing?'Pause':'Play'} disabled={!replay||busy} onClick={togglePlay}>{playing?'Ⅱ':'▶'}</button><button aria-label="Forward 10 seconds" disabled={!replay||busy} onClick={()=>seek(time+10)}><small>10</small> ↷</button><span className="time-readout">{formatTime(time)} <span>/ {formatTime(replay?.metadata.duration??0)}</span></span></div><label className="speed">Playback speed <select aria-label="Playback speed" value={speed} onChange={e=>{const v=Number(e.target.value);setSpeed(v);clock.current.speed=v;}}>{[0.25,0.5,1,2,4].map(s=><option key={s} value={s}>{s}×</option>)}</select></label></div>
          </div>
        </section>
        <aside>
          {selectedPlayer&&replay&&<PlayerInspector player={selectedPlayer} time={time} events={eventIndex.byPlayer.get(selectedPlayer.id)??[]} lifeEvents={lifeIndex.get(selectedPlayer.id)??[]} lifeVerified={Boolean(replay.metadata.eventCoverage?.respawns)} verified={Boolean(replay.metadata.eventCoverage?.championKills)} follow={follow} trail={trail} trailSeconds={trailSeconds} onFollow={v=>{setFollow(v);clock.current.follow=v;}} onTrail={v=>{setTrail(v);clock.current.trail=v;}} onTrailSeconds={v=>{setTrailSeconds(v);clock.current.trailSeconds=v;}}/>}
          {replay&&<EventFeed events={eventIndex.sorted} players={replay.players} selectedEvent={selectedEvent} onReview={review} player={selected} debug={debug}/>}
          <div className="roster-heading"><h2>On the Rift</h2><span>{replay?'10 PLAYERS':'— PLAYERS'}</span></div>
          {(['BLUE','RED'] as const).map(team=><section className={`team ${team.toLowerCase()}`} key={team}><h3><span/> {team==='BLUE'?'Blue side':'Red side'} <small>{team==='BLUE'?'01 — 05':'06 — 10'}</small></h3>{replay?replay.players.filter(p=>p.team===team).map(p=><button className={`player ${selected===p.id?'selected':''}`} key={p.id} onClick={()=>select(p.id)} aria-pressed={selected===p.id}><img src={championAsset(p)} alt=""/><span><strong>{championDisplayName(p)}</strong><small>{p.role==='UTILITY'?'SUPPORT':p.role==='BOTTOM'?'BOT':p.role==='MIDDLE'?'MID':p.role}</small></span><span className="player-indicator">{selected===p.id?'◎':'·'}</span></button>):<p className="roster-placeholder">The five champions on this side<br/>will appear when you load a replay.</p>}</section>)}
          <div className="match-note"><span>◇</span><div><strong>{replay?'From the actual replay':'Your replay stays here'}</strong><p>{replay?`${replay.diagnostics.sampleCount.toLocaleString()} position samples. Select a champion to highlight their movement.`:'Files are parsed on your local backend. No Riot account or API key needed.'}</p></div></div>
        </aside>
      </div>
      <div className="below-viewer"><span><kbd>SPACE</kbd> play / pause <kbd>←</kbd><kbd>→</kbd> seek 10s</span><span>2D movement preview <span className="divider">/</span> All-player view</span></div>
    </main>
    <footer><span>RIFT REPLAY <small>v0.1</small></span><p>Rift Replay is not endorsed by Riot Games and does not reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games and all associated properties are trademarks or registered trademarks of Riot Games, Inc.</p></footer>
  </div>;
}


