import type {MapEntity} from '../../shared/replay';
import type {EventIconKind} from './eventIcons';

export const mapEntityIcon=(entity:MapEntity)=>entity.kind.toLowerCase() as EventIconKind;
export function mapEntityStateAt(entity:MapEntity,time:number){
  let lo=0,hi=entity.states.length;
  while(lo<hi){const mid=(lo+hi)>>>1;if(entity.states[mid].timestamp<=time)lo=mid+1;else hi=mid;}
  return lo?entity.states[lo-1].state:undefined;
}
export function mapEntityLabel(entity:MapEntity){
  if(entity.kind==='VOID_GRUB')return `Void Grub ${entity.name.split('.').at(-1)}`;
  return [entity.team,entity.lane,entity.tier,entity.kind.replaceAll('_',' ')].filter(Boolean).join(' ');
}
