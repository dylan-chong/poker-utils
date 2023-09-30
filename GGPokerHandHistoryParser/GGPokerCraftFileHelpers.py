from pathlib import Path
import glob
import re
import os
import zipfile
import tempfile

from GGPokerHandHistoryParser.GGPokerCraftExportParser import parse_hand_basic, parse_hand
from GGPokerHandHistoryParser.Utils import DOWNLOADS_DIR, NonAnalyzableHandException
from GGPokerHandHistoryParser.Calculations import calculate_positions_for_hand, calculate_preflop_actions_for_chart

UUID_REGEX = r'^[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12}$'

def load_all_lazy_hands():
    files_dir = extract_downloads()

    file_glob = str(Path(files_dir, Path("GG20*.txt")))
    files = glob.glob(file_glob)
    files.sort()

    lazy_hands = []

    for file in files:
        lazy_hands_from_file = load_hands_from_file(file)
        lazy_hands.extend(lazy_hands_from_file)
    
    return lazy_hands

def extract_downloads():
    file_paths = os.listdir(DOWNLOADS_DIR)

    pattern = UUID_REGEX.replace('$', '.zip$')
    zip_paths = [
        Path(Path(DOWNLOADS_DIR), Path(path))
        for path in file_paths
        if re.match(pattern, path)
    ]
    zip_paths.sort(key=lambda path: os.path.getmtime(path))

    temp_dir = tempfile.TemporaryDirectory().name

    extracted_files = []
    for path in zip_paths:
        with zipfile.ZipFile(path, 'r') as zip:
            files = [
                file for file in zip.namelist()
                if re.match(r'^GG20.*\.txt$', file)
            ]
            extracted_files.extend(files)
            zip.extractall(temp_dir, files)
    
    print(f'{len(extracted_files)} files extracted from {len(zip_paths)} zips')
    return temp_dir

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

    lazy_hands = []
    for lines in hands_lines_stripped:
        basic_hand, segments = parse_hand_basic(lines)

        def parse(seg=segments, basic=basic_hand):
            return parse_and_calculate_hand(seg, basic)

        lazy_hands.append({ **basic_hand, 'parse': parse })

    return lazy_hands

def parse_and_calculate_hand(segments, basic_hand):
    try:
        if 'postflop' not in segments:
            raise NonAnalyzableHandException("Hand ended preflop")

        hand = parse_hand(segments, basic_hand)

        preflop_actions_for_chart = calculate_preflop_actions_for_chart(hand)
        full_hand = {
            **hand,
            'preflop': { **hand['preflop'], **preflop_actions_for_chart }
        }

        positions = calculate_positions_for_hand(full_hand)
        full_hand = {**hand, **positions}
        return full_hand
    except NonAnalyzableHandException as e:
        hand = {**basic_hand}
        hand['error'] = e.args[0]
        return hand
