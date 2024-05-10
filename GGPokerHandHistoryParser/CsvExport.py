from GGPokerHandHistoryParser.Utils import POSTFLOP_SEAT_ORDER

def export_hands_to_csv(filename, hands):
    bankroll = 0.0
    bankroll_bb_per_100_h = 0.0

    with open(filename, 'w') as export:
        for i, hand in enumerate(hands):
            win_loss = hand['players']['Hero']['win_loss_post_rake_fees']
            bankroll = bankroll + win_loss
            bankroll_bb_per_100_h = bankroll_bb_per_100_h + (win_loss / hand['big_blind'] / len(hands) * 100.0)

            tuples = hand_to_tuples(hand, i, bankroll, bankroll_bb_per_100_h)

            if i == 0:
                for key, _ in tuples:
                    export.write(key)
                    export.write(',')

            for _, value in tuples:
                export.write(value)
                export.write(',')
            export.write('\n')
            
def hand_to_tuples(hand, hand_i, bankroll, bankroll_bb_per_100_h):
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
        ('rel_bank_bb_per_100_ha',   str(bankroll_bb_per_100_h)),
        ('hero_is_postflop',         str(hero_is_postflop)),
        ('preflop_n_bet',            str(len(preflop_raises))),
        ('preflop_is_raiser',        str(is_raiser)),
    ]
