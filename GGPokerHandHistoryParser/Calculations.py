from GGPokerHandHistoryParser.Utils import NonAnalyzableHandException, POSTFLOP_SEAT_ORDER, find_index_where, get_postflop_seat, format_action_description
from GGPokerHandHistoryParser.Ranges import find_chart, get_range_from_chart

def calculate_effective_stack_size_on_flop(hand):
    oop_id = hand['oop']['player_id']
    ip_id = hand['ip']['player_id']
    stacks = hand['preflop']['new_stacks']
    return min(stacks[oop_id], stacks[ip_id])

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

def get_round_aggressor(round_key, hand):
    actions = hand[round_key]['actions']
    last_aggressor_i = find_index_where(lambda act: act['action'] in ['raises', 'bets'], actions, from_end=True)
    if last_aggressor_i is None: return None

    postflop_seat = get_postflop_seat(actions[last_aggressor_i]['player_id'], hand)
    if postflop_seat is None: return None
    return postflop_seat