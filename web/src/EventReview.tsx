import {memo,useMemo,useState} from 'react';
import type {GameEvent,Player} from '../../shared/replay';
import {eventDetails,eventLabel,filterEvents,type EventFilter} from './events';
import {EventIcon,EventLegend} from './EventIcon';
import {eventIconKind} from './eventIcons';
import {formatTime} from './math';

function EventSymbol({event}:{event:GameEvent}){return <EventIcon kind={eventIconKind(event)}/>;}
interface Props {events:GameEvent[];players:Player[];selectedEvent:string|null;onReview:(event:GameEvent)=>void}
export const ReplayTimeline=memo(function ReplayTimeline({events,players,selectedEvent,onReview,duration}:Props&{duration:number}){
  const [showRespawns,setShowRespawns]=useState(false);
  const markers=useMemo(()=>events.filter(e=>e.type!=='CHAMPION_RESPAWN'||showRespawns||e.id===selectedEvent),[events,showRespawns,selectedEvent]);
  return <><label className="timeline-options"><input type="checkbox" checked={showRespawns} onChange={e=>setShowRespawns(e.target.checked)}/> Respawn markers</label><div className="event-markers" aria-label="Game event timeline">{markers.map((event,index)=><button key={event.id} className={`event-marker ${event.timestamp/duration<.15?'near-start':event.timestamp/duration>.85?'near-end':''} ${selectedEvent===event.id?'chosen':''}`} style={{left:`${event.timestamp/duration*100}%`,top:`${index%3*18}px`}} aria-label={`${formatTime(event.timestamp)} ${eventLabel(event,players)}`} onClick={()=>onReview(event)}>
    <EventSymbol event={event}/><span role="tooltip" className="event-tooltip">{formatTime(event.timestamp)}{'\n'}{eventDetails(event,players)}</span>
  </button>)}</div><EventLegend/></>;
});
export const EventFeed=memo(function EventFeed({events,players,selectedEvent,onReview,player,debug}:Props&{player:number|null;debug:boolean}){
  const [filter,setFilter]=useState<EventFilter>('All'),[onlyPlayer,setOnlyPlayer]=useState(false);
  const visible=useMemo(()=>filterEvents(events,filter,onlyPlayer?player:null),[events,filter,onlyPlayer,player]);
  const selected=events.find(e=>e.id===selectedEvent);
  return <details className="review-panel" open><summary>Events <small>{visible.length}</small></summary>
    <div className="event-filters">{(['All','Kills','Respawns','Objectives','Structures'] as const).map(value=><button key={value} aria-pressed={filter===value} onClick={()=>setFilter(value)}>{value}</button>)}</div>
    {player!==null&&<label className="review-toggle"><input type="checkbox" checked={onlyPlayer} onChange={e=>setOnlyPlayer(e.target.checked)}/> Selected player only</label>}
    <p className="support-note">Void Grubs: individual kills and observed map entities are available with decoder v7. Showing decoded events only. Tower locations and lanes are available after re-upload. Assists and inhibitor locations remain undecoded.</p>
    <div className="event-feed">{visible.map(event=><button key={event.id} className={selectedEvent===event.id?'chosen':''} title={eventDetails(event,players)} onClick={()=>onReview(event)}><time>{formatTime(event.timestamp)}</time><EventSymbol event={event}/><span>{eventLabel(event,players)}</span></button>)}{!visible.length&&<p>No decoded events in this view.</p>}</div>
    {debug&&selected&&<pre className="event-debug" aria-label="Event source details">{JSON.stringify(selected,null,2)}{'\n'}Coordinates: {selected.x===undefined?'unavailable':`${selected.x}, ${selected.y}`}</pre>}
  </details>;
});
