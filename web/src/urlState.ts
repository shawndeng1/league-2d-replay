export interface ReplayUrlState {replayId?:string;time:number;player?:number;event?:string}
export function parseReplayUrlState(url:string):ReplayUrlState{
  const parsed=new URL(url,'http://localhost');const match=/^\/replay\/([a-f0-9]{64})\/?$/.exec(parsed.pathname);
  const time=Number(parsed.searchParams.get('t')??0),rawPlayer=parsed.searchParams.get('player'),player=rawPlayer===null?NaN:Number(rawPlayer);
  return {replayId:match?.[1],time:Number.isFinite(time)?Math.max(0,time):0,...(Number.isInteger(player)&&player>=0&&player<10?{player}:{}),...(parsed.searchParams.get('event')?{event:parsed.searchParams.get('event')!}:{})};
}
export function serializeReplayUrlState(state:ReplayUrlState){const query=new URLSearchParams();query.set('t',Math.max(0,Number.isFinite(state.time)?state.time:0).toFixed(2));if(state.player!==undefined)query.set('player',String(state.player));if(state.event)query.set('event',state.event);return `${state.replayId?`/replay/${state.replayId}`:'/'}?${query}`;}
