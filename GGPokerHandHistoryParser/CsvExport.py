from GGPokerHandHistoryParser.Utils import POSTFLOP_SEAT_ORDER

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

    flop_actions = hand.get('flop', {}).get('actions', [])
    hero_is_postflop = any(
        action.get('player_id') == 'Hero'
        and action.get('action') is not 'shows'
        for action in flop_actions
    )

    oop = hand.get('oop', { 'action': None, 'player_id': None })
    ip = hand.get('ip', { 'action': None, 'player_id': None })
    is_raiser = (
        (oop['action'] == 'raise' and oop['player_id'] == 'Hero')
        or (ip['action'] == 'raise' and ip['player_id'] == 'Hero')
    )

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
        ('preflop_n_bet',            str(len(preflop_raises))),
        ('preflop_is_raiser',        str(is_raiser)),
    ]
