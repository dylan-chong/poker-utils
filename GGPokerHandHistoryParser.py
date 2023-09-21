"""
# Setup 
You will have to run PreflopChartsExtractor.py to produce the charts JSON. See that file for docs

# Deps
pip3 install parse
pip3 install pyperclip

# Run
python3 GGPokerHandHistoryParser.py

# To export, for another person to use
pip3 install pyinstaller
pyinstaller.exe GGPokerHandHistoryParser.py -y --add-data 'PreflopChartExtractions/PreflopCharts.json;data'
# Then compress/send the folder inside /dist/
"""

import os
import glob
import traceback
import json
import re
import zipfile
import tempfile
from datetime import datetime
from pathlib import Path

from parse import *
import pyperclip

SEAT_NUM_TO_SEAT = {
    1: 'BTN',
    2: 'SB',
    3: 'BB',
    4: 'LJ',
    5: 'HJ',
    6: 'CO',
}
POSTFLOP_SEAT_ORDER = ['SB', 'BB', 'LJ', 'HJ', 'CO', 'BTN']
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
SUIT_LETTERS = ["c", "d", "h", "s"]

DOWNLOADS_DIR = Path(Path.home(), Path('Downloads'))
LOG_FILE_PATH = Path(DOWNLOADS_DIR, Path('GG'), Path('history.txt'))

UUID_REGEX = r'^[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12}$'

CHART_FILE = Path('PreflopChartExtractions/PreflopCharts.json')
with open(CHART_FILE) as f:
    range_chart = json.load(f)

class NonAnalyzableHandException(Exception):
    "Raised when the hand can't be analysed, e.g., the player folds preflop, or nobody calls the player's open raise"
    pass
class InvalidSearchException(Exception):
    pass

def main():
    print(f'Download your GG PokerCraft hand history zips into your `{DOWNLOADS_DIR}` directory')

    while True:
        try:
            print()
            save_to_history_file(*main_loop())
        except InvalidSearchException as e:
            print(e)
        except Exception as e:
            print('-----------------------------------')
            print('*** An unexpected error has occurred. Please send Dylan the following contents: ***')
            traceback.print_exc()
            print('-----------------------------------')

def main_loop():
    print(f'Enter command, e.g.: ')
    print(f'- r - show recent analysable hands (where the hero reaches the flop, without limp or check)')
    print(f'- #RC1800277957 - show hand with the given hand ID (requires extraction) ')
    print(f'- l - repeat the last search')
    print(f'- h - show search history')
    print(f'- c - `c bb co lj` to print heads up ranges for BB call, vs CO 3Bet vs LJ RFI')
    print(f'- a - show all hands')
    search_term = input('>>> ').strip()
    print()
    search_term = reformat_search_term(search_term)

    if search_term == 'h':
        print_history()
        return search_term, []
    if search_term.startswith('c '):
        print_call_and_raise_range(search_term)
        return search_term, []

    lazy_hands = load_all_lazy_hands()
    lazy_hands.sort(key=lambda hand: hand['date'])
    hands = []
    
    if search_term.startswith('#'):
        for lazy_hand in lazy_hands:
            if lazy_hand['id'] != search_term: continue
            hand = lazy_hand['parse']()
            hands.append(hand)
            if 'error' in hand:
                print_hand_error(hand)
                continue
            print_hand(hand, wait_between_sections=True)

    if search_term == 'a':
        for lazy_hand in lazy_hands:
            hand = lazy_hand['parse']()
            if 'error' in hand:
                print_hand_error(hand)
                continue
            print_hand(hand)
            hands.append(hand)
    
    if search_term == 'r':
        for lazy_hand in reversed(lazy_hands):
            if len(hands) == 50: break
            hand = lazy_hand['parse']()
            if 'error' in hand: continue
            hands.append(hand)
        hands = list(reversed(hands))
        for hand in hands: print_hand_short(hand)

    print()
    for line in format_result_count(search_term, hands):
        print(line)
    return search_term, hands

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

def reformat_search_term(search_term):
    if search_term in ['h', 'e', 'a', 'r']: return search_term

    if search_term.startswith('RC'):
        search_term = '#' + search_term

    if search_term.startswith('#RC'):
        if not re.match(r'^#RC\d{7,13}$', search_term):
            raise InvalidSearchException(f'Invalid hand ID `{search_term}`')
        return search_term

    if search_term == 'l':
        last_term = last_search_term() or ''
        print(f'Last search term: `{last_term}`')
        return reformat_search_term(last_term.strip())

    if search_term.startswith('c '):
        return search_term

    raise InvalidSearchException(f'Unknown command `{search_term}`')

