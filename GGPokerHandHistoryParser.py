"""
# Setup 
You will have to run PreflopChartsExtractor.py to produce the charts JSON. See that file for docs

# Run
python3 GGPokerHandHistoryParser.py

# To export, for another person to use
python -m PyInstaller GGPokerHandHistoryParser.py -y --add-data 'PreflopChartExtractions/PreflopCharts.json;data'
# Then compress/send the folder inside /dist/
"""

import multiprocessing
import traceback
import re

from GGPokerHandHistoryParser.DesktopPostflopHelpers import gen_desktop_postflop_json
from GGPokerHandHistoryParser.GGPokerCraftFileHelpers import load_all_hands
from GGPokerHandHistoryParser.PrintHelpers import print_main_loop_instructions, print_main_loop_instructions, print_hand_error, print_hand, print_hand_short, print_call_and_raise_range, format_result_count
from GGPokerHandHistoryParser.Utils import InvalidSearchException, DOWNLOADS_DIR
from GGPokerHandHistoryParser.History import save_to_history_file, last_search_term, print_history

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
    print_main_loop_instructions()
    search_term = input('>>> ').strip()
    print()
    search_term = reformat_search_term(search_term)

    if search_term == 'h':
        print_history()
        return search_term, []
    if search_term.startswith('c '):
        print_call_and_raise_range(search_term)
        return search_term, []

    hands = load_all_hands()
    hands.sort(key=lambda hand: hand['date'])
    result_hands = []
    
    if search_term.startswith('#'):
        for hand in hands:
            if hand['id'] != search_term: continue
            result_hands.append(hand)
            if 'error' in hand:
                print_hand_error(hand)
                continue
            print_hand(hand, wait_and_copy_json=gen_desktop_postflop_json(hand))

    if search_term == 'a':
        for hand in hands:
            if 'error' in hand:
                print_hand_error(hand)
                continue
            print_hand(hand)
            result_hands.append(hand)
    
    if search_term == 'r':
        hands_by_id = {}
        for hand in reversed(hands):
            if len(hands_by_id) == 50: break
            if hand['id'] in hands_by_id: continue
            if 'error' in hand: continue
            hands_by_id[hand['id']] = hand
        result_hands = list(hands_by_id.values())
        result_hands.sort(key=lambda hand: hand['date'])
        for hand in result_hands: print_hand_short(hand)

    print()
    for line in format_result_count(search_term, result_hands):
        print(line)
    return search_term, result_hands

def reformat_search_term(search_term):
    if search_term in ['h', 'e', 'a', 'r']: return search_term

    if search_term.startswith('RC'):
        search_term = '#' + search_term
    if search_term.startswith('#RC'):
        if search_term.endswith('.0'):
            search_term = search_term[:-2]

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

if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
