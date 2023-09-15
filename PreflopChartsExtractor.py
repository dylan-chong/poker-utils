import os
import shutil
import math
import json
from pathlib import Path
from collections import OrderedDict

# pip3 install opencv-python
import cv2

# pip3 install pypdf[image]
from pypdf import PdfReader

# pip3 install pytesseract
# install tesseract here https://github.com/tesseract-ocr/tesseract#installing-tesseract
from PIL import Image
import pytesseract
pytesseract.pytesseract.tesseract_cmd = 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

# pip3 install parse
from parse import parse

OUTPUT_DIR = 'PreflopChartExtractions'
CHARTS_PDF = 'PreflopCharts.pdf'
CHARTS_JSON_OUTPUT = Path(Path(OUTPUT_DIR), Path('PreflopCharts.json'))

N_CHART_CELLS = 13 # 13 cards in deck, 13 x 13 grid

CELL_COLOR_SAMPLE_POS_COL = 0.5
CELL_COLOR_SAMPLE_POS_ROW = 0.7
CHART_BORDER_SIZE = 3.0 / 46.0

B_CHAN = 0
G_CHAN = 1
R_CHAN = 2
ACTION_COLORS = { 
    'raise': [95, 113, 244],
    'call': [115, 219, 105],
    'fold': [233, 144, 130],
    'raise_or_fold': [183, 184, 252],
    'call_or_fold': [178, 246, 163],
    'raise_or_call': [27, 139, 253],
    'raise_or_call_or_fold': [240, 237, 109],
}

# 624 and 601 are dimensions of image 13-X21.jpg
LABEL_BG_SAMPLE_ROW_PERC = (624.0 - 10) / 624
LABEL_BG_SAMPLE_COL_PERC = 10.0 / 601
LABEL_BG_GREYSCALE_MOE = 15
LABEL_BG_BORDER = 5

CARDS = list('AKQJT98765432')
CARDS_SEPARATOR = ","

"""OCR is not good enough, so have to override"""
LABEL_NAME_TO_TEXT_ORDERED = [ 
    ("49-X4-label.png", "RFI: LJ"),
    ("16-X2-label.png", "RFI vs 3Bet: LJ vs BB"),
    ("8-X3-label.png", "RFI vs 3Bet: LJ vs SB"), 
    ("27-X5-label.png", "RFI vs 3Bet: LJ vs BTN"),
    ("0-X6-label.png", "RFI vs 3Bet: LJ vs CO"),
    ("4-X7-label.png", "RFI vs 3Bet: LJ vs HJ"),

    ("52-X8-label.png", "RFI: HJ"),
    ("30-X9-label.png", "vs RFI: HJ vs LJ"),
    ("35-X10-label.png", "RFI vs 3Bet: HJ vs BB"),
    ("20-X11-label.png", "RFI vs 3Bet: HJ vs SB"),
    ("48-X12-label.png", "RFI vs 3Bet: HJ vs BTN"),
    ("31-X13-label.png", "RFI vs 3Bet: HJ vs CO"),

    ("10-X15-label.png", "RFI: CO"), 
    ("41-X16-label.png", "vs RFI: CO vs HJ"),
    ("22-X17-label.png", "vs RFI: CO vs LJ"),
    ("13-X21-label.png", "RFI vs 3Bet: CO vs BB"),
    ("37-X20-label.png", "RFI vs 3Bet: CO vs SB"),
    ("19-X19-label.png", "RFI vs 3Bet: CO vs BTN"),
    ("42-X22-label.png", "vs 3Bet: CO vs HJ"),

    ("11-X26-label.png", "RFI: BTN"),
    ("9-X24-label.png", "vs RFI: BTN vs CO"), 
    ("36-X25-label.png", "vs RFI: BTN vs HJ"),
    ("26-X27-label.png", "vs RFI: BTN vs LJ"),
    ("44-X28-label.png", "RFI vs 3Bet: BTN vs BB"),
    ("51-X29-label.png", "RFI vs 3Bet: BTN vs SB"),
    ("25-X30-label.png", "vs 3Bet: BTN vs HJ"),
    ("40-X31-label.png", "vs 3Bet: BTN vs CO"),

    ("15-X33-label.png", "RFI: SB"),
    ("1-X34-label.png", "vs RFI: SB vs BTN"), 
    ("vs RFI: SB vs CO", "vs RFI: SB vs CO"),
    ("2-X36-label.png", "vs RFI: SB vs HJ"), 
    ("38-X35-label.png", "vs RFI: SB vs LJ"),
    ("12-X38-label.png", "RFI vs 3Bet: SB vs BB"),
    ("17-X39-label.png", "vs 3Bet: SB vs BTN"),
    ("21-X40-label.png", "vs 3Bet: SB vs CO"),
    ("3-X41-label.png", "vs 3Bet: SB vs HJ"),

    ("45-X43-label.png", "vs RFI: BB vs SB"),
    ("34-X44-label.png", "vs RFI: BB vs BTN"),
    ("43-X45-label.png", "vs RFI: BB vs CO"),
    ("5-X46-label.png", "vs RFI: BB vs HJ"), 
    ("23-X47-label.png", "vs RFI: BB vs LJ"),
    ("24-X49-label.png", "vs 3Bet: BB vs SB vs BTN"),
    ("39-X50-label.png", "vs 3Bet: BB vs SB vs CO"),
    ("50-X48-label.png", "vs 3Bet: BB vs SB vs HJ/LJ"),
    ("50-X48-label.png-SPLIT1", "vs 3Bet: BB vs SB vs HJ"),
    ("50-X48-label.png-SPLIT2", "vs 3Bet: BB vs SB vs LJ"),
    ("7-X51-label.png", "vs 3Bet: BB vs BTN"),
    ("46-X52-label.png", "vs 3Bet: BB vs CO"),
    ("18-X53-label.png", "vs 3Bet: BB vs HJ"),
]
LABEL_NAME_TO_TEXT = dict(LABEL_NAME_TO_TEXT_ORDERED)
LABEL_ORDER = [label for _, label in LABEL_NAME_TO_TEXT_ORDERED]