def last_search_term():
    lines = read_history(1)
    if len(lines) == 0:
        return None
    return lines[-1].split(' - ')[0]

def print_history():
    history = read_history(50)
    for i, line in enumerate(history):
        print(f'{len(history) - i}. {line}')

def read_history(n_lines_from_end):
    with open(LOG_FILE_PATH, 'r') as f:
        lines = [line.strip() for line in f.readlines() if line.strip() != '']
        return lines[-n_lines_from_end:]

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

def save_to_history_file(search_term, matches):
    with open(LOG_FILE_PATH, 'a+') as f:
        for line in format_history_lines(search_term, matches):
            f.write(line)
            f.write('\n')

def format_history_lines(search_term, matches):
    if search_term in ['l', 'h', 'a', 'e', 'r']: return []
    if search_term.startswith('c '): return []
    if len(matches) == 0: return [f'{search_term} - {len(matches)} matches']
    return format_result_count(search_term, matches)

def format_result_count(search_term, matches):
    match_cards = [
        format_cards(hand['players']['Hero']['hole_cards'])
        for hand in matches
        if 'error' not in hand
    ]

    non_analysable = [hand for hand in matches if 'error' in hand]
    non_analysable_suffix = '' if len(non_analysable) == 0 else f', {len(non_analysable)} not'

    count_label = 'recent analysable' if search_term == 'r' else 'analysable'
    counts = f'{len(match_cards)} {count_label}{non_analysable_suffix}'

    if len(match_cards) == 0: matches_joined = ''
    else: matches_joined = ' - ' + ', '.join(match_cards)
    return [f'{search_term} - {counts}{matches_joined}']

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

def get_postflop_seat(player_id, hand):
    if hand['oop']['player_id'] == player_id: return 'oop'
    if hand['ip']['player_id'] == player_id: return 'ip'
    return None
    
def print_hand_title(hand):
    print(f'{hand["id"]} - {hand["date"]}')

def print_hand_error(hand):
    print_hand_title(hand)
    print(f'  {hand["error"]}')

def print_hand(hand, wait_between_sections=False):
    print()
    print_hand_title(hand)
    print_position('oop', hand)
    print_position('ip', hand)
    print(f'  Board')
    print(f'    {format_cards(hand.get("board", []), sort=False)}')
    print(f'  Starting Pot')
    print(f'    ${hand["preflop"]["pot"]:.2f}')
    print(f'  Effective Stack')
    print(f'    ${calculate_effective_stack_size_on_flop(hand):.2f}')
    print_actions('preflop', hand, include_folds=False, include_aggressor=True)

    if wait_between_sections:
        pyperclip.copy(gen_desktop_postflop_json(hand))
        print(f'Copied Desktop Postflop JSON to clipboard.')
        print(f'-------------------------')
        input(f'Press ENTER to continue ')
    else:
        print(f'  -------------------------')

    print_actions('flop', hand, board_cards = (0, 3))
    print_actions('turn', hand, board_cards = (3, 4))
    print_actions('river', hand, board_cards = (4, 5))

    if wait_between_sections:
        print(f'')
        input(f'Press ENTER to continue ')
        print(f'-------------------------')
    else:
        print()

def print_hand_short(hand):
    if 'error' in hand: error_suffix = f'not analysable ({hand["error"]})'
    else: error_suffix = 'Analysable'

    cards = format_cards(hand["players"]["Hero"]["hole_cards"])
    print(f'{hand["id"]} - {cards} - {hand["date"]} - {error_suffix}')

def print_position(position_key, hand):
    position = hand[position_key]
    player_id = position['player_id']
    player = hand['players'][player_id]
    hole_cards = player.get('hole_cards', [])

    hero_suffix = ' Hero' if player_id == 'Hero' else ''
    hole_cards_suffix = f' {format_cards(hole_cards)}' if hole_cards else ''

    print(f'  {position_key.upper()}{hero_suffix}{hole_cards_suffix}')
    print_position_chart(position)

