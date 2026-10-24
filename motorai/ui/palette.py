"""Colors for all charts in the app — one place, so every view agrees on
what a color means. Values are the validated defaults from the project's
dataviz palette (categorical slots 1/2, diverging blue<->red, neutral gray,
status good/critical). Run `validate_palette.js` again if these ever change.
"""

SURFACE_LIGHT = "#fcfcfb"
GRID_LINE = "#e1e0d9"
AXIS = "#c3c2b7"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
TEXT_MUTED = "#898781"

# Two-series comparison charts (analysed lap vs reference/best lap)
COLOR_ANALYSED_LAP = "#2a78d6"   # categorical slot 1 — blue
COLOR_REFERENCE_LAP = "#eb6834"  # categorical slot 2 — orange

# Diverging delta-time encoding: losing time vs gaining time, neutral = on pace
COLOR_LOSING_TIME = "#e34948"    # diverging red pole
COLOR_GAINING_TIME = "#2a78d6"   # diverging blue pole
COLOR_NEUTRAL = "#c3c2b7"        # gray midpoint

COLOR_GOOD = "#0ca30c"
COLOR_CRITICAL = "#d03b3b"
