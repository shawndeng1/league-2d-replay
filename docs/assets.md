# Static assets

The map and cached champion icons are Riot-provided Data Dragon assets from
version `16.18.1`. Source URL prefix:
`https://ddragon.leagueoflegends.com/cdn/16.18.1/`.

- Map: `img/map/map11.png` (512 × 512 schematic Summoner's Rift map).
- Icons: `img/champion/{championName}.png`.
- Champion ID/name catalog: `data/en_US/champion.json`.

Run `python tools/fetch_assets.py` to reproduce the files. The cached icons
cover the primary integration replay; other roster icons resolve through the
same official CDN in `web/src/assets.ts`. Static assets and game trademarks
remain Riot's property, not this project's original code.

See [Riot's Data Dragon documentation](https://developer.riotgames.com/docs/lol#data-dragon).
