from pathlib import Path
import glob
import re
import os
import zipfile
import tempfile
import shutil
from collections import ChainMap
import multiprocessing

from GGPokerHandHistoryParser.GGPokerCraftExportParser import parse_hand_basic, parse_hand
from GGPokerHandHistoryParser.Utils import DOWNLOADS_DIR, NonAnalyzableHandException
from GGPokerHandHistoryParser.Calculations import calculate_positions_for_hand, calculate_preflop_actions_for_chart

UUID_REGEX = r'^[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12}$'

GG_FILE_GLOB = "GG*.txt"

def load_all_hands(hand_cache):
    temp_dir = tempfile.TemporaryDirectory().name
    extract_downloads(temp_dir)
    copy_downloads_non_zipped(temp_dir)

    file_glob = str(Path(temp_dir, Path('**/' + GG_FILE_GLOB)))
    files = glob.glob(file_glob, recursive=True)
    files.sort()

    unloaded_files = [file for file in files if os.path.basename(file) not in hand_cache]
    print(f'Loading {len(unloaded_files)} files matching {GG_FILE_GLOB}')

    with multiprocessing.Pool() as pool:
        hands_files = pool.map(load_hands_from_file, unloaded_files)

    hands_per_file = {**hand_cache}
    for hands, file in hands_files:
        hands_per_file[os.path.basename(file)] = hands

    return hands_per_file


def extract_downloads(temp_dir):
    file_paths = os.listdir(DOWNLOADS_DIR)

    pattern = UUID_REGEX.replace('$', '.zip$')
    zip_paths = [
        Path(Path(DOWNLOADS_DIR), Path(path))
        for path in file_paths
        if re.match(pattern, path)
    ]
    zip_paths.sort(key=lambda path: os.path.getmtime(path))

    for path in zip_paths:
        with zipfile.ZipFile(path, 'r') as zip:
            zip.extractall(temp_dir)
    
    return temp_dir

def copy_downloads_non_zipped(to_dir):
    file_glob = str(Path(DOWNLOADS_DIR, Path('**/' + GG_FILE_GLOB)))
    files = glob.glob(file_glob, recursive=True)
    for file in files:
        shutil.copy(file, to_dir)

def load_hands_from_file(file):
    with open(file, "r") as f:
        contents = f.read()

    hand_strings = contents.split('\n\n')
    hand_strings_stripped = [str.strip() for str in hand_strings if str.strip() != '']

    hands_lines_stripped = [
        [
            line.strip()
            for line in hand_string.split('\n')
            if line.strip() != ''
        ]
        for hand_string in hand_strings_stripped
    ]

    hands = []
    for lines in hands_lines_stripped:
        basic_hand, segments = parse_hand_basic(lines)
        hands.append(parse_and_calculate_hand(segments, basic_hand))

    return hands, file

def parse_and_calculate_hand(segments, basic_hand):
    hand = {**basic_hand}
    try:
        hand = parse_hand(segments, basic_hand)

        if 'postflop' not in segments:
            hand['error'] = "Hand ended preflop"

        preflop_actions_for_chart = calculate_preflop_actions_for_chart(hand)
        full_hand = {
            **hand,
            'preflop': { **hand['preflop'], **preflop_actions_for_chart }
        }

        positions = calculate_positions_for_hand(full_hand)
        full_hand = {**hand, **positions}
        return full_hand
    except NonAnalyzableHandException as e:
        if hand and 'error' in hand: return hand
        hand['error'] = e.args[0]
        return hand
