from parse import *
from datetime import datetime
import re

from GGPokerHandHistoryParser.Utils import find_index_where, matches_regex, STREETS

SEAT_NUM_TO_SEAT = {
    1: 'BTN',
    2: 'SB',
    3: 'BB',
    4: 'LJ',
    5: 'HJ',
    6: 'CO',
}

def split_lines_into_segments(hand_lines):
    header_i = find_index_where(matches_regex(r'Poker Hand .*'), hand_lines)
    preflop_i = find_index_where(matches_regex(r'\*\*\* HOLE CARDS .*'), hand_lines)
    flop_i = find_index_where(matches_regex(r'\*\*\* (FLOP|FIRST FLOP) .*'), hand_lines)
    # GGPoker calls the end of the hand showdown, not the actual reveal of cards
    showdown_i = find_index_where(matches_regex(r'\*\*\* (SHOWDOWN|FIRST SHOWDOWN) .*'), hand_lines)
    summary_i = find_index_where(matches_regex(r'\*\*\* SUMMARY .*'), hand_lines)

    preflop_full = hand_lines[preflop_i:(flop_i or showdown_i)]
    preflop_actions =  [line for line in preflop_full if not line.startswith('Dealt to')]

    postflop = hand_lines[flop_i:showdown_i] if flop_i else None

    segments = {
        'all_lines': hand_lines,
        'header': hand_lines[header_i:preflop_i],
        'preflop_full': preflop_full,
        'preflop': preflop_actions,
        'showdown': hand_lines[showdown_i:summary_i],
        'summary': hand_lines[summary_i:]
    }

    if not postflop:
        return segments

    segments['postflop'] = postflop
    res = { **segments, **split_postflop_lines(postflop)}

    return res

def split_postflop_lines(lines):
    flop_i = find_index_where(matches_regex(r'\*\*\* FLOP \*\*\*.*'), lines)
    turn_i = find_index_where(matches_regex(r'\*\*\* TURN \*\*\*.*'), lines)
    river_i = find_index_where(matches_regex(r'\*\*\* RIVER \*\*\*.*'), lines)
    
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
    basic_hand = parse_basic_header_meta(segments)
    basic_hand['players'] = parse_header_players(segments)
    parse_summary(basic_hand, segments)
    parse_winners(basic_hand, segments)
    return basic_hand, segments

def parse_hand(segments, hand):
    hand = {**hand}
    hand['players'] = parse_shown_cards(segments, hand)

    hand['preflop'] = parse_bets_and_new_stacks(
        hand,
        parse_actions(segments['preflop'], hand),
        players_to_stacks(hand['players']),
        0,
        post_blinds=True,
        segments=segments
    )

    hand['board'] = parse_board(segments)

    for i, street in enumerate(STREETS):
        if i == 0: continue
        prev_street = STREETS[i - 1]
        if not street in segments: break

        hand[street] = parse_bets_and_new_stacks(
            hand,
            parse_actions(segments[street], hand),
            hand[prev_street]['new_stacks'],
            hand[prev_street]['new_pot']
        )

    return hand

def players_to_stacks(players):
    return { name: player['initial_stack'] for name, player in players.items() }

def parse_basic_header_meta(segments):
    hand_id, small_blind, big_blind, date_str = parse("Poker Hand {}: Hold'em No Limit (${}/${}) - {}", segments['header'][0])

    dt = datetime.strptime(date_str, '%Y/%m/%d %H:%M:%S')

    return {
        "id": hand_id,
        "small_blind": parse_money_amount(small_blind),
        "big_blind": parse_money_amount(big_blind),
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
            "initial_stack": parse_money_amount(stack_size_str)
        }
    
    players['Hero']['hole_cards'] = parse_hero_cards(segments)

    return players

def parse_summary(basic_hand, segments):
    for line in segments['summary']:
        summary = re.match(r'Total pot \$([\d.]+) \| Rake \$([\d.]+) \| Jackpot \$([\d.]+)', line)
        if not summary: continue
        pot_str, rake_str, jackpot_str = summary.group(1, 2, 3)

        basic_hand['pot'] = float(pot_str)
        # I have no idea WTF this jackpot is but it seems to be taken from the winners
        basic_hand['rake'] = float(rake_str) + float(jackpot_str)
        basic_hand['jackpot_fees'] = float(jackpot_str)
        return

    raise Exception(f"Did not find summary in expected format in {segments['summary']}")

