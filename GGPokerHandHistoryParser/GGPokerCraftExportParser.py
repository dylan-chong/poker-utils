from parse import *
from datetime import datetime

from GGPokerHandHistoryParser.Utils import find_index_where, matches_format

SEAT_NUM_TO_SEAT = {
    1: 'BTN',
    2: 'SB',
    3: 'BB',
    4: 'LJ',
    5: 'HJ',
    6: 'CO',
}

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

    for action_obj in hand.get('preflop', {}).get('actions', []):
        action = action_obj['action'] # todo rename to type
        player_id = action_obj['player_id']
        if action == 'folds': continue
        if action == 'checks': continue
        if action == 'raises':
            bets_by_player[player_id].append(action_obj['to_amount'])
        if action == 'calls':
            bets = bets_by_player[player_id]
            last_bet = 0 if len(bets) == 0 else bets[-1]
            bets.append(action_obj['amount'] + last_bet)

    pot = sum(bets[-1] for _, bets in bets_by_player.items() if len(bets) > 0)
    return {
        'bets': bets_by_player,
        'new_stacks': calculate_player_stacks(hand, [bets_by_player]),
        'pot': pot
    }

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

def dollars_without_all_in_suffix(str):
    return float(str.replace(' and is all-in', ''))

def parse_blinds(lines):
    bets = []
    for line in lines:
        parsed = parse('{}: posts {} blind ${}', line)
        if not parsed: continue
        player_id, _, blind_str = parsed
        bets.append((player_id, float(blind_str)))
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

    if action == 'bets':
        bet = parse('${}', tail)
        amounts = { 'amount': dollars_without_all_in_suffix(bet[0]) }
    elif action == 'calls':
        call = parse('${}', tail)
        amounts = { 'amount': dollars_without_all_in_suffix(call[0]) }
    elif action == 'raises':
        _, raise_to = parse('${} to ${}', tail)
        amounts = { 'to_amount': dollars_without_all_in_suffix(raise_to) }
    else:
        amounts = {}

    seat = hand['players'][player_id]['seat']
    return {
        'player_id': player_id,
        'action': action,
        'seat': seat,
        'tail': tail,
        **amounts
    }

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
