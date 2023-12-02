"""
On GGPoker $5 cash game tables, people fold the blinds too often to a 2BB BTN open raise.
This script find the percentage of the time neither of the blinds defends against the BTN.

# Deps
See `GGPokerHandHistoryParser.py`

# Run
python3 GGBtnRaiseBlindDefenderRate.py
"""

import math

from GGPokerHandHistoryParser.GGPokerCraftFileHelpers import load_all_hands

BLIND = 0.05
OPEN_RAISE = 2.0

def main():
    all_hands = load_all_hands()

    hands_005bb = [hand for hand in all_hands if math.isclose(hand['big_blind'], BLIND)]
    print(f'Total {BLIND} BBhands: {len(hands_005bb)}')

    hands_player_open = [hand for hand in hands_005bb if does_hand_first_action_match(hand, lambda a: a["player_id"] == "Hero")]
    print(f'Total player open hands: {len(hands_player_open)}')

    hands_player_btn_open = [hand for hand in hands_player_open if does_hand_first_action_match(hand, lambda a: a["seat"] == "BTN")]
    print(f'Total player BTN open hands: {len(hands_player_btn_open)}')

    hands_player_btn_open_xbb = [hand for hand in hands_player_btn_open if does_hand_first_action_match(hand, lambda a: math.isclose(a["to_amount"], OPEN_RAISE * BLIND))]
    print(f'Total player BTN open hands {OPEN_RAISE}bb: {len(hands_player_btn_open_xbb)}')

    button_hands_no_defenders = [hand for hand in hands_player_btn_open if last_action_is_button_open_raise(hand)]
    print(f'Total player BTN open hands {OPEN_RAISE}bb, no defenders: {len(button_hands_no_defenders)}')

    fold_rate = len(button_hands_no_defenders) / len(hands_player_btn_open_xbb)
    print(f'Out of {len(hands_player_btn_open_xbb)} button hands, {len(button_hands_no_defenders)} immediately folded')
    print(f'Thats a {fold_rate * 100}% fold rate')

def is_button_open_raise(action):
    if action['action'] != 'raises': return False
    if not math.isclose(action['to_amount'], OPEN_RAISE * BLIND): return False
    if action['player_id'] != 'Hero': return False
    if action['seat'] != 'BTN': return False
    return True

def does_hand_first_action_match(hand, cond):
    if 'preflop' not in hand: return False

    non_fold_actions = [act for act in hand['preflop']['actions'] if act['action'] != 'folds']
    if len(non_fold_actions) == 0: return False
    if not cond(non_fold_actions[0]): return False

    return True

def last_action_is_button_open_raise(hand):
    non_fold_actions = [act for act in hand['preflop']['actions'] if act['action'] != 'folds']
    return is_button_open_raise(non_fold_actions[-1])

if __name__ == '__main__':
    main()
