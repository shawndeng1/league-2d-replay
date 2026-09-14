import {Assets,Container,Graphics,Sprite,Text} from 'pixi.js';
import type {MapEntity,WorldBounds} from '../../shared/replay';
import {eventIconAsset,eventIcons} from './eventIcons';
import {mapEntityIcon,mapEntityStateAt,mapEntityLabel} from './mapEntities';
import {worldToMap} from './math';

/** Fixed scene objects; seeking evaluates normalized transitions, never timers. */
export async function createMapEntitiesLayer(entities:MapEntity[],bounds:WorldBounds){
  const layer=new Container();
  const actors=await Promise.all(entities.map(async entity=>{
    const node=new Container(),kind=mapEntityIcon(entity);
    const color=entity.team==='BLUE'?0x63caff:entity.team==='RED'?0xff6c87:eventIcons[kind].color;
    const background=new Graphics().circle(0,0,13).fill({color:0x09131d,alpha:.9}).stroke({color,width:1.5});
    const sprite=new Sprite(await Assets.load(eventIconAsset(kind)));sprite.anchor.set(.5);sprite.width=19;sprite.height=19;sprite.tint=color;
    const cross=new Graphics().moveTo(-9,9).lineTo(9,-9).stroke({color:0x9eabb9,width:2});
    const label=new Text({text:mapEntityLabel(entity),style:{fontFamily:'Arial',fontSize:11,fill:0xffffff,stroke:{color:0x09131d,width:4}}});
    label.anchor.set(.5,1);label.y=-17;label.visible=false;
    node.addChild(background,sprite,cross,label);const p=worldToMap(entity.x,entity.y,800,800,bounds);node.position.set(p.x,p.y);
    node.eventMode='static';node.on('pointerover',()=>{label.visible=true;});node.on('pointerout',()=>{label.visible=false;});
    node.visible=false;layer.addChild(node);return {entity,node,cross,label};
  }));
  return {layer,update(time:number,visible:boolean){
    layer.visible=visible;
    for(const {entity,node,cross,label} of actors){
      const state=mapEntityStateAt(entity,time);
      const structure=entity.kind==='TOWER'||entity.kind==='INHIBITOR';
      node.visible=state!==undefined&&(structure||(state!=='DESTROYED'&&state!=='DESPAWNED'));
      node.alpha=state==='DESTROYED'?.3:state==='UNKNOWN'?.5:1;
      cross.visible=state==='DESTROYED';
      label.text=`${mapEntityLabel(entity)} · ${state==='OBSERVED'?entity.kind==='VOID_GRUB'?'observed entity; initial placement':'observed in keyframe':state==='UNKNOWN'?'destroyed previously; rebuild state unknown':state?.toLowerCase()??'unobserved'}`;
    }
  }};
}