def parse_winners(basic_hand, segments):
    for line in segments['all_lines']:
        match = re.match(r'(\w+) collected \$([\d.]+)', line)
        if not match: continue
        winner, amount_str = match.group(1, 2)

        for player_id, player in basic_hand['players'].items():
            prev_win = player.get('win_post_rake', 0)
            if winner == player_id:
                player['win_post_rake'] = float(amount_str) + prev_win
            else:
                player['win_post_rake'] = prev_win

def parse_bets_and_new_stacks(hand, street_actions, previous_player_stacks, previous_pot, post_blinds=False, segments={}):
    # bets the player makes (raising to the latest amount in the list)
    bets_by_player = {player_id: [] for player_id, _ in hand['players'].items()}

    if post_blinds:
        for player_id, blind in parse_blinds(segments['header']):
            bets_by_player[player_id].append(blind)

    for action_obj in street_actions:
        action = action_obj['action'] # todo rename to type
        player_id = action_obj['player_id']
        if action == 'folds': continue
        if action == 'checks': continue
        if action == 'bets':
            bets_by_player[player_id].append(action_obj['amount'])
        if action == 'raises':
            bets_by_player[player_id].append(action_obj['to_amount'])
        if action == 'calls':
            bets = bets_by_player[player_id]
            last_bet = 0 if len(bets) == 0 else bets[-1]
            bets.append(action_obj['amount'] + last_bet)
        if action == 'excess_uncalled_bet_returned':
            bets = bets_by_player[player_id]
            last_bet = bets[-1]
            bets.append(last_bet - action_obj['amount'])

    pot_diff = sum(bets[-1] for _, bets in bets_by_player.items() if len(bets) > 0)

    return {
        'actions': street_actions,
        'bets': bets_by_player,
        'new_stacks': calculate_player_stacks(previous_player_stacks, [bets_by_player]),
        'new_pot': pot_diff + previous_pot
    }

def calculate_player_stacks(stacks, bets_by_player_list):
    new_stacks = { **stacks }
    for bets_by_player in bets_by_player_list:
        for player_id, bets in bets_by_player.items():
            last_bet = 0 if len(bets) == 0 else bets[-1]
            new_stacks[player_id] = stacks[player_id] - last_bet
    return new_stacks

def dollars_without_all_in_suffix(str):
    return parse_money_amount(str.replace(' and is all-in', ''))

def parse_blinds(lines):
    bets = []
    for line in lines:
        parsed = parse('{}: posts {} blind ${}', line)
        if not parsed: continue
        player_id, _, blind_str = parsed
        bets.append((player_id, parse_money_amount(blind_str)))
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
    
    return []

def parse_actions(lines, hand):
    actions = []
    for line in lines:
        if line.startswith('***'): continue
        actions.append(parse_action(line, hand))
    return actions

def parse_action(line, hand):
    uncalled_bet = re.match(r'Uncalled bet \(\$([\d.]+)\) returned to (\w+)', line)
    if uncalled_bet:
        amount_str, player_id = uncalled_bet.group(1, 2)
        return {
            'player_id': player_id,
            'action': 'excess_uncalled_bet_returned',
            'seat': hand['players'][player_id]['seat'],
            # This is the raise minus the amount required to call any previous
            # bet, that call amount will be put in the total pot figure.
            'amount': float(amount_str)
        }

    parse_result = parse('{}: {}', line)
    if not parse_result:
        raise Exception(f'Unexpected action line: {line}')
    player_id, full_action = parse_result

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
        **amounts
    }

def parse_hero_cards(segments):
    lines = segments.get('preflop_full', [])
    line_i = find_index_where(matches_regex('Dealt to Hero.*'), lines)
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

def parse_money_amount(amount):
    # Yeah GGPoker. Wrong % format string somewhere?
    # It also appears to only appear in '1.\x00\x00' as the initial stack size.
    # The stack size of '1.00' is also incorrect when it happens (not even close to what it actually is).
    return float(amount.replace('\x00', '0'))
