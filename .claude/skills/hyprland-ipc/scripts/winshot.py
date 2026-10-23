#!/usr/bin/env python3
"""Screenshot one window: winshot.py CLASS OUT.png [--title REGEX]

Finds the window with `hyprctl clients -j` and captures its geometry with grim.
Geometry is in logical pixels; the PNG is in physical pixels (scaled by the monitor's
scale). Prints the window's size, position and whether it is floating.
"""

import argparse
import json
import re
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument("window_class", help="exact window class, e.g. hyprmonctl or org.quickshell")
parser.add_argument("output")
parser.add_argument("--title", help="regex the window title must match")
args = parser.parse_args()

clients = json.loads(subprocess.check_output(["hyprctl", "clients", "-j"]))
matches = [
    c for c in clients
    if c["class"] == args.window_class and (not args.title or re.search(args.title, c["title"]))
]
if not matches:
    sys.exit(f"no window with class {args.window_class!r}" + (f" and title /{args.title}/" if args.title else ""))
window = matches[0]
(x, y), (w, h) = window["at"], window["size"]
subprocess.check_call(["grim", "-g", f"{x},{y} {w}x{h}", args.output])
print(f"{window['class']} {window['title']!r}: {w}x{h} at {x},{y} floating={window['floating']}")
