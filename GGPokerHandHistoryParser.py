"""
# Setup 
You will have to run PreflopChartsExtractor.py to produce the charts JSON. See that file for docs

# Deps
pip3 install parse

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
from pathlib import Path

from parse import *

SEAT_NUM_TO_SEAT = {
    1: 'BTN',
    2: 'SB',
    3: 'BB',
    4: 'LJ',
    5: 'HJ',
    6: 'CO',
}
POSTFLOP_SEAT_ORDER = ['SB', 'BB', 'LJ', 'HJ', 'CO', 'BTN']
DOWNLOADS_DIR = Path(Path.home(), Path('Downloads'))
CONTENTS_DIR = Path(DOWNLOADS_DIR, Path('GG'))
LOG_FILE_PATH = Path(CONTENTS_DIR, Path('history.txt'))

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
    print(f'Download your GGPoker hand histories into your `{DOWNLOADS_DIR}` directory')
    print(f'You can then run the `extract` command to decompress them')

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

    print('Enter command, e.g.: ')
    print('- `#RC1800277957` - show hand with the given hand ID (requires extraction) ')
    print('- `e` - extract to extract the data from PokerCraft zip')
    print('- `l` - repeat the last search')
    print('- `h` - show search history')
    print('- `a` - show all hands')
    search_term = input('>>> ').strip()
    search_term = reformat_search_term(search_term)

    if search_term == 'h':
        print_history()
        return search_term, []
    if search_term.find('range ') == 0:
        print_range(search_term)
        return search_term, []
        # TODO hero <pattern> <pattern> search is deprecated
        # TODO range command we may not keep
    if search_term == 'e':
        extract_downloads()
        return search_term, []

    file_glob = str(Path(CONTENTS_DIR, Path("GG20*.txt")))
    files = glob.glob(file_glob)
    files.sort()

    # TODO could become a memory issue with a lot of hands
    matches = []

    for file in files:
        lazy_hands = load_hands_from_file(file)

        for lazy_hand in lazy_hands:
            if not hand_matches_search(lazy_hand, search_term): continue

            hand = lazy_hand['parse']()
            matches.append(hand)

            if is_hero_hand_search(search_term):
                print_hand_short(hand)
                continue

            if 'error' in hand:
                print_hand_error(hand)
                continue

            print_hand(hand)
    
    print()
    for line in format_result_count(search_term, matches):
        print(line)
    return search_term, matches

def extract_downloads():
    file_paths = os.listdir(DOWNLOADS_DIR)

    pattern = UUID_REGEX.replace('$', '.zip$')
    zip_paths = [
        Path(Path(DOWNLOADS_DIR), Path(path))
        for path in file_paths
        if re.match(pattern, path)
    ]
    zip_paths.sort(key=lambda path: os.path.getmtime(path))

    extracted_files = []
    for path in zip_paths:
        with zipfile.ZipFile(path, 'r') as zip:
            files = [
                file for file in zip.namelist()
                if re.match(r'^GG20.*\.txt$', file)
            ]
            extracted_files.extend(files)
            zip.extractall(CONTENTS_DIR, files)
    
    print(f'{len(extracted_files)} files extracted from {len(zip_paths)} zips')

def print_range(search_term):
    raise Exception("Range selection not implemented yet")
    # TODO LATER allow convenient formatgg for search?
    term = parse('range {}', search_term)
    raise_range = get_range(term[0], 'raise')
    call_range = get_range(term[0], 'call')

    print(term[0])
    if raise_range == 'MissingChart' and call_range == 'MissingChart':
        print('  No range found')
        return
    
    print(f'  Raise')
    print(f'    {raise_range}')
    print(f'  Call')
    print(f'    {call_range}')

def is_hero_hand_search(search_term):
    return search_term.lower().find('hero ') == 0

def hand_matches_search(lazy_hand, search_term):
    if search_term == 'a': return True
    if is_hero_hand_search(search_term):
        return matches_hero_hole_card_search(lazy_hand, search_term)
    if lazy_hand["id"] == search_term: return True

    return False

def validate_hole_card_search(search_term, with_hero_prefix=True):
    search_term = search_term.lower()
    valid_cards = 'x23456789tjqka'
    valid_suits = 'xcdhs'
    hero_prefix = 'hero\s+' if with_hero_prefix else ''

    pattern = rf'^{hero_prefix}([{valid_cards}][{valid_suits}])\s+([{valid_cards}][{valid_suits}])$'
    return re.compile(pattern).match(search_term)

def matches_hero_hole_card_search(lazy_hand, search_term):
    match = validate_hole_card_search(search_term)
    pattern_a = card_pattern_to_regex(match.group(1))
    pattern_b = card_pattern_to_regex(match.group(2))
    [card_a, card_b] = lazy_hand['players']['Hero']['hole_cards']

    if pattern_a.match(card_a) and pattern_b.match(card_b): return True
    if pattern_b.match(card_a) and pattern_a.match(card_b): return True
    return False

def card_pattern_to_regex(pattern):
    return re.compile(pattern.capitalize().replace('x', '.'))

def reformat_search_term(search_term):
    if search_term in ['h', 'e', 'a']: return search_term

    if search_term == 'l':
        last_term = last_search_term() or ''
        print(f'Searching for: `{last_term}`')
        return last_term.strip()

    if search_term.startswith('RC'):
        search_term = '#' + search_term

    if search_term.startswith('#RC'):
        if not re.match(r'^#RC\d{7,13}$', search_term):
            raise InvalidSearchException(f'Invalid hand ID `{search_term}`')
        return search_term
    
    if search_term.startswith('hero'):
        if not validate_hole_card_search(search_term):
            raise InvalidSearchException(f'Invalid hero hole card search: {search_term}')

    if validate_hole_card_search(search_term, with_hero_prefix=False):
        raise InvalidSearchException(f'Prefix the card search with `hero`. E.g., {search_term}')

    raise InvalidSearchException(f'Unknown command {search_term}')

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
    if search_term in ['l', 'h', 'a', 'e']: return []
    if search_term.find('range ') == 0: return []
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
    counts = f'{len(match_cards)} analysable{non_analysable_suffix}'

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

        positions = calculate_positions(full_hand)
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

def print_hand(hand):
    print()
    print_hand_title(hand)
    print_position('oop', hand)
    print_position('ip', hand)
    print(f'  Board')
    print(f'    [{" ".join(hand.get("board", []))}]')
    print(f'  Starting Pot')
    print(f'    ${hand["preflop"]["pot"]:.2f}')
    print(f'  Effective Stack')
    print(f'    ${calculate_effective_stack_size_on_flop(hand):.2f}')
    print_actions('preflop', hand, include_folds=False, include_aggressor=True)
    print(f'  -------------------------')
    print_actions('flop', hand, board_cards = (0, 3))
    print_actions('turn', hand, board_cards = (3, 4))
    print_actions('river', hand, board_cards = (4, 5))
    print()

def print_hand_short(hand):
    if 'error' in hand: error_suffix = f'Not analysable ({hand["error"]})'
    else: error_suffix = 'Analysable'

    cards = format_cards(hand["players"]["Hero"]["hole_cards"])
    print(f'{hand["id"]} - {cards} - {hand["date"]} - {error_suffix}')

def print_position(position_key, hand):
    position = hand[position_key]
    player_id = position['player_id']
    player = hand['players'][player_id]
    hole_cards = format_cards(player.get('hole_cards', []))

    hero_suffix = ' Hero' if player_id == 'Hero' else ''
    hole_cards_suffix = f' {hole_cards}' if hole_cards else ''

    print(f'  {position_key.upper()}{hero_suffix}{hole_cards_suffix}')
    if position["chart"]:
        print(f'    {position["action_description"]} ({position["chart"]["label"]})')
    else:
        print(f'    {position["action_description"]}')
    print(f'      {position["range"]}')

def format_cards(cards, with_border=True):
    joined = ' '.join(cards)
    if not with_border: return joined
    return f'[{joined}]'

def format_position_stacks(position_key, hand):
    player_id = hand[position_key]["player_id"]
    initial_stack = hand["players"][player_id]["initial_stack"]
    new_stack = hand["preflop"]["new_stacks"][player_id]
    return f'{position_key.upper()} ${initial_stack:.2f} -> ${new_stack:.2f} start of flop'

def print_actions(round_key, hand, include_folds=True, include_aggressor=False, board_cards=(0,0)):
    if round_key not in hand: return

    folds_suffix = '' if include_folds else ' (excluding folds)'
    board_suffix = '' if board_cards == (0, 0) else f' {format_cards(hand["board"][board_cards[0]:board_cards[1]])}'
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
    last_aggressor_i = find_index_where(lambda act: act['action'] in ['raises', 'bets'], actions, from_end=True)
    if last_aggressor_i is None: return
    postflop_seat = get_postflop_seat(actions[last_aggressor_i]['player_id'], hand)
    if postflop_seat is None: return
    print(f'  {round_key.capitalize()} aggressor')
    print(f'    {postflop_seat.upper()}')

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
    
def format_position_action_description(seat, vs_raisers, action_key):
    vs_suffix = ' vs '.join(vs_raisers)
    vs_suffix = ''.join(f' vs {raiser} raise' for raiser in vs_raisers)
    return f'{action_key.capitalize()} as {seat}{vs_suffix}'
    
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
    if not chart: return '<MISSING_CHART>'

    if action_key == 'raise':
        action_keys = ['raise', 'raise_or_fold', 'raise_or_call', 'raise_or_call_or_fold']
    elif action_key == 'call':
        action_keys = ['call', 'call_or_fold', 'raise_or_call', 'raise_or_call_or_fold']
    else:
        raise Exception(f'Action lookup not implemented for `{action_key}`')

    ranges = [
        range for key, range in chart['actions'].items()
        if key in action_keys and range != ''
    ]
    joined_ranges = ','.join(ranges)

    if joined_ranges == '': return 'Empty Range'
    return joined_ranges

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

def calculate_positions(hand):
    if 'error' in hand:
        return { 'id': hand['id'], 'error': hand['error'] }
    
    chart_inputs = gen_preflop_chart_inputs(hand)

    raise_chart = find_chart(chart_inputs['raise']['seat'], chart_inputs['raise']['vs_raisers'])
    raise_range = get_range_from_chart(raise_chart, 'raise')

    call_chart = find_chart(chart_inputs['call']['seat'], chart_inputs['call']['vs_raisers'])
    call_range = get_range_from_chart(call_chart, 'call')

    positions = [
        {
            'player_id': chart_inputs['raise']['player_id'],
            'seat': chart_inputs['raise']['seat'],
            'action_description': format_position_action_description(chart_inputs['raise']['seat'], chart_inputs['raise']['vs_raisers'], 'raise'),
            'chart': raise_chart,
            'range': raise_range,
            'action': 'raise'
        },
        {
            'player_id': chart_inputs['call']['player_id'],
            'seat': chart_inputs['call']['seat'],
            'action_description': format_position_action_description(chart_inputs['call']['seat'], chart_inputs['call']['vs_raisers'], 'call'),
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

    return {
        "id": hand_id,
        "small_blind": float(small_blind),
        "big_blind": float(big_blind),
        "date": date_str,
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
        cards = cards_str.split(']')[0].split(' ')
        players[player_id]['hole_cards'] = cards

    return players

if __name__ == '__main__':
    main()