DUPLICATE_CHARTS = ['32-X18.jpg']

CHARTS_TO_DOUBLE = [
    ("vs 3Bet: BB vs SB vs HJ/LJ", ["vs 3Bet: BB vs SB vs HJ", "vs 3Bet: BB vs SB vs LJ"])
]

MANUAL_CHART_ENTRIES = [
    {
        "actions": { 
                "raise": "AA,AKs,AQs,AJs,ATs,A9s,A5s,AKo,KK,KQs,KJs,KTs,AQo,KQo,QQ,QJs,QTs,JJ,JTs,J9s,TT,T9s,99,88,77,66",
        },
        "label": "vs RFI: SB vs CO",
        "path": f"{OUTPUT_DIR}/14-X37.jpg",
    }
]

ANY_SEAT = "<ANY>"

def reset_chart_images_dir():
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

def extract_images_from_charts_pdf():
    reader = PdfReader(CHARTS_PDF)
    image_paths = []

    # For some reason, all the images are on the first page, even though it's not
    for i, image in enumerate(reader.pages[0].images):
        image_path = f'{OUTPUT_DIR}/{i}-{image.name}'
        image_paths.append(image_path)
        with open(image_path, "wb") as f:
            f.write(image.data)
    
    return image_paths

def remove_non_chart_images(image_paths):
    image_paths_to_keep = []
    for image_path in image_paths:
        image = cv2.imread(image_path, 0)
        rows, cols = image.shape
        aspect_ratio = cols / rows

        # Not a normal chart
        if aspect_ratio < 0.9 or aspect_ratio > 0.97: continue

        image_paths_to_keep.append(image_path)
    return image_paths_to_keep

def remove_duplicate_charts(image_paths):
    return [
        image_path
        for image_path in image_paths
        if image_path.split('/')[-1] not in DUPLICATE_CHARTS
    ]

def color_dist(a, b):
    [ab, ag, ar] = a
    [bb, bg, br] = b
    return math.sqrt(
        (int(bb) - int(ab)) ** 2 +
        (int(bg) - int(ag)) ** 2 +
        (int(br) - int(ar)) ** 2
    )

def get_action_for_color(pixel):
    action_color_dists = [
        (action, color, color_dist(pixel, color))
        for action, color in ACTION_COLORS.items()
    ]

    action_color_dists.sort(key = lambda a_c_dist: a_c_dist[2])
    
    return action_color_dists[0][0]