def print_position_chart(position):
    if position["chart"]:
        print(f'    {position["action_description"]} ({position["chart"]["label"]})')
    else:
        print(f'    {position["action_description"]}')

    for line in format_range_wrapped(position['range'], indent='      ', width=79):
        print(line)

def print_call_and_raise_range(search_term):
    chart_inputs = parse_range_search_term(search_term)
    positions = calculate_positions(chart_inputs)
    print(f'  OOP')
    print_position_chart(positions['oop'])
    print(f'  IP')
    print_position_chart(positions['ip'])

def parse_range_search_term(search_term):
    seats = re.split(r'\s+', search_term.upper())[1:]
    if len(seats) < 2:
        raise InvalidSearchException('Need at least 2 seats to print ranges')

    valid_seats = list(SEAT_NUM_TO_SEAT.values())
    for seat in seats:
        if seat not in valid_seats:
            valid_seats_lower = [vs.lower() for vs in valid_seats]
            raise InvalidSearchException('Seats must be one of: ' + ', '.join(valid_seats_lower))

    call_seat = seats[0]
    call_vs_seats = seats[1:]
    raise_seat = seats[1]
    raise_vs_seats = seats[2:]

    if 'ANY' in [call_seat, raise_seat]:
        raise InvalidSearchException('First two seats cannot be `any`')
    
    return {
        'raise': {
            'seat': raise_seat,
            'vs_raisers': raise_vs_seats
        },
        'call': {
            'seat': call_seat,
            'vs_raisers': call_vs_seats
        }
    }

def format_range_wrapped(range, indent, width):
    if range is None: return [indent + 'Missing chart']
    if len(range) == 0: return [indent + 'No hands in range']

    lines = [indent]
    for i, card in enumerate(range):
        if len(lines[-1]) + len(card) >= width:
            lines.append(indent)
        comma = ',' if i < len(range) - 1 else ''
        lines[-1] = lines[-1] + card + comma
    return lines

def format_cards(cards, with_border=True, sort=True):
    cards = list(cards)
    if sort:
        cards.sort(key=card_id_from_str)
        cards.reverse()
    joined = ' '.join(cards)
    if not with_border: return joined
    return f'[{joined}]'

def card_id(rank, suit):
    return 4 * rank + suit;

def card_id_from_str(card_str):
    pattern = f'^([${"".join(RANKS)}])([${"".join(SUIT_LETTERS)}])$'
    match = re.match(pattern, card_str, re.I)
    if not match: return None

    rank = RANKS.index(match[1].upper())
    suit = SUIT_LETTERS.index(match[2].lower())
    return card_id(rank, suit)

def format_position_stacks(position_key, hand):
    player_id = hand[position_key]["player_id"]
    initial_stack = hand["players"][player_id]["initial_stack"]
    new_stack = hand["preflop"]["new_stacks"][player_id]
    return f'{position_key.upper()} ${initial_stack:.2f} -> ${new_stack:.2f} start of flop'

def print_actions(round_key, hand, include_folds=True, include_aggressor=False, board_cards=(0,0)):
    if round_key not in hand: return

    folds_suffix = '' if include_folds else ' (excluding folds)'
    board_suffix = '' if board_cards == (0, 0) else f' {format_cards(hand["board"][board_cards[0]:board_cards[1]], sort=False)}'
    print(f'  {round_key.capitalize()}{folds_suffix}{board_suffix}')

    actions = hand[round_key]['actions']
    for action in actions:
        if not include_folds and action['action'] == 'folds': continue
        player_display = format_player_name(action['player_id'], hand)

        if action['action'] == 'raises':
            _, raise_to = parse('${} to ${}', action['tail'])
            tail = f'to ${raise_to}'
        else:
            tail = action['tail']

        print(f'    {player_display} {action["action"]} {tail}')
    
    if not include_aggressor: return
    print_round_aggressor(round_key, hand)

def get_round_aggressor(round_key, hand):
    actions = hand[round_key]['actions']
    last_aggressor_i = find_index_where(lambda act: act['action'] in ['raises', 'bets'], actions, from_end=True)
    if last_aggressor_i is None: return None

    postflop_seat = get_postflop_seat(actions[last_aggressor_i]['player_id'], hand)
    if postflop_seat is None: return None
    return postflop_seat

def print_round_aggressor(round_key, hand):
    postflop_seat = get_round_aggressor(round_key, hand)
    if not postflop_seat: return
    print(f'  {round_key.capitalize()} aggressor')
    print(f'    {postflop_seat.upper()}')

