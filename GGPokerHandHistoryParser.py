import glob
import sys
import traceback
import json
import re
from pathlib import Path

# pip3 install parse
from parse import *

# pip3 install pyinstaller
# pyinstaller.exe GGPokerHandHistoryParser.py -y --add-data 'PreflopChartExtractions/PreflopCharts.json;data'

SEAT_NUM_TO_SEAT = {
    1: 'BTN',
    2: 'SB',
    3: 'BB',
    4: 'LJ',
    5: 'HJ',
    6: 'CO',
}
POSTFLOP_SEAT_ORDER = ['SB', 'BB', 'LJ', 'HJ', 'CO', 'BTN']
CONTENTS_DIR = Path(Path.home(), Path('Downloads'), Path('GG'))
LOG_FILE_PATH = Path(CONTENTS_DIR, Path('history.txt'))

CHART_FILE = Path('PreflopChartExtractions/PreflopCharts.json')
print('reading file')
with open(CHART_FILE) as f:
    json.load(f.read)

# Yoinked from here and modified https://github.com/brianfordcode/poker-preflop-charts/blob/ef0e24e41fac6b0ede50569faf504e4b36aaaa98/src/components/chart.vue#L62C1-L62C1
# These appear to be based on Jonothan Little's charts https://poker-coaching.s3.amazonaws.com/tools/preflop-charts/full-preflop-charts.pdf
RANGE_CHART = {
    "LJ RFI": {
        "raise": "AA AKs AQs AJs ATs A9s A8s A7s A6s A5s A4s A3s A2s AKo KK KQs KJs KTs K9s K8s AQo KQo QQ QJs QTs Q9s AJo KJo QJo JJ JTs J9s ATo TT T9s 99 88 77 66",
    },
    "HJ RFI": {
        "raise": "AA AKs AQs AJs ATs A9s A8s A7s A6s A5s A4s A3s A2s AKo KK KQs KJs KTs K9s K8s K7s K6s AQo KQo QQ QJs QTs Q9s Q8s AJo KJo QJo JJ JTs J9s ATo KTo QTo TT T9s 99 98s 88 87s 77 76s 66 55"
    },
    "CO RFI": {
        "raise": "AA AKs AQs AJs ATs A9s A8s A7s A6s A5s A4s A3s A2s AKo KK KQs KJs KTs K9s K8s K7s K6s K5s K4s K3s AQo KQo QQ QJs QTs Q9s Q8s Q7s Q6s AJo KJo QJo JJ JTs J9s J8s ATo KTo QTo JTo TT T9s T8s T7s A9o 99 98s 97s A8o 88 87s 77 76s 66 55 44 33",
    },
    "BTN RFI": {
        "raise": "AA AKs AQs AJs ATs A9s A8s A7s A6s A5s A4s A3s A2s AKo KK KQs KJs KTs K9s K8s K7s K6s K5s K4s K3s K2s AQo KQo QQ QJs QTs Q9s Q8s Q7s Q6s Q5s Q4s Q3s AJo KJo QJo JJ JTs J9s J8s J7s J6s J5s J4s ATo KTo QTo JTo TT T9s T8s T7s T6s A9o K9o Q9o J9o T9o 99 98s 97s 96s A8o K8o T8o 98o 88 87s 86s 85s A7o 77 76s 75s A6o 66 65s 64s A5o 55 54s 53s A4o 44 33 22",
    },
    "SB RFI": {
        "raise": "22+,A2+,K2+,Q2+,J2s+,J5o+,T2s+,T5o+,92s+,95o+,82s+,85o+,72s+,75o+,62s+,64o+,52s+,54o,42s+,43o,32s"
    },
    "LJ vs HJ 3bet": {
        "raise": "AA AKs AKo KK QQ" + " A9s A8s A5s A4s A3s A2s KQo AJo",
        "call": "AQs AJs ATs KQs KJs KTs AQo QJs QTs JJ JTs TT T9s 99 98s 88 77",
    },
    "LJ vs CO 3bet": {
        "raise": "AA AKs AKo KK QQ JJ" + " A9s A8s A5s A4s A3s A2s KQo AJo",
        "call": "AQs AJs ATs KQs KJs KTs AQo QJs QTs JTs TT T9s 99 98s 88 77 66",
    },
    "LJ vs BTN 3bet": {
        "raise": "AA AKs AKo KK QQ JJ" + " A9s A8s A7s A5s A5s A4s A3s A2s KQo AJo 76s",
        "call": "AQs AJs ATs KQs KJs KTs AQo QJs QTs JTs TT T9s 99 98s 88 87s 77 66 55",
    },
    "LJ vs SB 3bet": {
        "raise": "AA AKs AKo KK QQ JJ" + " A9s A8s A7s A6s A5s A4s A3s A2s ATo KJo",
        "call": "AQs AJs ATs KQs KJs KTs AQo KQo QJs QTs AJo JTs J9s TT T9s 99 98s 88 87s 77 76s 66 55",
    },
    "LJ vs BB 3bet": {
        "raise": "AA AKs AKo KK QQ JJ" + " A9s A8s A7s A6s A5s A4s A3s A2s AJo KQo",
        "call": "AQs AJs ATs KQs KJs KTs AQo QJs QTs JTs TT T9s 99 98s 88 87s 77 76s 66 55 44",
    },
    "HJ vs LJ RFI": {
        "raise": "AA AKs AQs AJs ATs A5s AKo KK KQs KJs KTs AQo KQo QQ QJs JJ TT 99",
        "call": "TODO" # TODO add call stuff
    },
    "HJ vs CO 3bet": {
        "raise": "AA AKs AKo KK QQ JJ" + " A9s A8s A7s A6s A5s A4s A3s A2s KJo ATo 76s",
        "call": "AQs AJs ATs KQs KJs KTs K9s AQo KQo QJs QTs Q9s AJo JTs J9s TT T9s 99 98s 88 87s 77 66 55",
        "fold": "K8s QJo T8s 97s 65s 54s 44 33 22"
    },
    "HJ vs BTN 3bet": {
        "raise": "AA AKs AKo KK QQ JJ" + " A9s A8s A7s A6s A5s A4s A3s A2s KJo ATo 76s 65s 54s",
        "call": "AQs AJs ATs KQs KJs KTs K9s AQo KQo QJs QTs Q9s AJo JTs J9s TT T9s 99 98s 88 87s 77 66 55 44",
    },
    "HJ vs SB 3bet": {
        "raise": "AA AKs AKo KK QQ JJ" + " A9s A8s A7s A6s A5s A4s A3s A2s KJo ATo",
        "call": "AQs AJs ATs KQs KJs KTs K9s AQo KQo QJs QTs Q9s AJo JTs J9s TT T9s 99 98s 88 87s 77 76s 66 55 44",
    },
    "HJ vs BB 3bet": {
        "raise": "AA AKs AKo KK QQ JJ" + " A9s A8s A7s A6s A5s A4s A3s A2s KQo AJo",
        "call": "AQs AJs ATs KQs KJs KTs AQo QJs QTs JTs TT T9s 99 98s 88 87s 77 76s 66 55 44",
    },
    "CO vs LJ RFI": {
        "raise": "AA AKs AQs AJs ATs A5s AKo KK KQs KJs KTs AQo KQo QQ QJs JJ TT 99 88",
        "call": "TODO" # TODO add call stuff
    },
    "CO vs HJ RFI": {
        "raise": "AA AKs AQs AJs ATs A9s A5s A4s AKo KK KQs KJs KTs AQo KQo QQ QJs AJo JJ TT 99 88",
        "call": "TODO" # TODO add call stuff
    },
    "CO vs BTN 3bet": {
        "raise": "AA AKs AKo KK QQ JJ TT" + " A8s A7s A6s A4s A3s A2s KJo ATo 97s 86s 75s 54s",
        "call": "AQs AJs ATs A9s A5s KQs KJs KTs K9s AQo KQo QJs QTs Q9s AJo JTs J9s T9s T8s 99 98s 88 87s 77 76s 66 65s 55 44",
    },
    "CO vs SB 3bet": {
        "raise": "AA AKs AKo KK QQ JJ TT" + " A8s A7s A6s A4s A3s A2s KJo ATo 97s 86s 75s 54s",
        "call": "AQs AJs ATs A9s A5s KQs KJs KTs K9s AQo KQo QJs QTs Q9s AJo JTs J9s T9s T8s 99 98s 88 87s 77 76s 66 65s 55 44",
    },
    "CO vs BB 3bet": {
        "raise": "AA AKs AKo KK QQ JJ TT" + " A8s A4s A3s A2s KJo ATo T8s 97s 65s 54s",
        "call": "AQs AJs ATs A9s A5s KQs KJs KTs K9s AQo KQo QJs QTs Q9s AJo JTs J9s T9s 99 98s 88 87s 77 76s 66 55 44",
    },
    "BTN vs LJ RFI": {
        "raise": "AA AKs AQs A9s A8s A4s A3s AKo KK K9s KQo QQ QJs AJo JJ T9s",
        "call": "AJs ATs A5s KQs KJs KTs AQo QTs JTs TT 99 88 77 76s 66 65s 55 54s"
    },
    "BTN vs HJ RFI": {
        "raise": "AA AKs AQs A9s A8s A7s A4s A3s AKo KK KTs K9s K8s KQo QQ QTs Q9s AJo JJ T9s 66",
        "call": "AJs ATs A5s KQs KJs AQo QJs JTs TT 99 98s 88 87s 77 55 44"
    },
    "BTN vs CO RFI": {
        "raise": "AA AKs AQs A8s A7s A6s A4s A3s AKo KK KQs K9s KQo QQ QJs Q9s AJo KJo QJo JJ JTs J9s ATo TT 55",
        "call": "AJs ATs A9s A5s KJs KTs AQo QTs T9s 99 98s 88 77 66"
    },
    "BTN vs SB 3bet": {
        "raise": "AA AKs AQs AJs AKo KK AQo QQ JJ TT 99" + " K6s K5s K4s Q7s J7s QTo JTo K9o A8o 86s 75s 64s A5o 54s A4o 43s A3o",
        "call": "ATs A9s A8s A7s A6s A5s A4s A3s A2s KQs KJs KTs K9s K8s K7s KQo QJs QTs Q9s Q8s AJo KJo QJo JTs J9s J8s ATo KTo T9s T8s T7s A9o 98s 97s 88 87s 77 76s 66 65s 55 44 33 22",
    },
    "BTN vs BB 3bet": {
        "raise": "AA AKs AQs AJs AKo KK AQo QQ JJ TT 99" + " K6s K5s K4s Q7s J7s QTo JTo K9o A8o 86s 75s 64s A5o 54s A4o 43s A3o",
        "call": "ATs A9s A8s A7s A6s A5s A4s A3s A2s KQs KJs KTs K9s K8s K7s KQo QJs QTs Q9s Q8s AJo KJo QJo JTs J9s J8s ATo KTo T9s T8s T7s A9o 98s 97s 88 87s 77 76s 66 65s 55 44 33 22",
    },
    "SB vs LJ RFI": {
        "raise": "AA AKs AQs AJs ATs A5s AKo KK KQs KJs KTs AQo QQ QJs JJ TT 99",
        "call": "AJs ATs KQs KJs KTs AQo QJs QTs JJ JTs TT T9s 99 98s 88 66 55"
    },
    "SB vs HJ RFI": {
        "raise": "AA AKs AQs AJs ATs A5s AKo KK KQs KJs KTs AQo QQ QJs QTs JJ JTs TT 99 88 77",
        "call": "TODO" # TODO add call stuff
    },
    "SB vs CO RFI": {
        "raise": "AA AKs AQs AJs ATs A9s A5s AKo KK KQs KJs KTs AQo KQo QQ QJs QTs AQo KQo QQ QJs QTs JJ JTs J9s TT T9s 99 88 77 66",
        "call": ""
    },
    "SB vs BTN RFI": {
        "raise": "AA AKs AQs AJs ATs A9s A8s A7s A5s A4s AKo KK KQs KJs KTs K9s AQo KQo QQ QJs QTs Q9s AJo KJo JJ JTs J9s TT T9s T8s 99 88 77 66 55",
        "call": ""
    },
    "SB RFI vs BB 3bet": {
        "raise": "AA AKs AQs AJs AKo KK AQo QQ JJ" + " J4s Q5o Q4o K3o K2o ",
        "call": "ATs KQs KJs KQo QJs AJo KJo ATo TT 99 95s 88 85s 74s 43s",
    },
    "SB vs BB RFI": {
        # TODO SB stuff
    },
    "BB vs LJ RFI": {
        "raise": "AA AKs AQs A5s A4s AKo KK KQs KJs QQ QJs JJ JTs 65s 54s",
        "call": "AJs ATs A9s A8s A7s A6s A3s A2s KTs K9s K8s K7s K6s K5s K4s K3s K2s AQo KQo QTs Q9s Q8s Q7s Q6s Q5s AJo KJo QJo J9s J8s ATo JTo TT T9s T8s T7s 99 98s 97s 96s 88 87s 86s 85s 77 76s 75s 74s 66 64s 63s 55 53s 44 43s 33 32s 22" 
    },
    "BB vs HJ RFI": {
        "raise": "AA AKs AQs A9s A5s A4s AKo KK KQs KJs KTs K5s QQ QJs QTs JJ JTs TT 65s 54s",
        "call": "AJs ATs A8s A7s A6s A3s A2s K9s K8s K7s K6s K4s K3s K2s AQo KQo Q9s Q8s Q7s Q6s Q5s AJo KJo QJo J9s J8s J7s ATo KTo QTo JTo T9s T8s T7s A9o 99 98s 97s 96s 88 87s 86s 85s 77 76s 75s 74s 66 64s 63s 55 53s 44 43s 33 22" 
    },
    "BB vs CO RFI": {
        "raise": "AA AKs AQs AJs A9s A5s A4s AKo KK KQs KJs KTs AQo QQ QJs QTs Q9s JJ JTs J9s TT T9s 99 65s 54s",
        "call": "ATs A8s A7s A6s A3s A2s K9s K8s K7s K6s K5s K4s K3s K2s KQo Q8s Q7s Q6s Q5s Q4s Q3s AJo KJo QJo J8s J7s J6s ATo KTo QTo JTo T8s T7s A9o T9o 98s 97s 96s A8o 88 87s 86s 85s 77 76s 75s 74s 66 64s 63s A5o 55 53s 52s 44 43s 33 22" 
    },
    "BB vs BTN RFI": {
        "raise": "AA AKs AQs AJs ATs A6s A5s A4s AKo KKs KQs KJs KTs K9s AQo KQo QQ QJs QTs Q9s JJ JTs J9s J8s TT T9s T8s 99 98s 97s 88 87s 76s 65s 54s",
        "call": "A9s A8s A7s A3s A2s K8s K7s K6s K5s K4s K3s K2s Q8s Q7s Q6s Q5s Q4s Q3s Q2s AJo KJo QJo J7s J6s J5s J4s J3s J2s ATo KTo QTo JTo T7s T6s T5s T4s T3s T2s A9o K9o Q9o J9o T9o 96s 95s 94s A8o K8o Q8o J8o T8o 98o 86s 85s 84s A7o K7o 87o 77 75s 74s 73s A6o K6o 76o 66 64s 63s 62s A5o 65o 55 53s 52s A4o 54o 44 43s 42s 33 32s 22"  
    },
    "BB vs SB RFI": {
        # TODO raise
        "call": "88-22,A8s-A2s,ATo-A2o,K8s-K2s,KJo-K4o,Q8s-Q2s,Q5o+,J7s-J2s,J7o+,T6s-T2s,T7o+,95s-92s,97o+,83s-82s,87o,73s-72s,76o,62s,65o,52s,42s,32s"
    },
    "BB vs SB Raise": {
        "raise": "AA AKs AQs AJs ATs A5s A4s AKo KK KQs KJs KTs AQo QQ QJs JJ J5s TT T5s 99 95s J8o 88 87s J7o T7o 76s A6o K6o Q6o 65s K5o 54s",
        "call": "A9s A8s A7s A6s A3s A2s K9s K8s K7s K6s K5s K4s K3s K2s KQo QTs Q9s Q8s Q7s Q6s Q5s Q4s Q3s Q2s AJo KJo QJo JTs J9s J8s J7s J6s J4s J3s J2s ATo KTo QTo JTo T9s T8s T7s T6s T4s T3s T2s A9o K9o Q9o J9o T9o 98s 97s 96s 96s 94s 93s 92s A8o K8o Q8o T8o 98o 86s 85s 84s A7o K7o Q7o 97o 87o 77 75s 74s 73s 86o 76o 66 64s 63s 62s A5o 65o 55 53s 52s A4o 54o 44 43s 42s A3o 33 32s A2o"  
    },
}

