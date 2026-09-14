import longGapFixture from './long-route-gaps.fixture.json';
import turnsFixture from './rapid-turns.fixture.json';
import boundaryFixture from './movement-boundaries.fixture.json';
import {describe,expect,it} from 'vitest';
import {findFrameAtTime,interpolatePosition,samplePosition,worldToMap} from './math';
const frames=[{timestamp:125,x:5000,y:7000},{timestamp:126,x:5400,y:7100},{timestamp:140,x:6000,y:7200}];
describe('rapid recorded reversals',()=>{
  it('reaches actual rapid-turn origins across five replays without predicting past them',()=>{
    for(const {samples} of turnsFixture.cases){
      const [a,b]=samples,original=JSON.stringify(samples);
      const vx=b.x-a.x,vy=b.y-a.y,limit=vx*vx+vy*vy;
      let last=-1;
      for(let step=0;step<=20;step++){
        const p=samplePosition(samples,a.timestamp+(b.timestamp-a.timestamp)*step/20)!;
        const progress=(p.x-a.x)*vx+(p.y-a.y)*vy;
        expect(progress).toBeGreaterThanOrEqual(last-1e-6);
        expect(progress).toBeLessThanOrEqual(limit+1e-6);
        last=progress;
      }
      const before=samplePosition(samples,b.timestamp-1e-6)!;
      expect(Math.hypot(before.x-b.x,before.y-b.y)).toBeLessThan(.01);
      expect(samplePosition(samples,a.timestamp)).toMatchObject({x:a.x,y:a.y});
      expect(JSON.stringify(samples)).toBe(original);
    }
  });
  it('keeps larger or off-route reversals unsmoothed',()=>{
    const a={timestamp:0,x:0,y:0,speed:1000,path:[{x:0,y:0},{x:1000,y:0}]};
    const off={timestamp:.2,x:50,y:100,path:[{x:50,y:100},{x:0,y:100}]};
    const large={timestamp:.2,x:50,y:0,path:[{x:50,y:0},{x:0,y:0}]};
    for(const b of [off,large])expect(samplePosition([a,b],.1)).toMatchObject({x:100,y:0});
  });
});
describe('interpolatePosition',()=>{
  it('interpolates the midpoint',()=>expect(interpolatePosition(frames[0],frames[1],125.5)).toEqual({x:5200,y:7050}));
  it('clamps and handles coincident times',()=>{expect(interpolatePosition(frames[0],frames[1],124)).toEqual({x:5000,y:7000});expect(interpolatePosition(frames[0],frames[1],128)).toEqual({x:5400,y:7100});expect(interpolatePosition(frames[0],frames[0],125)).toEqual({x:5000,y:7000});});
});
describe('findFrameAtTime',()=>{
  it('handles boundaries, seeking and empty data',()=>{expect(findFrameAtTime([],1)).toBe(-1);expect(findFrameAtTime(frames,0)).toBe(0);expect(findFrameAtTime(frames,125.5)).toBe(0);expect(findFrameAtTime(frames,126)).toBe(1);expect(findFrameAtTime(frames,999)).toBe(2);});
  it('chooses the last update at the same timestamp',()=>expect(findFrameAtTime([frames[0],frames[0],frames[1]],125)).toBe(1));
});
describe('worldToMap',()=>{
  it('inverts world north and maps the exact bounds',()=>{expect(worldToMap(0,0)).toEqual({x:0,y:800});expect(worldToMap(14716,14824)).toEqual({x:800,y:0});expect(worldToMap(7358,7412)).toEqual({x:400,y:400});});
  it('supports non-square images and configurable bounds',()=>expect(worldToMap(15,30,200,100,{minX:10,maxX:20,minY:20,maxY:40})).toEqual({x:100,y:50}));
});
describe('display discontinuities',()=>{
  it('holds supplemental observations without inventing a route and supports backward seeking',()=>{
    const samples=[{timestamp:340.498318,x:7726,y:7412,speed:335,path:[{x:7726,y:7412}]},
      {timestamp:342.335318,x:8210,y:7934,positionOnly:true},
      {timestamp:344.142318,x:8216,y:7942,speed:335,path:[{x:8216,y:7942},{x:8622,y:8356}]}];
    expect(samplePosition(samples,343)).toMatchObject({x:8210,y:7934});
    expect(samplePosition(samples,341)).toMatchObject({x:7726,y:7412});
    expect(samplePosition(samples,344.142318)).toMatchObject({x:8216,y:7942});
    expect(samplePosition(samples,343)).toMatchObject({x:8210,y:7934});
  });
  it('holds stationary positions and long gaps',()=>{expect(samplePosition([{...frames[0],speed:0},frames[1]],125.5)?.x).toBe(5000);expect(samplePosition(frames,135)?.x).toBe(5400);});
  it('snaps at the next sample after a large jump',()=>{const f=[frames[0],{timestamp:126,x:14000,y:14000}];expect(samplePosition(f,125.5)?.x).toBe(5000);expect(samplePosition(f,126)?.x).toBe(14000);});
  it('handles missing tracks',()=>expect(samplePosition([],1)).toBeNull());
});
describe('recorded movement routes',()=>{
  const route = [{timestamp:0,x:0,y:0,speed:100,path:[{x:0,y:0},{x:300,y:0},{x:300,y:400}]},{timestamp:20,x:5000,y:5000,speed:0,path:[{x:5000,y:5000}]}];
  it('follows bends at the recorded speed despite a long gap',()=>{
    expect(samplePosition(route,2)).toMatchObject({x:200,y:0});
    expect(samplePosition(route,5)).toMatchObject({x:300,y:200});
  });
  it('holds the endpoint and applies the next observed position exactly',()=>{
    expect(samplePosition(route,19)).toMatchObject({x:300,y:400});
    expect(samplePosition(route,20)).toMatchObject({x:5000,y:5000});
    expect(samplePosition(route,2)).toMatchObject({x:200,y:0}); // Seeking is stateless.
  });
  it('stops on zero speed and handles repeated waypoints',()=>{
    expect(samplePosition([{...route[0],speed:0}],5)).toMatchObject({x:0,y:0});
    expect(samplePosition([{...route[0],path:[{x:0,y:0},{x:0,y:0},{x:300,y:0}]}],2)).toMatchObject({x:200,y:0});
  });
  it('moves Malphite during the real replay’s 17–29 second command gap',()=>{
    const samples=[{timestamp:17.21477827453615,x:620,y:750,speed:824.625,path:[{x:620,y:750},{x:1400,y:10284}]},{timestamp:29.07277827453619,x:1370,y:9922}];
    const position=samplePosition(samples,22.21477827453615)!;
    expect(position.x).toBeGreaterThan(900);
    // The later observed origin also reveals decay in the initial speed.
    expect(position.y).toBeCloseTo(750+(9922-750)*5/(29.07277827453619-17.21477827453615),5);
    const before=samplePosition(samples,29.07277827453619-1e-6)!;
    expect(Math.hypot(before.x-1370,before.y-9922)).toBeLessThan(.01);
  });
});

