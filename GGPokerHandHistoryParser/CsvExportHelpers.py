from GGPokerHandHistoryParser.Utils import POSTFLOP_SEAT_ORDER
from GGPokerHandHistoryParser.PrintHelpers import format_cards

def export_hands_to_csv(filename, hands):
    bankroll = 0.0

    with open(filename, 'w') as export:
        for hand_i, hand in enumerate(hands):
            win_loss = hand['players']['Hero']['win_loss_post_rake_fees']
            bankroll = bankroll + win_loss

            tuples = hand_to_tuples(hand, hand_i, bankroll)

            if hand_i == 0:
                write_csv_row(export, list(key for key, _ in tuples))

            write_csv_row(export, list(value for _, value in tuples))
            
def write_csv_row(file, values):
    for col_i, value in enumerate(values):
        file.write(value)
        if col_i < len(values) - 1:
            file.write(',')
    file.write('\n')


def hand_to_tuples(hand, hand_i, bankroll):
    win_loss = hand['players']['Hero']['win_loss_post_rake_fees']
    rake = hand['rake'] if win_loss > 0 else 0
    fees = hand['jackpot_fees'] if win_loss > 0 else 0

    preflop_raises = hand.get('preflop', {}).get('raises', [])

    hero_did_vpip_preflop = any(
        action['player_id'] == 'Hero'
        and action['action'] not in ['folds', 'checks']
        for action in hand.get('preflop', {}).get('actions', [])
    )

    flop_actions = hand.get('flop', {}).get('actions', [])
    hero_is_postflop = any(
        action.get('player_id') == 'Hero'
        and action.get('action') != 'shows'
        for action in flop_actions
    )

    flop_player_ids = { action['player_id'] for action in flop_actions }

    oop = hand.get('oop', { 'action': None, 'player_id': None })
    ip = hand.get('ip', { 'action': None, 'player_id': None })
    is_raiser = (
        (oop['action'] == 'raise' and oop['player_id'] == 'Hero')
        or (ip['action'] == 'raise' and ip['player_id'] == 'Hero')
    )

    hole_cards = format_cards(hand['players']['Hero']['hole_cards'], with_border=False).split(' ')

    return [
        ('hand_id',                  hand['id']),
        ('hand_no',                  str(hand_i + 1)),
        ('date_utc',                 str(hand['date'])),
        ('big_blind',                str(hand['big_blind'])),
        ('seat',                     hand['players']['Hero']['seat']),
        ('seat_index',               str(POSTFLOP_SEAT_ORDER.index(hand['players']['Hero']['seat']))),
        ('win_loss_post_rake_fees',  str(win_loss)),
        ('win_post_rake_fees',       str(hand['players']['Hero']['win_post_rake_fees'])),
        ('loss',                     str(hand['players']['Hero']['loss'])),
        ('rake_paid',                str(rake)),
        ('jackpot_fees',             str(fees)),
        ('relative_bankroll',        str(bankroll)),
        ('hero_is_postflop',         str(hero_is_postflop)),
        ('preflop_n_bet',            str(len(preflop_raises) + 1)),
        ('preflop_is_raiser',        str(is_raiser)),
        ('postflop_is_oop_heads_up', str(oop['player_id'] == 'Hero')),
        ('postflop_is_ip_heads_up',  str(ip['player_id'] == 'Hero')),
        ('postflop_n_way',           str(len(flop_player_ids))),
        ('hero_did_vpip',            str(hero_did_vpip_preflop)), # TODO handle vpip postflop if BB check preflop
        ('win_loss_bb',              str(win_loss / hand['big_blind'])),
        ('hole_card_1',              str(hole_cards[0])),
        ('hole_card_2',              str(hole_cards[1])),
    ]
