import os
from pathlib import Path
import pytest
from parser import ReplayParser

@pytest.fixture(scope='session')
def replay_file():
    path = Path(os.environ.get('ROFL_TEST_FILE', r'C:\Users\tom-d\OneDrive\Documents\League of Legends\Replays\NA1-5640196741.rofl'))
    if not path.is_file():
        pytest.skip('Set ROFL_TEST_FILE to the private NA1-5640196741.rofl integration fixture.')
    return path

@pytest.fixture(scope='session')
def replay_parser():
    return ReplayParser(os.environ.get('LEAGUE_CLIENT_EXE', r'C:\Riot Games\League of Legends\Game\League of Legends.exe'))

@pytest.fixture(scope='session')
def normalized(replay_file, replay_parser):
    if not replay_parser.client_exe.is_file():
        pytest.skip('Set LEAGUE_CLIENT_EXE to the exact matching client for semantic integration tests.')
    return replay_parser.parse(replay_file)
