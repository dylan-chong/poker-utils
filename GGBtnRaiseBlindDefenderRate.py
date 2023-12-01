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

def main():
    hands = load_all_hands()
    hands = [hand for hand in hands if math.isclose(hand['big_blind'], 0.05)]
    print(f'Total hands: {len(hands)}')
    print(f'Total player open hands: {len([hand for hand in hands if does_hand_first_action_match(hand, lambda a: a["player_id"] == "Hero")])}')
    print(f'Total player BTN open hands: {len([hand for hand in hands if does_hand_first_action_match(hand, lambda a: a["player_id"] == "Hero" and a["seat"] == "BTN")])}')
    print(f'Total player BTN open hands 2bb: {len([hand for hand in hands if does_hand_first_action_match(hand, lambda a: a["player_id"] == "Hero" and a["seat"] == "BTN" and math.isclose(a["to_amount"], 2 * 0.05))])}')
    print(f'Total player BTN open hands 2.4bb: {len([hand for hand in hands if does_hand_first_action_match(hand, lambda a: a["player_id"] == "Hero" and a["seat"] == "BTN" and math.isclose(a["to_amount"], 2.4 * 0.05))])}')
    print(f'Total player BTN open hands not 2bb and not 2.4bb: {len([hand for hand in hands if does_hand_first_action_match(hand, lambda a: a["player_id"] == "Hero" and a["seat"] == "BTN" and (not math.isclose(a["to_amount"], 2 * 0.05) and not math.isclose(a["to_amount"], 2.4 * 0.05)))])}')

    button_hands = [hand for hand in hands if is_hero_button_hand(hand)]
    button_hands_no_defenders = [hand for hand in button_hands if last_action_is_button_open_raise(hand)]

    fold_rate = len(button_hands_no_defenders) / len(button_hands)
    print(f'Out of {len(button_hands)} button hands, {len(button_hands_no_defenders)} immediately folded')
    print(f'Thats a {fold_rate * 100}% fold rate')

def is_button_open_raise(action):
    if action['action'] != 'raises': return False
    if not math.isclose(action['to_amount'], 2 * 0.05): return False
    if action['player_id'] != 'Hero': return False
    if action['seat'] != 'BTN': return False
    return True

def is_hero_button_hand(hand):
    if 'preflop' not in hand: return False

    non_fold_actions = [act for act in hand['preflop']['actions'] if act['action'] != 'folds']
    if len(non_fold_actions) == 0: return False
    if not is_button_open_raise(non_fold_actions[0]): return False

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