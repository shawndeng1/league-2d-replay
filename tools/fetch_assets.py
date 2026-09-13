"""Cache official Riot Data Dragon static assets; no API key required."""
import json
from pathlib import Path
from urllib.request import urlopen

VERSION = '16.18.1'
ROOT = Path(__file__).resolve().parents[1]
BASE = f'https://ddragon.leagueoflegends.com/cdn/{VERSION}'
def fetch(url):
    with urlopen(url, timeout=30) as response:
        return response.read()

def main():
    data = json.loads(fetch(BASE + '/data/en_US/champion.json'))['data']
    catalog = {v['id']: {'id': int(v['key']), 'name': v['name'], 'image': v['image']['full']} for v in data.values()}
    (ROOT/'shared/champions.json').write_text(json.dumps(catalog, indent=2), encoding='utf-8')
    assets = ROOT/'web/public/assets'
    (assets/'champions').mkdir(parents=True, exist_ok=True)
    (assets/'map11.png').write_bytes(fetch(BASE+'/img/map/map11.png'))
    for name in ['Malphite','Graves','TwistedFate','Ashe','Seraphine','Camille','Naafiri','Syndra','Vayne','Shaco']:
        (assets/'champions'/f'{name}.png').write_bytes(fetch(BASE+'/img/champion/'+catalog[name]['image']))
    print(f'Cached map, 10 icons and {len(catalog)} champion catalog entries from Data Dragon {VERSION}.')

if __name__ == '__main__':
    main()
