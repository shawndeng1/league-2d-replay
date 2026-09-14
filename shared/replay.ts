/** Format v1: seconds, Riot planar world coordinates; no ROFL protocol types. */
export interface WorldPoint { x: number; y: number }
export interface PositionSample { timestamp: number; x: number; y: number; speed?: number; positionOnly?:boolean; positionSource?:string; /** Commanded route, including origin. Destinations are not timestamped observations. */ path?: WorldPoint[] }
export interface Player { id: number; championName: string; championId?: number; displayName?:string; team: 'BLUE' | 'RED'; role: string; finalStats?: {kills?:number;deaths?:number;assists?:number;level?:number;totalGold?:number;minionKills?:number;neutralMinionKills?:number} }
export interface Track { playerId: number; samples: PositionSample[] }
export interface WorldBounds { minX: number; maxX: number; minY: number; maxY: number }
interface BaseEvent { mapEntityId?:string; id:string; timestamp:number; x?:number; y?:number; source:{opcode:string;packetSize:number;rawTimestamp:number;confidence:'VERIFIED'|'LIKELY'|'UNKNOWN';victimEntityId?:number;killerEntityId?:number;entityId?:number;creditedEntityId?:number;corroboratingOpcode?:string;creditOpcode?:string;coordinateSource?:string;coordinateTimestamp?:number;coordinateConfidence?:'LIKELY'|'VERIFIED'} }
export interface ChampionKillEvent extends BaseEvent {type:'CHAMPION_KILL';killerPlayerId?:number;victimPlayerId:number;assistingPlayerIds?:number[]}
export interface ObjectiveEvent extends BaseEvent {type:'OBJECTIVE_KILL';coverage?:'CAMP_ANNOUNCED_KILL_ONLY';objective:'DRAGON'|'RIFT_HERALD'|'BARON'|'VOID_GRUB';killerTeam?:'BLUE'|'RED';killerPlayerId?:number}
export interface StructureEvent extends BaseEvent {type:'STRUCTURE_DESTROYED';structure:'TOWER'|'INHIBITOR';lane?:string;tier?:string;destroyedTeam:'BLUE'|'RED'}
export interface RespawnEvent extends BaseEvent {type:'CHAMPION_RESPAWN';playerId:number;deathEventId:string;x:number;y:number}
export type GameEvent = ChampionKillEvent | RespawnEvent | ObjectiveEvent | StructureEvent;
export interface MapEntity {
  id:string; kind:'TOWER'|'INHIBITOR'|'DRAGON'|'RIFT_HERALD'|'BARON'|'VOID_GRUB'; name:string;
  x:number; y:number; team?:'BLUE'|'RED'; lane?:string; tier?:string;
  states:{timestamp:number;state:'ALIVE'|'OBSERVED'|'DESTROYED'|'DESPAWNED'|'UNKNOWN';eventId?:string}[];
  source:{identityOpcode?:string;positionOpcode?:string;confidence:'VERIFIED'|'LIKELY'|'UNKNOWN';presenceStart?:'FIRST_KEYFRAME_OBSERVATION'|'FIRST_OBSERVATION';asset?:string};
}
export interface Replay {
  schemaVersion: 1;
  metadata: { patch: string; mapId: number; duration: number; sourceSha256: string; decoder: string; positionSource: string; worldBounds: WorldBounds; entityMapping: string; eventCoverage?:{championKills:boolean;respawns?:boolean;assists:boolean;objectives:boolean;dragons?:boolean;voidGrubs?:'CAMP_ANNOUNCED_KILL_ONLY'|'INDIVIDUAL_KILLS';structures:boolean} };
  players: Player[];
  tracks: Track[];
  events: GameEvent[];
  mapEntities?:MapEntity[];
  diagnostics: { movementPackets: number; sampleCount: number; supplementalPositionSamples?: number; opcodeHistogram: Record<string, number> };
}