def gen_desktop_postflop_json(hand):
    preflop_aggressor = get_round_aggressor('preflop', hand)
    object = {
        "oopRange": ','.join(hand['oop']['range'] or ''),
        "ipRange": ','.join(hand['ip']['range'] or ''),
        "config": {
            "board": hand['board'][0:3],
            "startingPot": dollars_to_cents(hand["preflop"]["pot"]),
            "effectiveStack": dollars_to_cents(calculate_effective_stack_size_on_flop(hand)),
            "rakePercent": 5,
            "rakeCap": 0,
            "donkOption": False,
            "oopFlopBet": "50, 75" if preflop_aggressor == 'oop' else "",
            "oopFlopRaise": "60",
            "oopTurnBet": "50, 75",
            "oopTurnRaise": "60",
            "oopTurnDonk": "",
            "oopRiverBet": "50, 75",
            "oopRiverRaise": "60",
            "oopRiverDonk": "",
            "ipFlopBet": "50, 75",
            "ipFlopRaise": "60",
            "ipTurnBet": "50, 75",
            "ipTurnRaise": "60",
            "ipRiverBet": "50, 75",
            "ipRiverRaise": "60",
            "addAllInThreshold": 150,
            "forceAllInThreshold": 20,
            "mergingThreshold": 10,
            "addedLines": "",
            "removedLines": ""
        }
    } 
    return json.dumps(object, indent=2)

def format_player_name(player_id, hand):
    player = hand['players'][player_id]
    seat = player['seat']

    details = []
    if hand['oop']['player_id'] == player_id: details.append('OOP')
    if hand['ip']['player_id'] == player_id: details.append('IP')
    if player_id == 'Hero': details.append('Hero')
    if 'hole_cards' in player: details.append(format_cards(player['hole_cards']))

    if len(details) == 0: return seat

    return f'{seat} ({" ".join(details)})'

def parse_hand_basic(lines):
    segments = split_lines_into_segments(lines)
    basic_hand = parse_basic_header_meta(segments['header'])
    basic_hand['players'] = parse_header_players(segments)
    return basic_hand, segments

def parse_hand(segments, hand):
    hand = {**hand}
    hand['players'] = parse_shown_cards(segments, hand)

    hand['preflop'] = parse_preflop_actions(segments['preflop'], hand)
    hand['preflop'] = {**hand['preflop'], **parse_preflop_bets(segments, hand)}

    hand['board'] = parse_board(segments)
    hand = {**hand, **parse_postflop(segments, hand)}
    
    return hand

def vs_raisers_match(vs_raisers_from_chart, vs_raisers, match_any):
    if len(vs_raisers_from_chart) != len(vs_raisers): return False

    for from_chart, not_from_chart in zip(vs_raisers_from_chart, vs_raisers):
        if from_chart == '<ANY>' and match_any: continue
        if from_chart == not_from_chart: continue
        return False
    return True
    
def format_action_description(seat, vs_raisers, action_key):
    action = 'Call' if action_key == 'call' else format_n_bet(len(vs_raisers) + 2)
    vs_suffix = ' vs '.join(vs_raisers)
    vs_suffix = ''.join(
        f' vs {raiser} {format_n_bet(len(vs_raisers) - i + 1)}'
        for i, raiser in enumerate(vs_raisers)
    )
    return f'{action} as {seat}{vs_suffix}'

def format_n_bet(n):
    if n < 2: raise Exception(f"Invalid n bet: {n}")
    if n == 2: return 'RFI'
    return f'{n}Bet'
    
def find_chart(seat, vs_raisers):
    exact_matches = [
        chart for chart in range_chart.values()
        if chart['seat'] == seat
        and vs_raisers_match(chart['vs_raisers'], vs_raisers, match_any=False)
    ]

    any_matches = [
        chart for chart in range_chart.values()
        if chart['seat'] == seat
        and vs_raisers_match(chart['vs_raisers'], vs_raisers, match_any=True)
    ]

    if len(exact_matches) == 1: return exact_matches[0]
    if len(exact_matches) > 1: raise Exception(f"Somehow got {len(exact_matches)} exact chart matches for {seat}-{vs_raisers}")

    if len(any_matches) == 1: return any_matches[0]
    if len(any_matches) > 1: raise Exception(f"Somehow got {len(any_matches)} any chart matches for {seat}-{vs_raisers}")

    return None

