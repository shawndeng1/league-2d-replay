"""Print a reviewable event feed from normalized JSON; never infers events."""
import argparse
import json

def main():
    ap=argparse.ArgumentParser();ap.add_argument('normalized_replay');args=ap.parse_args()
    with open(args.normalized_replay,encoding='utf-8') as handle: replay=json.load(handle)
    names={p['id']:p['championName'] for p in replay['players']}
    for e in replay['events']:
        minutes=int(e['timestamp']//60);seconds=e['timestamp']%60
        if e['type']=='CHAMPION_KILL':
            print(f"{minutes:02}:{seconds:06.3f} CHAMPION_KILL {names.get(e.get('killerPlayerId'),'Non-player')} -> {names[e['victimPlayerId']]} [{e['id']}]")
        elif e['type']=='CHAMPION_RESPAWN':
            print(f"{minutes:02}:{seconds:06.3f} CHAMPION_RESPAWN {names[e['playerId']]} [{e['id']}]")
        elif e['type']=='OBJECTIVE_KILL':
            print(f"{minutes:02}:{seconds:06.3f} {e['objective']}_KILL {e.get('killerTeam','Unknown team')} [{e['id']}]")

if __name__=='__main__':main()
