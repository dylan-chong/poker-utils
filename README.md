# Poker Utils

Various poker utils. See each file for installation/usage instructions.

## `GGPokerHandHistoryParser.py`

Takes GGPoker hand histories exported from PokerCraft and formats them such that you can copy the data (almost) directly into a solver, like <https://wasm-postflop.pages.dev/>.

- Why? It takes a while to enter in the hand ranges and the various other fields into a solver, so this saves you time

## `PreflopChartsExtractor.py`

A one-time tool to extract the chart data from `PreflopCharts.pdf` and put it in JSON format

- Why? We need to represent the charts in some useful data format for `GGPokerHandHistoryParser.py` to access. And screw manually entering in the chart data for all 53 charts, each being a 13x13 grid.

## `PreflopChartsSearchable.html`

A preflop chart viewer, so you can find the right preflop chart with the minimal amount of key presses.
Supports mobile.
You can [view it running here](https://htmlpreview.github.io/?https://github.com/dylan-chong/poker-utils/blob/web/PreflopChartsSearchable.html).

- Why? The `PreflopCharts.pdf` does not have text-labelled graphs (the label is inside the image), so you cannot CTRL-F to find the right chart. Hence, I need a faster way to find the right chart. (The PDF is also not mobile friendly.)
    - And we have the charts in JSON format because of `PreflopChartsExtractor.py`, so why not use them?

# Development

```bash
pip install -r requirements.txt
```
