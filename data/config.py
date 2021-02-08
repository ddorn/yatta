"""
User configuration should define categories and a function
called [categorize] that takes a LogEntry and return its category

Two categories are always defined, AFK and UNCAT,they can be found with
>>> from src.core import LogEntry, Category, AFK, UNCAT

The categorize function should always return a category, so
>>> def categorize(log):
>>>     return UNCAT
is the minimal function.
"""

import re
from pathlib import Path
from time import sleep
from typing import List, Tuple, Union
import subprocess

import pygame

from src.core import LogEntry, Category, AFK, UNCAT

# Categories
CODE = Category("Coding", 0xffffff)
CHAT = Category("Chat", 0xffa500)
ASSIST = Category("Assistanat", 0xffff00)
MOOC = Category("MOOCs", 0x4070c0)
CQFD = Category("CQFD", 0x222222)
EPFL = Category("EPFL", 0xff0000)
CHILL = Category("Chill", 0xff00ff)
TIMETRACK = Category("Time tracking", 0x0000ff)
NIXOS = Category("NixOs", 0x555555)
WONTFIX = Category("Wont fix", 0x000080)
ADMIN = Category("Administratif", 0xaaaaaa)
FRACTALS = Category("Fractals", 0xf62459)

RULES_FILE = Path(__file__).with_suffix(".yatta")

def load_rules() -> List[Tuple[Category, Union[str, re.Pattern]]]:
    cats = {k: v for k, v in globals().items() if k.isupper() and isinstance(v, Category)}
    file = RULES_FILE.read_text().splitlines()

    rules = []
    last_cat = None
    for line in file:
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue

        if line.startswith(" "):  # rule
            assert last_cat, "The rule is not in a category"

            # find if there is a type
            t, _, rule = stripped.partition(" ")
            rule = rule.strip()
            flags = re.IGNORECASE
            if t.lower() in ("r", "e"):
                if t.isupper():
                    flags ^= re.IGNORECASE

                t = t.lower()
                if t == "r":  # rule is a regex
                    pass
                # elif t == "e":  # rule is a conjunction
                #     rule = t.split("&")
            else:
                rules.append((last_cat, stripped.casefold()))
                continue

            rules.append((last_cat, re.compile(rule, flags)))
        else:  # Category
            last_cat = cats[stripped.strip(":")]

    return rules


name_rules = load_rules()

def categorize(log: LogEntry, __cache={}) -> Category:
    as_tuple = (log.start, log.end, log.name, log.klass)
    if as_tuple in __cache:
        return __cache[as_tuple]

    cat = _categorize(log)
    __cache[as_tuple] = cat
    return cat

def _categorize(log: LogEntry) -> Category:
    # Categorizing vim uses
    if log.name == "nvim":
        return CODE

    if log.klass == '"zoom", "zoom"':
        return categorize_zoom(log)

    name = log.name.casefold()
    for cat, pattern in name_rules:
        if isinstance(pattern, str):
            if pattern in name:
                return cat
        elif re.search(pattern, log.name):
            return cat

    class_contains_map = {
        "telegram": CHAT,
        "Spotify": CHILL,
        "krita": CHILL,
        "mandelbort": FRACTALS,
        "Steam": CHILL,
        "wpa_gui": NIXOS,
        # "terminator": CODE,
    }

    for pattern, cat in class_contains_map.items():
        if pattern in log.klass:
            return cat

    wontfix = [
        "/run/current-system/sw/bin/htop",
        "Mozilla Firefox",
        "Save As",
        "File Upload",
        "Unsaved*"
    ]
    for w in wontfix:
        if log.name == w or log.klass == w:
            return WONTFIX

    if log.name == log.klass == "":
        return AFK

    return UNCAT



def categorize_zoom(log: LogEntry):
    """Do it based on my schedule as zoom does not provide any meaningful info -_-"""
    weekday = log.start.weekday()
    hour = log.start.hour

    if log.start.year == 2020:
        if weekday == 0:  # Monday
            if hour == 10:
                return ASSIST
            elif hour == 12:
                return CHILL  # Séminaire Bachelor
        elif weekday == 1:  # Tuesday
            if 14 <= hour < 16:
                return ASSIST
        elif weekday == 2:  # Wednesday
            if hour == 16:
                return CQFD
        elif weekday == 3:  # Thursday
            if 10 <= hour < 12 or 13 <= hour < 15:
                return ASSIST
        elif weekday == 4:  # Friday
            if hour == 18:
                return CHILL  # Trivials notions

    return EPFL


def shortcuts(event):
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_e:
            subprocess.call(["terminator", "-fx", f"nvim -O {RULES_FILE} {__file__}"])

        if event.key == pygame.K_s:
            sleep(5 * 60)