def get_range_from_chart(chart, action_key):
    if not chart: return None

    if action_key == 'raise':
        action_to_suffix = {
            'raise': '',
            'raise_or_fold': ':0.5',
            'raise_or_call': ':0.5',
            'raise_or_call_or_fold': ':0.35'
        }
    elif action_key == 'call':
        action_to_suffix = {
            'call': '',
            'call_or_fold': ':0.5',
            'raise_or_call': ':0.5',
            'raise_or_call_or_fold': ':0.35'
        }
    else:
        raise Exception(f'Action lookup not implemented for `{action_key}`')

    ranges = [
        add_suffixes(chart['actions'][action], suffix)
        for action, suffix in action_to_suffix.items()
    ]
    return sum(ranges, [])

def add_suffixes(cards_str, suffix):
    cards = cards_str.split(',')
    return [card.strip() + suffix for card in cards if card.strip() != '']

def calculate_preflop_actions_for_chart(hand):
    """
    If the hero's last action was a fold:
    - nothing to do as there is no hand to analyse
    Otherwise:
    - find the number of raises
    - find the seat of the last raise
    - find the seat of the call (after last raise)
    - throw if:
      - multipler callers after last raise
      - there are no callers after last raise
      - there are 0 raises (limp ranges not supported)
    """
    validate_hero_played_preflop(hand)

    actions = hand['preflop']['actions']
    last_raise_action_i = find_index_where(lambda act: act['action'] == 'raises', actions, from_end=True)
    if last_raise_action_i is None:
        raise NonAnalyzableHandException("We don't have charts for the player limping")

    raises = [action for action in actions if action['action'] == 'raises']
    final_raise_calls = [ action for action in actions[last_raise_action_i + 1:] if action['action'] == 'calls']

    if len(final_raise_calls) == 0:
        raise NonAnalyzableHandException("There was no preflop caller")
    if len(final_raise_calls) > 1:
        raise NonAnalyzableHandException("Solvers will not support multiway pots")

    return { 'raises': raises, 'call': final_raise_calls[0] }

def validate_hero_played_preflop(hand):
    actions = hand['preflop']['actions']
    last_hero_action_i = find_index_where(lambda act: act['player_id'] == 'Hero', actions, from_end=True)
    if last_hero_action_i is None:
        raise NonAnalyzableHandException("Hero performed no actions")
    if actions[last_hero_action_i]['action'] == 'folds':
        raise NonAnalyzableHandException("Last hero action is a fold")

def calculate_positions_for_hand(hand):
    if 'error' in hand:
        return { 'id': hand['id'], 'error': hand['error'] }
    
    chart_inputs = gen_preflop_chart_inputs(hand)
    return calculate_positions(chart_inputs)

def calculate_positions(chart_inputs):
    raise_chart = find_chart(chart_inputs['raise']['seat'], chart_inputs['raise']['vs_raisers'])
    raise_range = get_range_from_chart(raise_chart, 'raise')

    call_chart = find_chart(chart_inputs['call']['seat'], chart_inputs['call']['vs_raisers'])
    call_range = get_range_from_chart(call_chart, 'call')

    positions = [
        {
            'player_id': chart_inputs['raise'].get('player_id'),
            'seat': chart_inputs['raise']['seat'],
            'action_description': format_action_description(
                chart_inputs['raise']['seat'],
                chart_inputs['raise']['vs_raisers'],
                'raise'
            ),
            'chart': raise_chart,
            'range': raise_range,
            'action': 'raise'
        },
        {
            'player_id': chart_inputs['call'].get('player_id'),
            'seat': chart_inputs['call']['seat'],
            'action_description': format_action_description(
                chart_inputs['call']['seat'],
                chart_inputs['call']['vs_raisers'],
                'call'
            ),
            'chart': call_chart,
            'range': call_range,
            'action': 'call'
        }
    ]
    positions.sort(key=lambda player: POSTFLOP_SEAT_ORDER.index(player['seat']))

    return { 'oop': positions[0], 'ip': positions[1] }

