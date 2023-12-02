from pathlib import Path
from parse import *

POSTFLOP_SEAT_ORDER = ['SB', 'BB', 'LJ', 'HJ', 'CO', 'BTN']
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
SUIT_LETTERS = ["c", "d", "h", "s"]

DOWNLOADS_DIR = Path(Path.home(), Path('Downloads'))

class NonAnalyzableHandException(Exception):
    "Raised when the hand can't be analysed, e.g., the player folds preflop, or nobody calls the player's open raise"
    pass
class InvalidSearchException(Exception):
    pass

def format_action_description(seat, vs_raisers, action_key):
    action = 'Call' if action_key == 'call' else format_n_bet(len(vs_raisers) + 2)
    vs_suffix = ' vs '.join(vs_raisers)
    vs_suffix = ''.join(
        f' vs {raiser} {format_n_bet(len(vs_raisers) - i + 1)}'
        for i, raiser in enumerate(vs_raisers)
    )
    return f'{action} as {seat}{vs_suffix}'

def format_n_bet(n):
    if n < 2: raise Exception(f"Invalid n bet: {n}")
    if n == 2: return 'RFI'
    return f'{n}Bet'

def get_postflop_seat(player_id, hand):
    if hand['oop']['player_id'] == player_id: return 'oop'
    if hand['ip']['player_id'] == player_id: return 'ip'
    return None
    
def find_index_where(func, iterable, from_end=False):
    with_index = reversed(list(enumerate(iterable))) if from_end else enumerate(iterable)
    for i, line in with_index:
        if func(line): return i
    return None

def dollars_to_cents(dollars, should_round=True):
    cents = 100 * dollars
    if should_round: return int(round(cents))
    return cents

def matches_format(format):
    return lambda line: bool(parse(format, line))

def matches_any_format(formats):
    def matches(line):
        for format in formats:
            if parse(format, line): return True
        return False
    return matches
