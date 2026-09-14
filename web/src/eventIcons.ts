import type {GameEvent} from '../../shared/replay';
import {eventCategory} from './events';

/** Original local vector artwork shared by React controls and Pixi sprites. */
export const eventIcons={
  kill:{label:'Kill',color:0xf7a6ad},
  respawn:{label:'Respawn',color:0x86dbce},
  dragon:{label:'Dragon',color:0xa8e5b3},
  rift_herald:{label:'Herald',color:0xd1a2fc},
  void_grub:{label:'Void Grub',color:0xd7a0f6},
  baron:{label:'Baron',color:0xaf92ff},
  tower:{label:'Tower',color:0xe8d49b},
  inhibitor:{label:'Inhibitor',color:0x7ee3ee},
} as const;
export type EventIconKind=keyof typeof eventIcons;
export const eventIconAsset=(kind:EventIconKind)=>`/assets/events/${kind}.svg`;
export const eventIconKind=(event:GameEvent)=>eventCategory(event) as EventIconKind;

// Measured centers on the bundled 512×512 schematic map11.png. These are
// image annotations, NOT decoded world positions or monster presence/spawns.
const pits={VOID_GRUB:{x:170/512,y:148/512},DRAGON:{x:343/512,y:360/512},BARON:{x:170/512,y:148/512},RIFT_HERALD:{x:170/512,y:148/512}};
export function objectiveMapAnchor(event:GameEvent,width:number,height:number){
  if(event.type!=='OBJECTIVE_KILL')return undefined;
  const pit=pits[event.objective];
  return {x:pit.x*width,y:pit.y*height};
}
