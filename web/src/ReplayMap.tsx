import { useEffect, useRef, useState, type MutableRefObject } from 'react';
import { Application, Assets, Container, Graphics, Sprite, Text } from 'pixi.js';
import type { Replay } from '../../shared/replay';
import { championAsset, championDisplayName, mapAsset } from './assets';
import { worldToMap, formatTime } from './math';
import {indexLifeEvents,playerLifeAt,samplePlayerPosition} from './life';
import {findEventsNearTimestamp} from './events';
import {recentTrail} from './trails';

export interface Playback { time: number; playing: boolean; speed: number; selected: number | null; debug: boolean;follow:boolean;trail:boolean;trailSeconds:number }
interface Props { replay: Replay | null; clock: MutableRefObject<Playback>; onTime: (time: number, playing: boolean) => void;onSelect:(id:number)=>void }

export function ReplayMap({ replay, clock, onTime,onSelect }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const debugText = useRef<HTMLPreElement>(null);
  const callback = useRef(onTime);
  callback.current = onTime;
  const selectionCallback=useRef(onSelect);selectionCallback.current=onSelect;
  const [error, setError] = useState('');
  const [ready, setReady] = useState(false);
  useEffect(() => {
    let disposed = false, initialized = false;
    let observer: ResizeObserver | undefined;
    const app = new Application();
    setError(''); setReady(false);
    async function start() {
      try {
        await app.init({width:800,height:800,backgroundAlpha:0,antialias:true,resolution:Math.min(devicePixelRatio,2),autoDensity:true});
        initialized = true;
        if (disposed) { app.destroy(true,{children:true}); return; }
        host.current!.appendChild(app.canvas);
        app.canvas.setAttribute('aria-label', 'Summoner’s Rift replay map');
        const scene = new Container(); app.stage.addChild(scene);
        const texture = await Assets.load(mapAsset);
        if (disposed) return;
        const map = new Sprite(texture); map.width=800; map.height=800;
        map.alpha = replay ? 0.94 : 0.25; scene.addChild(map);
        const trailGraphic=new Graphics(),eventGraphic=new Graphics();scene.addChild(trailGraphic,eventGraphic);
        const events=[...(replay?.events??[])].sort((a,b)=>a.timestamp-b.timestamp);
        const lifeEvents=indexLifeEvents(replay?.metadata.eventCoverage?.respawns?events:[],replay?.players.map(p=>p.id)??[]);
        const actors = await Promise.all((replay?.players ?? []).map(async player => {
          const node = new Container();
          const color = player.team==='BLUE' ? 0x63caff : 0xff6c87;
          const halo = new Graphics().circle(0,0,22).stroke({width:2,color:0xf1da99});
          halo.visible=false;
          const ring = new Graphics().circle(0,0,17).fill(0x091018).stroke({width:3,color});
          const icon = new Sprite(await Assets.load(championAsset(player)));
          icon.anchor.set(0.5); icon.width=29; icon.height=29;
          const mask = new Graphics().circle(0,0,14.5).fill(0xffffff);
          icon.mask=mask;
          const label = new Text({text:championDisplayName(player),style:{fontFamily:'Arial',fontSize:12,fontWeight:'600',fill:0xffffff,stroke:{color:0x071018,width:4}}});
          label.anchor.set(0.5,0); label.y=23;
          node.addChild(halo,ring,icon,mask,label);
          const deadMark=new Graphics().moveTo(-7,-7).lineTo(7,7).moveTo(-7,7).lineTo(7,-7).stroke({width:3,color:0xffd2d8});deadMark.visible=false;node.addChild(deadMark);
          node.eventMode='static';node.cursor='pointer';node.on('pointertap',()=>selectionCallback.current(player.id));
          return {player,node,halo,label,icon,deadMark,life:lifeEvents.get(player.id)??[],track:replay!.tracks.find(t=>t.playerId===player.id)!};
        }));
        if (disposed) return;
        actors.forEach(a=>scene.addChild(a.node));
        const grid = new Graphics();
        for (let i=0;i<=4;i++) { grid.moveTo(i*200,0).lineTo(i*200,800); grid.moveTo(0,i*200).lineTo(800,i*200); }
        grid.stroke({color:0xffffff,width:1,alpha:0.15});
        // Known planar bounds and midpoint: a calibration overlay, not game entities.
        for(const p of [[400,400],[22,778],[778,22]]) grid.moveTo(p[0]-8,p[1]).lineTo(p[0]+8,p[1]).moveTo(p[0],p[1]-8).lineTo(p[0],p[1]+8);
        grid.stroke({color:0xffdc89,width:2}); grid.visible=false; scene.addChild(grid);
        function resize() { if (!host.current || disposed) return; const size=host.current.clientWidth; app.renderer.resize(size,size); scene.scale.set(size/800); }
        observer=new ResizeObserver(resize); observer.observe(host.current!); resize();
        let lastUpdate=0,lastTrailKey='';
        app.ticker.add(ticker=>{
          const c=clock.current;
          if(c.playing && replay) { c.time=Math.min(replay.metadata.duration,c.time+Math.min(ticker.deltaMS,100)/1000*c.speed); if(c.time>=replay.metadata.duration) c.playing=false; }
          const lines=[`GAME ${formatTime(c.time)}  ·  ${ticker.FPS.toFixed(0)} FPS`, `PATCH ${replay?.metadata.patch ?? '—'}`, 'CHAMPION        WORLD X/Y       MAP X/Y       PREV → NEXT'];
          actors.forEach(actor=>{
            const pos=samplePlayerPosition(actor.track.samples,c.time,actor.life); if(!pos)return;
            const life=playerLifeAt(actor.life,c.time);actor.deadMark.visible=life.dead;actor.icon.tint=life.dead?0x7b858d:0xffffff;
            const mapPos=worldToMap(pos.x,pos.y,800,800,replay!.metadata.worldBounds);
            actor.node.position.set(mapPos.x,mapPos.y);
            actor.halo.visible=c.selected===actor.player.id;
            actor.halo.scale.set(c.follow?1.2:1);
            actor.label.visible=c.selected===actor.player.id || c.debug;
            actor.node.alpha=c.selected===null || c.selected===actor.player.id ? 1 : c.follow?0.35:0.6;
            if(c.debug) lines.push(`${actor.player.championName.padEnd(15)} ${pos.x.toFixed(0).padStart(5)},${pos.y.toFixed(0).padStart(5)}  ${mapPos.x.toFixed(0).padStart(4)},${mapPos.y.toFixed(0).padStart(4)}  ${pos.previous.toFixed(2)} → ${pos.next.toFixed(2)}`);
          });
          grid.visible=c.debug;
          const trailKey=`${c.selected}:${c.trail}:${c.trailSeconds}:${Math.floor(c.time*10)}`;
          if(trailKey!==lastTrailKey){lastTrailKey=trailKey;trailGraphic.clear();const actor=actors.find(a=>a.player.id===c.selected);
            if(c.trail&&actor){const points=recentTrail(actor.track.samples,c.time,c.trailSeconds,actor.life);for(let i=1;i<points.length;i++){if(points[i].breakBefore)continue;const a=worldToMap(points[i-1].x,points[i-1].y,800,800,replay!.metadata.worldBounds),b=worldToMap(points[i].x,points[i].y,800,800,replay!.metadata.worldBounds);trailGraphic.moveTo(a.x,a.y).lineTo(b.x,b.y).stroke({color:actor.player.team==='BLUE'?0x63caff:0xff6c87,width:3,alpha:.15+.65*(1-points[i].age)});}}
          }
          eventGraphic.clear();
          for(const event of findEventsNearTimestamp(events,c.time,2.5)){if(event.x===undefined||event.y===undefined)continue;const p=worldToMap(event.x,event.y,800,800,replay!.metadata.worldBounds),age=c.time-event.timestamp;eventGraphic.circle(p.x,p.y,20+age*8).stroke({color:event.type==='CHAMPION_KILL'?0xffa1a1:0xf1da99,width:2,alpha:Math.max(0,.7*(1-age/2.5))});}
          if(performance.now()-lastUpdate>100) { callback.current(c.time,c.playing); lastUpdate=performance.now(); if(debugText.current && c.debug) debugText.current.textContent=lines.join('\n'); }
        });
        setReady(true);
      } catch (reason) { if(!disposed) setError(`Map renderer could not load: ${String(reason)}`); }
    }
    void start();
    return ()=>{disposed=true;observer?.disconnect();if(initialized)app.destroy(true,{children:true});};
  },[replay,clock]);
  return <><div className="map-host" ref={host}>
    {!ready&&!error&&<div className="map-message">Loading Summoner’s Rift…</div>}
    {error&&<div className="map-message error" role="alert">{error}</div>}
    {!replay&&ready&&<div className="map-message empty-map"><span className="map-symbol">◇</span><strong>Your match, from above.</strong><p>Open a replay to see every rotation,<br/>roam, and route across the Rift.</p></div>}
    <span className="map-corner top-left">SUMMONER’S RIFT</span>
    <span className="map-corner bottom-right">ALL PLAYERS · 2D</span>
  </div><pre className="debug-panel" ref={debugText} hidden={!clock.current.debug} aria-label="Developer overlay" /></>;
}

