import {eventIcons,eventIconAsset,type EventIconKind} from './eventIcons';

export function EventIcon({kind}:{kind:EventIconKind}){
  return <span aria-hidden="true" className={`event-symbol ${kind}`}>
    <span className="event-glyph" style={{maskImage:`url("${eventIconAsset(kind)}")`,WebkitMaskImage:`url("${eventIconAsset(kind)}")`}} />
  </span>;
}

export function EventLegend(){
  return <div className="event-legend" aria-label="Event icon legend">{(Object.keys(eventIcons) as EventIconKind[]).map(kind=><span key={kind}><EventIcon kind={kind}/>{eventIcons[kind].label}</span>)}</div>;
}