class NonAnalyzableHandException(Exception):
    "Raised when the hand can't be analysed, e.g., the player folds preflop, or nobody calls the player's open raise"
    pass
class InvalidHoleCardSearchException(Exception):
    pass

def main():
    print(f'Please extract all your GG hand history .txt files directly into your `{CONTENTS_DIR}` directory (create it if it doesn\'t exist).')
    print(f'(You don\'t have to restart this app when you add new files)')

    while True:
        try:
            print()
            save_to_history_file(*main_loop())
        except InvalidHoleCardSearchException as e:
            print(e)
        except Exception as e:
            print('-----------------------------------')
            print('*** An unexpected error has occurred. Please send Dylan the following contents: ***')
            traceback.print_exc()
            print('-----------------------------------')

def main_loop():
    # TODO hero <pattern> <pattern> search is deprecated
    search_term = input('Enter hand ID (e.g., `#RC1800277957`), `all`, `last`, `history`, `hero T8 H8`, `hero Ah xx`, `range LJ vs BB 3bet`: ').strip()
    search_term = reformat_search_term(search_term)

    if search_term == 'history':
        print_history()
        return search_term, []
    if search_term.find('range ') == 0:
        print_range(search_term)
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

def print_range(search_term):
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
    if search_term == 'all': return True
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
    if search_term == 'last':
        last_term = last_search_term() or ''
        print(f'Searching for: {last_term}')
        return last_term.strip()

    if search_term.startswith('RC'):
        search_term = '#' + search_term
    
    if search_term.startswith('hero'):
        if not validate_hole_card_search(search_term):
            raise InvalidHoleCardSearchException(f'Invalid hero hole card search: {search_term}')

    if validate_hole_card_search(search_term, with_hero_prefix=False):
        raise InvalidHoleCardSearchException(f'Prefix the card search with `hero`. E.g., {search_term}')

    return search_term

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
    if search_term in ['last', 'history', 'all']: return []
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
    print(f'    {position["action"].capitalize()} as {position["chart_key"]}')
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
    
