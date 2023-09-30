"""Helpers for the Desktop Postflop tool"""

import json

from GGPokerHandHistoryParser.Utils import dollars_to_cents
from GGPokerHandHistoryParser.Calculations import get_round_aggressor, calculate_effective_stack_size_on_flop

def gen_desktop_postflop_json(hand):
    preflop_aggressor = get_round_aggressor('preflop', hand)
    object = {
        "oopRange": ','.join(hand['oop']['range'] or ''),
        "ipRange": ','.join(hand['ip']['range'] or ''),
        "config": {
            "board": hand['board'][0:3],
            "startingPot": dollars_to_cents(hand["preflop"]["pot"]),
            "effectiveStack": dollars_to_cents(calculate_effective_stack_size_on_flop(hand)),
            "rakePercent": 0,
            "rakeCap": 0,
            "donkOption": False,
            "oopFlopBet": "50, 75" if preflop_aggressor == 'oop' else "",
            # TODO adapt these numbers based on ranges 
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
            # TODO put this in the bet sizings (eg 39c). may have to estimate the ram usage as you can't load profiles for bet sizes
            "addedLines": gen_postflop_bet_lines(hand),
            "removedLines": ""
        }
    } 
    return json.dumps(object, indent=2)

def gen_postflop_bet_lines(hand):
    actions_per_round = []
    for key in ['flop', 'turn', 'river']:
        actions = hand.get(key, {}).get('actions', [])
        action_strings = [gen_postflop_action_string(action) for action in actions]
        actions_per_round.append(action_strings)
    
    return "|".join([
        "-".join([
            act for act in actions
            if act
        ])
        for actions in actions_per_round
        if actions
    ])
        
def gen_postflop_action_string(action_obj):
    action = action_obj['action']
    if action in ['shows', 'folds']: return ''

    if action == 'checks': return 'X'
    if action == 'calls': return 'C'
    if action == 'bets': return f'B{dollars_to_cents(action_obj["amount"])}'
    if action == 'raises': return f'R{dollars_to_cents(action_obj["to_amount"])}'
    raise Exception('Unexpected action {act}')