def format_card(r, c):
    if r < c:
        return f'{CARDS[r]}{CARDS[c]}s'
    elif r == c:
        return f'{CARDS[r]}{CARDS[r]}'
    else:
        return f'{CARDS[c]}{CARDS[r]}o'

def chart_image_to_card_action_dict(image):
    rows, cols, _channels = image.shape
    # account for border taking up space on both the left/top and bottom/right
    chart_size_px = cols * N_CHART_CELLS / (N_CHART_CELLS - CHART_BORDER_SIZE)

    card_to_action = {}
    for r in range(N_CHART_CELLS):
        for c in range(N_CHART_CELLS):
            rpx = int((r + CELL_COLOR_SAMPLE_POS_ROW) / N_CHART_CELLS * chart_size_px)
            cpx = int((c + CELL_COLOR_SAMPLE_POS_COL) / N_CHART_CELLS * chart_size_px)

            action = get_action_for_color(image[rpx][cpx])
            card = format_card(r, c)
            card_to_action[card] = action

    return card_to_action

def flip_chart_to_action_dict(dict):
    flipped = {}
    for k, v in dict.items():
        if v not in flipped: flipped[v] = []
        flipped[v].append(k)

    return {
        'actions': {
            action: join_cards(cards)
            for action, cards in flipped.items()
        }
    }

def join_cards(cards):
    return CARDS_SEPARATOR.join(cards)

def fill_chart_empty_actions(chart):
    filled_chart = {
        'actions': { 
            action: chart['actions'].get(action, "")
            for action in ACTION_COLORS
        }
    }
    filled_chart['label'] = chart['label']
    filled_chart['path'] = chart['path']
    return filled_chart

def join_cards_array(action_to_cards):
    return {action: " ".join(cards) for action, cards in action_to_cards.items()}

def color_to_gray(color):
    [b, g, r] = color
    return 0.3 * r + 0.59 * g + 0.11 * b

def greyscale_dist(color_a, color_b):
    return abs(color_to_gray(color_a) - color_to_gray(color_b))

def extract_label_area(image):
    rows, cols, _channels = image.shape
    base_row = int(LABEL_BG_SAMPLE_ROW_PERC * rows)
    base_col = int(LABEL_BG_SAMPLE_COL_PERC * cols)

    bg_color = image[base_row][base_col]

    top = base_row
    bottom = base_row
    left = base_col
    right = cols - base_col

    # Find the whole height of the label bg
    while top > 1 and greyscale_dist(image[top - 1][base_col], bg_color) < LABEL_BG_GREYSCALE_MOE:
        top = top - 1
    while bottom + 1 < rows and greyscale_dist(image[bottom + 1][base_col], bg_color) < LABEL_BG_GREYSCALE_MOE:
        bottom = bottom + 1

    return (top, bottom, left, right)

def transform_label_for_ocr(image, image_path, label_area):
    top, bottom, left, right = label_area

    label = image[top:bottom][:]
    bg_color = label[2][2].tolist()
    label = cv2.copyMakeBorder(label, LABEL_BG_BORDER, LABEL_BG_BORDER, LABEL_BG_BORDER, LABEL_BG_BORDER, cv2.BORDER_CONSTANT, value=bg_color)

    label = cv2.cvtColor(label, cv2.COLOR_BGR2GRAY)
    # _, label = cv2.threshold(label, 127, 255, cv2.THRESH_BINARY)

    # brightness = 50
    # contrast = 50
    # label = label * (contrast/127+1) - contrast + brightness

    label_path = image_path.replace('.jpg', '-label.png')
    cv2.imwrite(label_path, label)
    return label_path

def ocr(label_path):
    label_name = label_path.split('/')[-1]
    if label_path.split('/')[-1] in LABEL_NAME_TO_TEXT:
        return LABEL_NAME_TO_TEXT[label_name]

    result = pytesseract.image_to_string(Image.open(label_path))
    return (
        result
        .replace('$', 'S')
        .replace('REF', 'RFI')
        .replace('RFE', 'RFI')
        .replace('REL', 'RFI')
        .replace('BIN', 'BTN')
        .replace('Hi', 'HJ')
        .replace('HI', 'HJ')
        .replace('LI', 'LJ')
        .replace('d', 'J')
        .replace('Cutoff', 'CO')
        .replace('cutoff', 'CO')
        .replace('bet', 'Bet')
        .replace('3 Bet', '3Bet')
        .replace('ve', 'vs')
        .replace('vs', ' vs ')
        .replace('  ', ' ')
        .strip()
        .replace('‘', '')
        .replace('.', '')
        .replace('(', '')
        .replace(')', '')
        .strip()
    )

