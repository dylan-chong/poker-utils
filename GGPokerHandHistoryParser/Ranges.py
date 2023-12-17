import json
from pathlib import Path

CHART_FILE = Path('_internal/data/PreflopCharts.json')
with open(CHART_FILE) as f:
    range_chart = json.load(f)

def find_chart(seat, vs_raisers):
    exact_matches = [
        chart for chart in range_chart.values()
        if chart['seat'] == seat
        and vs_raisers_match(chart['vs_raisers'], vs_raisers, match_any=False)
    ]

    any_matches = [
        chart for chart in range_chart.values()
        if chart['seat'] == seat
        and vs_raisers_match(chart['vs_raisers'], vs_raisers, match_any=True)
    ]

    if len(exact_matches) == 1: return exact_matches[0]
    if len(exact_matches) > 1: raise Exception(f"Somehow got {len(exact_matches)} exact chart matches for {seat}-{vs_raisers}")

    if len(any_matches) == 1: return any_matches[0]
    if len(any_matches) > 1: raise Exception(f"Somehow got {len(any_matches)} any chart matches for {seat}-{vs_raisers}")

    return None

def get_range_from_chart(chart, action_key):
    if not chart: return None

    if action_key == 'raise':
        action_to_suffix = {
            'raise': '',
            'raise_or_fold': ':0.5',
            'raise_or_call': ':0.5',
            'raise_or_call_or_fold': ':0.35'
        }
    elif action_key == 'call':
        action_to_suffix = {
            'call': '',
            'call_or_fold': ':0.5',
            'raise_or_call': ':0.5',
            'raise_or_call_or_fold': ':0.35'
        }
    else:
        raise Exception(f'Action lookup not implemented for `{action_key}`')

    ranges = [
        add_suffixes(chart['actions'][action], suffix)
        for action, suffix in action_to_suffix.items()
    ]
    return sum(ranges, [])

def add_suffixes(cards_str, suffix):
    cards = cards_str.split(',')
    return [card.strip() + suffix for card in cards if card.strip() != '']

def vs_raisers_match(vs_raisers_from_chart, vs_raisers, match_any):
    if len(vs_raisers_from_chart) != len(vs_raisers): return False

    for from_chart, not_from_chart in zip(vs_raisers_from_chart, vs_raisers):
        if from_chart == '<ANY>' and match_any: continue
        if from_chart == not_from_chart: continue
        return False
    return True
    