describe('real replay movement corrections',()=>{
  it('removes small update-boundary snaps in NA1-5640962900 without changing raw samples',()=>{
    for(const example of boundaryFixture.cases){
      const samples=example.samples,original=JSON.stringify(samples),next=samples[1];
      const before=samplePosition(samples,next.timestamp-0.000001)!;
      expect(Math.hypot(before.x-next.x,before.y-next.y),example.champion).toBeLessThan(.01);
      expect(samplePosition(samples,next.timestamp)).toMatchObject({x:next.x,y:next.y});
      const middle=(samples[0].timestamp+next.timestamp)/2;
      const expected=samplePosition(samples,middle);
      samplePosition(samples,next.timestamp+20);
      expect(samplePosition(samples,middle)).toEqual(expected);
      expect(JSON.stringify(samples)).toBe(original);
    }
  });
  it('does not smooth large relocations or explicit stopped samples',()=>{
    const moving={timestamp:0,x:0,y:0,speed:400,path:[{x:0,y:0},{x:2000,y:0}]};
    expect(samplePosition([moving,{timestamp:1,x:900,y:0}],.5)).toMatchObject({x:200,y:0});
    expect(samplePosition([moving,{timestamp:1,x:900,y:0}],1)).toMatchObject({x:900,y:0});
    expect(samplePosition([{...moving,speed:0},{timestamp:1,x:40,y:0}],.5)).toMatchObject({x:0,y:0});
    expect(samplePosition([{...moving,path:[{x:0,y:0}]},{timestamp:1,x:40,y:0}],.5)).toMatchObject({x:0,y:0});
  });
});

describe('reported long-gap stutters in 5640962900',()=>{
  it('keeps Yi at 25s and Ashe at 26s moving forward through the next observation',()=>{
    for(const {champion,samples} of longGapFixture.cases){
      const [a,b]=samples,original=JSON.stringify(samples);
      let previous=samplePosition(samples,a.timestamp)!;
      for(let t=a.timestamp+1/60;t<b.timestamp;t+=1/60){
        const current=samplePosition(samples,t)!;
        expect(current.y,champion).toBeLessThanOrEqual(previous.y);
        expect(Math.hypot(current.x-previous.x,current.y-previous.y),champion).toBeLessThan(16);
        previous=current;
      }
      const last=samplePosition(samples,b.timestamp-1e-6)!;
      expect(Math.hypot(last.x-b.x,last.y-b.y),champion).toBeLessThan(.01);
      expect(samplePosition(samples,b.timestamp)).toMatchObject({x:b.x,y:b.y});
      expect(samplePosition(samples,a.timestamp)).toMatchObject({x:a.x,y:a.y});
      expect(JSON.stringify(samples)).toBe(original);
    }
  });
  it('preserves route bends, completed routes, off-route relocations and zero speed',()=>{
    const a={timestamp:0,x:0,y:0,speed:100,path:[{x:0,y:0},{x:100,y:0},{x:100,y:500}]};
    const b={timestamp:4,x:100,y:200};
    expect(samplePosition([a,b],1)).toMatchObject({x:75,y:0});
    expect(samplePosition([a,b],2)).toMatchObject({x:100,y:50});
    expect(samplePosition([a,{timestamp:12,x:100,y:500}],8)).toMatchObject({x:100,y:500});
    expect(samplePosition([a,{timestamp:4,x:4000,y:4000}],3)).toMatchObject({x:100,y:200});
    expect(samplePosition([{...a,speed:0},b],3)).toMatchObject({x:0,y:0});
  });
});
