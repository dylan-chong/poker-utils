import re
import pyperclip
from parse import *

from GGPokerHandHistoryParser.Calculations import calculate_effective_stack_size_on_flop, calculate_positions, get_round_aggressor
from GGPokerHandHistoryParser.Utils import InvalidSearchException, POSTFLOP_SEAT_ORDER, SUIT_LETTERS, RANKS

def print_main_loop_instructions():
    print(f'Enter command, e.g.: ')
    print(f'- r - show recent analysable hands (where the hero reaches the flop, without limp or check)')
    print(f'- #RC1800277957 - show hand with the given hand ID (requires extraction) ')
    print(f'- l - repeat the last search')
    print(f'- h - show search history')
    print(f'- c - `c btn co lj` to print heads up ranges for BTN call, vs CO 3Bet vs LJ RFI')
    print(f'- a - show all hands')

def print_hand_title(hand):
    print(f'{hand["id"]} - {hand["date"]}')

def print_hand_error(hand):
    print_hand_title(hand)
    print(f'  {hand["error"]}')

def print_hand(hand, wait_and_copy_json=None):
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

    print(f'  -------------------------')

    print_actions('flop', hand, board_cards = (0, 3))
    print_actions('turn', hand, board_cards = (3, 4))
    print_actions('river', hand, board_cards = (4, 5))

    if wait_and_copy_json:
        print(f'')
        pyperclip.copy(wait_and_copy_json)
        print(f'Copied Desktop Postflop JSON to clipboard.')
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

    for seat in seats:
        if seat not in POSTFLOP_SEAT_ORDER:
            valid_seats_lower = [vs.lower() for vs in POSTFLOP_SEAT_ORDER]
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

def print_round_aggressor(round_key, hand):
    postflop_seat = get_round_aggressor(round_key, hand)
    if not postflop_seat: return
    print(f'  {round_key.capitalize()} aggressor')
    print(f'    {postflop_seat.upper()}')

def format_result_count(search_term, matches):
    match_hands = [hand for hand in matches if 'error' not in hand]

    non_analysable = [hand for hand in matches if 'error' in hand]
    non_analysable_suffix = '' if len(non_analysable) == 0 else f', {len(non_analysable)} not'

    count_label = 'recent analysable' if search_term == 'r' else 'analysable'
    counts = f'{len(match_hands)} {count_label}{non_analysable_suffix}'

    return [f'{search_term} - {counts}']

def format_cards(cards, with_border=True, sort=True):
    cards = list(cards)
    if sort:
        cards.sort(key=card_id_from_str)
        cards.reverse()
    joined = ' '.join(cards)
    if not with_border: return joined
    return f'[{joined}]'

def card_id(rank, suit):
    return 4 * rank + suit

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