def gen_preflop_chart_inputs(hand):
    last_raise = hand['preflop']['raises'][-1]
    call = hand['preflop']['call']

    return {
        'raise': {
            'seat': last_raise['seat'],
            'vs_raisers': list(reversed([
                action['seat'] for action in hand['preflop']['raises'][:-1]
            ])),
            'player_id': last_raise['player_id'],
        },
        'call': {
            'seat': call['seat'],
            'vs_raisers': list(reversed([
                action['seat'] for action in hand['preflop']['raises']
            ])),
            'player_id': call['player_id'],
        }
    }

def format_nth_preflop_raise(nth_raise):
    if nth_raise < 1: raise f"Invalid nth raise {nth_raise}"
    if nth_raise == 1: return "RFI"
    return f'{nth_raise + 1}bet'

def parse_basic_header_meta(header_lines):
    hand_id, small_blind, big_blind, date_str = parse("Poker Hand {}: Hold'em No Limit (${}/${}) - {}", header_lines[0])

    dt = datetime.strptime(date_str, '%Y/%m/%d %H:%M:%S')

    return {
        "id": hand_id,
        "small_blind": float(small_blind),
        "big_blind": float(big_blind),
        "date": dt,
    }

def parse_header_players(segments):
    players = {}
    seat_lines = [line for line in segments['header'] if line.find('Seat') == 0]
    for line in seat_lines:
        seat_n, player_id, stack_size_str = parse("Seat {:d}: {} (${} in chips)", line)
        seat = SEAT_NUM_TO_SEAT[seat_n]

        players[player_id] = {
            "id": player_id,
            "seat": seat,
            "initial_stack": float(stack_size_str)
        }
    
    players['Hero']['hole_cards'] = parse_hero_cards(segments)

    return players

def parse_preflop_actions(preflop_lines, hand):
    return {
        'actions': parse_actions(preflop_lines, hand)
    }

def parse_preflop_bets(segments, hand):
    # bets the player makes (raising to the latest amount in the list)
    bets_by_player = {player_id: [] for player_id, _ in hand['players'].items()}

    for player_id, blind in parse_blinds(segments['header']):
        bets_by_player[player_id].append(blind)

    for player_id, action, bet in parse_bets(segments['preflop'], hand):
        if action == 'folds': continue
        if action == 'checks': continue
        if action == 'raises': bets_by_player[player_id].append(bet)
        if action == 'calls':
            bets = bets_by_player[player_id]
            last_bet = 0 if len(bets) == 0 else bets[-1]
            bets.append(bet + last_bet)

    pot = sum(bets[-1] for _, bets in bets_by_player.items() if len(bets) > 0)
    return {
        'bets': bets_by_player,
        'new_stacks': calculate_player_stacks(hand, [bets_by_player]),
        'pot': pot
    }

def calculate_effective_stack_size_on_flop(hand):
    oop_id = hand['oop']['player_id']
    ip_id = hand['ip']['player_id']
    stacks = hand['preflop']['new_stacks']
    return min(stacks[oop_id], stacks[ip_id])

def calculate_player_stacks(hand, bets_by_player_list):
    stacks = {
        player_id: player['initial_stack']
        for player_id, player in hand['players'].items()
    }
    for bets_by_player in bets_by_player_list:
        for player_id, bets in bets_by_player.items():
            last_bet = 0 if len(bets) == 0 else bets[-1]
            stacks[player_id] = stacks[player_id] - last_bet
    return stacks

def parse_blinds(lines):
    bets = []
    for line in lines:
        parsed = parse('{}: posts {} blind ${}', line)
        if not parsed: continue
        player_id, _, blind_str = parsed
        bets.append((player_id, float(blind_str)))
    return bets

def parse_bets(lines, hand):
    bets = []
    for action_obj in parse_actions(lines, hand):
        action = action_obj['action']
        player_id = action_obj['player_id']
        tail = action_obj['tail']

        if action == 'folds': continue
        if action == 'checks': continue

        if action == 'raises':
            _, raise_to = parse('${} to ${}', tail)
            raise_to_without_all_in = raise_to.replace(' and is all-in', '')
            bets.append((player_id, action, float(raise_to_without_all_in)))
        
        if action == 'calls':
            call = parse('${}', tail)
            call_without_all_in = call[0].replace(' and is all-in', '')
            bets.append((player_id, action, float(call_without_all_in)))

    return bets

