import {describe,it,expect} from 'vitest';
import type {MapEntity} from '../../shared/replay';
import {mapEntityStateAt,mapEntityIcon} from './mapEntities';
const tower:MapEntity={id:'t',name:'tower',kind:'TOWER',x:6919,y:1483,source:{confidence:'VERIFIED'},states:[{timestamp:0,state:'ALIVE'},{timestamp:687.36,state:'DESTROYED'}]};
describe('persistent map state',()=>{
  it('seeks across destruction and back without retaining stale state',()=>{
    expect(mapEntityStateAt(tower,687.35)).toBe('ALIVE');
    expect(mapEntityStateAt(tower,687.36)).toBe('DESTROYED');
    expect(mapEntityStateAt(tower,2000)).toBe('DESTROYED');
    expect(mapEntityStateAt(tower,0)).toBe('ALIVE');
  });
  it('does not invent objective spawn times or respawns',()=>{
    const objective:MapEntity={...tower,kind:'BARON',states:[{timestamp:1200.48,state:'OBSERVED'},{timestamp:1470.8,state:'DESTROYED'}]};
    expect(mapEntityStateAt(objective,1200)).toBeUndefined();
    expect(mapEntityStateAt(objective,1400)).toBe('OBSERVED');
    expect(mapEntityStateAt(objective,2000)).toBe('DESTROYED');
    expect(mapEntityStateAt(objective,1199)).toBeUndefined();
    expect(mapEntityIcon(objective)).toBe('baron');
  });
});

it('tracks three individual grub deaths and restores them on backward seek',()=>{
  const grubs:MapEntity[]=[628.275972,641.98709,652.34809].map((time,i)=>({...tower,id:`grub-${i}`,name:`SRU_Horde.12.${i+1}`,kind:'VOID_GRUB',states:[{timestamp:473.25,state:'OBSERVED'},{timestamp:time,state:'DESTROYED'}]}));
  const visible=(time:number)=>grubs.filter(e=>mapEntityStateAt(e,time)==='OBSERVED').length;
  expect(visible(470)).toBe(0);expect(visible(600)).toBe(3);expect(visible(635)).toBe(2);
  expect(visible(645)).toBe(1);expect(visible(655)).toBe(0);expect(visible(600)).toBe(3);
  const cleanup:MapEntity={...grubs[0],states:[{timestamp:473.25,state:'OBSERVED'},{timestamp:885.022,state:'DESPAWNED'}]};
  expect(mapEntityStateAt(cleanup,886)).toBe('DESPAWNED');
});
