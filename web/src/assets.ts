import catalog from '../../shared/champions.json';
import type { Player } from '../../shared/replay';
export const ASSET_VERSION = '16.18.1';
export const mapAsset = '/assets/map11.png';
const local = new Set(['Malphite','Graves','TwistedFate','Ashe','Seraphine','Camille','Naafiri','Syndra','Vayne','Shaco']);
export function championAsset(player: Player) {
  const entry = (catalog as Record<string,{id:number;name:string;image:string}>)[player.championName]
    ?? Object.values(catalog).find(c => c.id === player.championId);
  const name = entry?.image ?? `${player.championName}.png`;
  return local.has(player.championName) ? `/assets/champions/${name}` : `https://ddragon.leagueoflegends.com/cdn/${ASSET_VERSION}/img/champion/${encodeURIComponent(name)}`;
}
export function championDisplayName(player: Player) {
  return (catalog as Record<string,{name:string}>)[player.championName]?.name ?? player.championName;
}