def parse_board(segments):
    if 'river' in segments:
        a, b, c, d, e = parse('*** RIVER *** [{} {} {} {}] [{}]', segments['river'][0])
        return [a, b, c, d, e]
    if 'turn' in segments:
        a, b, c, d = parse('*** TURN *** [{} {} {}] [{}]', segments['turn'][0])
        return [a, b, c, d]
    if 'flop' in segments:
        a, b, c = parse('*** FLOP *** [{} {} {}]', segments['flop'][0])
        return [a, b, c]
    
    return None

def parse_postflop(segments, hand):
    new_hand_fields = {}

    for segment_key in ['flop', 'turn', 'river']:
        if not segment_key in segments: continue
        actions = parse_actions(segments[segment_key], hand)
        new_hand_fields[segment_key] = { 'actions': actions }

    return new_hand_fields

def parse_actions(lines, hand):
    actions = []
    for line in lines:
        if line.startswith('***'): continue
        if line.startswith('Uncalled bet'): continue
        if parse('{} collected ${} from pot', line): continue
        actions.append(parse_action(line, hand))
    return actions

def parse_action(line, hand):
    player_id, full_action = parse('{}: {}', line)

    if full_action in ['folds', 'checks']:
        tail = ''
        action = full_action
    else:
        action, tail = parse('{} {}', full_action)

    seat = hand['players'][player_id]['seat']
    return {
        'player_id': player_id,
        'action': action,
        'seat': seat,
        'tail': tail
    }

def find_index_where(func, iterable, from_end=False):
    with_index = reversed(list(enumerate(iterable))) if from_end else enumerate(iterable)
    for i, line in with_index:
        if func(line): return i
    return None

def split_lines_into_segments(hand_lines):
    header_i = find_index_where(matches_format('Poker Hand #{}'), hand_lines)
    preflop_i = find_index_where(matches_format('*** HOLE CARDS ***'), hand_lines)
    flop_i = find_index_where(matches_format('*** FLOP *** [{}]'), hand_lines)
    # GGPoker calls the end of the hand showdown, not the actual reveal of cards
    showdown_i = find_index_where(matches_format('*** SHOWDOWN ***'), hand_lines)
    summary_i = find_index_where(matches_format('*** SUMMARY ***'), hand_lines)

    preflop_full = hand_lines[preflop_i:(flop_i or showdown_i)]
    preflop_actions =  [line for line in preflop_full if not line.startswith('Dealt to')]

    postflop = hand_lines[flop_i:summary_i] if flop_i else None

    segments = {
        'header': hand_lines[header_i:preflop_i],
        'preflop_full': preflop_full,
        'preflop': preflop_actions,
        'showdown': hand_lines[showdown_i:summary_i],
        'summary': hand_lines[summary_i:]
    }

    if not postflop:
        return segments

    segments['postflop'] = postflop
    return { **segments, **split_postflop_lines(postflop)}

def split_postflop_lines(lines):
    flop_i = find_index_where(matches_format('*** FLOP *** [{}]'), lines)
    turn_i = find_index_where(matches_format('*** TURN *** [{}] [{}]'), lines)
    river_i = find_index_where(matches_format('*** RIVER *** [{}] [{}]'), lines)
    
    sections = {}
    
    if flop_i is not None:
        sections['flop'] = lines[flop_i:turn_i] if turn_i else lines[flop_i:]
    if turn_i:
        sections['turn'] = lines[turn_i:river_i] if river_i else lines[turn_i:]
    if river_i:
        sections['river'] = lines[river_i:]

    return sections

def matches_format(format):
    return lambda i: bool(parse(format, i))

def parse_hero_cards(segments):
    lines = segments.get('preflop_full', [])
    line_i = find_index_where(matches_format('Dealt to Hero {}'), lines)
    cards = parse('Dealt to Hero [{}]', lines[line_i])
    return cards[0].split(' ')

def parse_shown_cards(segments, hand):
    shows = [
        parse('{}: shows [{}', line)
        for line in segments.get('postflop', [])
        if line.find('shows') != -1
    ]

    players = {id: {**player} for id, player in hand['players'].items()}
    for player_id, cards_str in shows:
        if player_id == 'Hero': continue
        cards = cards_str.split(']')[0].split(' ')
        players[player_id]['hole_cards'] = cards

    return players

def dollars_to_cents(dollars, should_round=True):
    cents = 100 * dollars
    if should_round: return int(round(cents))
    return cents

if __name__ == '__main__':
    main()