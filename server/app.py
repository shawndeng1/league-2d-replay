import json
import logging
import os
import re
import tempfile
import threading
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool
from parser import ReplayParser, ParseError

ROOT = Path(__file__).resolve().parents[1]
STORE = Path(os.environ.get('REPLAY_STORE', ROOT / 'samples/local/replays'))
CLIENT = os.environ.get('LEAGUE_CLIENT_EXE', r'C:\Riot Games\League of Legends\Game\League of Legends.exe')
MAX_UPLOAD = 128 * 1024 * 1024
parse_lock = threading.Lock()
app = FastAPI(title='Rift Replay API', version='0.1.0')
logging.basicConfig(level=logging.INFO)

def replay_path(replay_id: str) -> Path:
    if not re.fullmatch(r'[0-9a-f]{64}', replay_id):
        raise HTTPException(404, 'Replay not found.')
    path = STORE / f'{replay_id}.json'
    if not path.is_file():
        raise HTTPException(404, 'Replay not found.')
    return path

@app.get('/api/health')
def health():
    return {'status': 'ok', 'supportedClient': '16.18.817.5716', 'clientAvailable': Path(CLIENT).is_file()}

@app.post('/api/replays', status_code=201)
async def upload(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith('.rofl'):
        await file.close()
        raise HTTPException(415, 'Select a .rofl replay file.')
    if not parse_lock.acquire(blocking=False):
        await file.close()
        raise HTTPException(503, 'A replay is currently parsing. Try again shortly.')
    path = None
    try:
        STORE.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=STORE, suffix='.rofl', delete=False) as tmp:
            path = Path(tmp.name)
            size = 0
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD:
                    raise HTTPException(413, 'Replay exceeds the 128 MB limit.')
                tmp.write(chunk)
        result = await run_in_threadpool(ReplayParser(CLIENT).parse, path)
        replay_id = result['metadata']['sourceSha256']
        destination = STORE / f'{replay_id}.json'
        temporary = destination.with_suffix('.part')
        temporary.write_text(json.dumps(result, separators=(',', ':')), encoding='utf-8')
        temporary.replace(destination)
        return {'id': replay_id, 'metadata': result['metadata'], 'sampleCount': result['diagnostics']['sampleCount']}
    except ParseError as exc:
        raise HTTPException(422, {'code': exc.code, 'message': str(exc)}) from exc
    finally:
        if path is not None:
            path.unlink(missing_ok=True)
        await file.close()
        parse_lock.release()

@app.get('/api/replays/{replay_id}')
@app.get('/api/replays/{replay_id}/data')
def data(replay_id: str):
    return FileResponse(replay_path(replay_id), media_type='application/json')

@app.get('/api/replays/{replay_id}/metadata')
def metadata(replay_id: str):
    result = json.loads(replay_path(replay_id).read_text(encoding='utf-8'))
    return {'metadata': result['metadata'], 'players': result['players'], 'diagnostics': result['diagnostics']}