def read_chart_and_label(image_path):
    # if not image_path.startswith(CHART_IMAGES_DIR + '/13') and not image_path.startswith(CHART_IMAGES_DIR + '/42'): continue # TODO remove
    image = cv2.imread(image_path)

    card_to_action = chart_image_to_card_action_dict(image)
    chart = flip_chart_to_action_dict(card_to_action)

    label_area = extract_label_area(image)
    label_path = transform_label_for_ocr(image, image_path, label_area)
    label = ocr(label_path)

    return label, { **chart, 'label': label, 'path': image_path}

def manual_chart_entries():
    processed_charts = []
    for manual_chart in MANUAL_CHART_ENTRIES:
        label = manual_chart['label']
        actions = manual_chart['actions']
        if 'fold' in manual_chart:
            processed_charts.append((label, manual_chart))

        mentioned_cards = CARDS_SEPARATOR.join(actions.values()).split(CARDS_SEPARATOR)
        fold_cards = [card for card in all_possible_cards() if card not in mentioned_cards]
        actions_with_fold = {**actions, 'fold': join_cards(fold_cards)}

        processed_charts.append((label, { **manual_chart, 'actions': actions_with_fold }))

    return processed_charts

def all_possible_cards():
    cards = []
    for r in range(N_CHART_CELLS):
        for c in range(N_CHART_CELLS):
            cards.append(format_card(r, c))
    return cards

def double_charts_where_needed(label_to_chart_tuples):
    label_to_chart = dict(label_to_chart_tuples)

    for base_label, new_labels in CHARTS_TO_DOUBLE:
        chart = label_to_chart[base_label]
        del label_to_chart[base_label]
        for new_label in new_labels:
            label_to_chart[new_label] = { **chart, 'label': new_label }
    
    return list(label_to_chart.items())

def sort_charts_by_label_order(label_to_chart):
    label_to_chart = list(label_to_chart)
    def index_in_label_order(label_chart):
        label, _ = label_chart
        return LABEL_ORDER.index(label)
    label_to_chart.sort(key=index_in_label_order)
    return label_to_chart

def parse_seats(chart):
    label = chart['label']

    parsed = parse('RFI: {:w}', label)
    if parsed:
        return parsed[0], []

    parsed = parse('vs RFI: {:w} vs {:w}', label)
    if parsed:
        return parsed[0], [parsed[1]]

    parsed = parse('RFI vs 3Bet: {:w} vs {:w}', label)
    if parsed:
        return parsed[0], [parsed[1], parsed[0]]

    parsed = parse('vs 3Bet: {:w} vs {:w}', label)
    if parsed:
        return parsed[0], [parsed[1], ANY_SEAT]

    parsed = parse('vs 3Bet: {:w} vs {:w} vs {:w}', label)
    if parsed:
        return parsed[0], [parsed[1], parsed[2]]

    raise Exception(f'Unknown label format: {label}')

def with_seats(chart):
    seat, vs_raisers = parse_seats(chart)
    return { **chart, 'seat': seat, 'vs_raisers': vs_raisers }

def output_result(charts):
    charts_json = json.dumps(charts, indent=2)
    print(charts_json)

    with open(CHARTS_JSON_OUTPUT, 'w') as f:
        f.write(charts_json)
    print()
    print(f'Charts saved to {CHARTS_JSON_OUTPUT}')

def main():
    reset_chart_images_dir()
    image_paths = extract_images_from_charts_pdf()
    image_paths = remove_non_chart_images(image_paths)
    image_paths = remove_duplicate_charts(image_paths)

    generated_charts = [read_chart_and_label(image_path) for image_path in image_paths]

    all_charts = generated_charts + manual_chart_entries()
    all_charts = double_charts_where_needed(all_charts)
    all_charts = sort_charts_by_label_order(all_charts)

    all_charts = [(label, fill_chart_empty_actions(chart)) for label, chart in all_charts]
    all_charts = [(label, with_seats(chart)) for label, chart in all_charts]

    output_result(OrderedDict(all_charts))

if __name__ == '__main__':
    main()