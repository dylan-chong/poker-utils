from pathlib import Path

from GGPokerHandHistoryParser.Utils import DOWNLOADS_DIR
from GGPokerHandHistoryParser.PrintHelpers import format_result_count

LOG_FILE_PATH = Path(Path.home(), Path('.GGPokerHandHistoryParser.history.txt'))

def last_search_term():
    lines = read_history(1)
    if len(lines) == 0:
        return None
    return lines[-1].split(' - ')[0]

def print_history():
    history = read_history(50)
    for i, line in enumerate(history):
        print(f'{len(history) - i}. {line}')

def read_history(n_lines_from_end):
    with open(LOG_FILE_PATH, 'r') as f:
        lines = [line.strip() for line in f.readlines() if line.strip() != '']
        return lines[-n_lines_from_end:]

def save_to_history_file(search_term, matches):
    with open(LOG_FILE_PATH, 'a+') as f:
        for line in format_history_lines(search_term, matches):
            f.write(line)
            f.write('\n')

def format_history_lines(search_term, matches):
    if search_term in ['l', 'h', 'a', 'e', 'r']: return []
    if search_term.startswith('c '): return []
    if len(matches) == 0: return [f'{search_term} - {len(matches)} matches']
    return format_result_count(search_term, matches)