def get_range(base_range_key, action_key):
    base = RANGE_CHART.get(base_range_key, {})
    range = base.get(action_key, 'Missing Chart')
    if range == 'Missing Chart': return 'Missing Chart'
    if range == '': return 'Empty Range'
    return range.replace(' ', ',')

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

    positions = [
        {
            'player_id': chart_inputs['raise']['player_id'],
            'seat': chart_inputs['raise']['seat'],
            'chart_key': chart_inputs['raise']['key'],
            'range': get_range(chart_inputs['raise']['key'], 'raise'),
            'action': 'raise'
        },
        {
            'player_id': chart_inputs['call']['player_id'],
            'seat': chart_inputs['call']['seat'],
            'chart_key': chart_inputs['call']['key'],
            'range': get_range(chart_inputs['call']['key'], 'call'),
            'action': 'call'
        }
    ]
    positions.sort(key=lambda player: POSTFLOP_SEAT_ORDER.index(player['seat']))

    return { 'oop': positions[0], 'ip': positions[1] }

def gen_preflop_chart_inputs(hand):
    n_raises = len(hand['preflop']['raises'])
    raise_player_id = hand['preflop']['raises'][-1]['player_id']
    call_player_id = hand['preflop']['call']['player_id']
    raise_seat = hand['preflop']['raises'][-1]['seat']
    call_seat = hand['preflop']['call']['seat']

    if n_raises == 1:
        return {
            'raise': {
                'key': f'{raise_seat} {format_nth_preflop_raise(1)}',
                'seat': raise_seat,
                'player_id': raise_player_id,
            },
            'call': {
                'key': f'{call_seat} vs {raise_seat} {format_nth_preflop_raise(1)}',
                'seat': call_seat,
                'player_id': call_player_id,
            }
        }

    prev_raise_seat = hand['preflop']['raises'][-2]['seat'] 

    return {
        'raise': {
            'key': f'{raise_seat} vs {prev_raise_seat} {format_nth_preflop_raise(n_raises - 1)}',
            'seat': raise_seat,
            'player_id': raise_player_id,
        },
        'call': {
            'key': f'{call_seat} vs {raise_seat} {format_nth_preflop_raise(n_raises)}',
            'seat': call_seat,
            'player_id': call_player_id,
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