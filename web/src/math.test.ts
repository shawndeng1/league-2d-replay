import {describe,expect,it} from 'vitest';
import {findFrameAtTime,interpolatePosition,samplePosition,worldToMap} from './math';
const frames=[{timestamp:125,x:5000,y:7000},{timestamp:126,x:5400,y:7100},{timestamp:140,x:6000,y:7200}];
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
    expect(position.y).toBeGreaterThan(4800);
    expect(position.y).toBeLessThan(4900);
  });
});
