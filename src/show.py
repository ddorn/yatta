"""
This module contains all function to show logs in a meaning full way,
after they have been processed.
"""
from collections import defaultdict
from datetime import date, datetime
from enum import Enum
from itertools import groupby
from math import ceil
from operator import itemgetter
from typing import List

from src.context import Context
from src.core import Category, LogEntry, HOUR, MIN, DAY, AFK
from src.utils import *


# When adding a value here, show_grouped must be updated accordingly !
class ViewTypes(Enum):
    LIST = "list"
    TOTAL = "total"
    TIMELINE = "timeline"


def show_total(categ: dict, category=None, **ignored):
    """Print a summary of time spent in each category."""

    # Compute total for each tag. categ is not needed afterwards
    tot_time = {}
    for tag, logs in categ.items():
        tot_time[tag] = Context.tot_secs(logs)

    # We never want to see AFK
    tot_time.pop(AFK, None)

    single_max = max(tot_time.values())
    total = sum(tot_time.values())

    if isinstance(tag, date):
        # If keys are day we prefer them sorted
        sort_key = itemgetter(0)
    else:
        # otherwise we use the total time as key
        sort_key = itemgetter(1)
    lines = [
        [tag, sec2str(s), int(100 * s // total)]
        for tag, s in sorted(tot_time.items(), key=sort_key)
    ]

    pad = [
        max(len(str(c)) for c in col)
        for col in zip(*lines)
    ]

    tag: Category
    for tag, *line in lines:

        if isinstance(tag, Category):
            colorize = tag.colorize
        elif category is not None:
            colorize = category.colorize
        else:
            colorize = lambda s: fmt(s, 0, bg=0xffa500)

        cat_padded = " {:>{pad[0]}} ".format(str(tag), pad=pad)
        tag_str = colorize(cat_padded)

        tot = f" {line[0]} ".rjust(pad[1] + 2)

        BAR_LEN = 60
        prop = tot_time[tag] / single_max
        bar = "·" * ceil(prop * BAR_LEN)
        bar = colorize(bar)

        per = f" {line[1]}%"

        full = tag_str + tot + bar + per
        print(full)
    print("Total:", sec2str(total), "• average:", sec2str(total / len(lines)))


def print_group_logs(logs, only_total=False, **ignored):
    """Print logs with idientical names/class grouped together."""

    groups = defaultdict(int)

    for log in logs:
        groups[log.name, log.klass] += log.duration

    if not only_total:
        for (n, cl), dur in sorted(groups.items(), key=itemgetter(1)):
            print(sec2str(dur), n, "||", cl)

    print("Total:", sec2str(sum(groups.values())))


def print_time_line(ctx, grouped, **options):
    if len(grouped) == 1:
        grouped = grouped.popitem()[1]

    if isinstance(grouped, list):
        print_one_time_line(ctx, grouped, **options)
        print_labels(grouped[0].start, grouped[-1].end, **options)
        return

    key_sample = next(iter(grouped))

    if isinstance(key_sample, date):
        d: date
        days = [datetime(d.year, d.month, d.day, 4, 0, 0, 0) for d in grouped]
        firsts = [min(l.start for l in logs) for day, logs in grouped.items()]
        lasts = [max(l.end for l in logs) for day, logs in grouped.items()]

        _start = min(t - d for d, t in zip(days, firsts))
        _end = max(t - d for d, t in zip(days, lasts))

        start = lambda i: days[i] + _start
        end = lambda i: days[i] + _end
    else:
        _start = min(l.start for ls in grouped.values() for l in ls)
        _end = max(l.end for ls in grouped.values() for l in ls)

        start = lambda i: _start
        end = lambda i: _end

    pad = max(len(str(s)) for s in grouped)

    print("".rjust(pad), end=" ")
    print_labels(start(0), end(0), **options)
    for i, (tag, logs) in enumerate(grouped.items()):
        print(str(tag).rjust(pad), end=" ")
        print_one_time_line(ctx, logs, start(i), end(i), **options)
    print("".rjust(pad), end=" ")
    print_labels(start(0), end(0), **options)


def print_one_time_line(ctx: Context, logs: List[LogEntry], start=None, end=None, width=190,
                        min_sec_to_show=10, **ignored):
    """Print all logs in a timeline form."""

    if start is None:
        start = logs[0].start
    if end is None:
        end = logs[-1].end
    duration = end - start

    # Finding which category was the most at that time
    one_step = duration / width
    cats = [AFK] * width
    for i in range(width):
        pos = start + i * one_step
        ls = [c for log in logs if (c := log.intersected(pos, pos + one_step)) is not None]
        if ls:
            groups = ctx.group_category(ls)
            groups.pop(AFK, None)
            most_cat = max(groups, key=lambda x: ctx.tot_secs(groups[x]), default=AFK)

            if ctx.tot_secs(groups.get(most_cat, [])) > min_sec_to_show:
                cats[i] = most_cat

    # Print colorised categories
    groups = [(cat, len(list(group))) for cat, group in groupby(cats)]
    for cat, qte in groups:
        if cat != AFK:
            print(cat.with_len(qte), end="")
        else:
            print(" " * qte, end="")
    print()


def print_labels(start, end, width=190, **ignored):
    duration = end - start

    # Computing the label times
    if duration < 4 * HOUR:
        step = 15 * MIN
        base = start.replace(minute=start.minute // 15 * 15) + 15 * MIN  # next quarter
    elif duration < DAY:
        step = HOUR
        base = start.replace(minute=0) + HOUR  # Next full hour
    else:
        step = 4 * HOUR
        base = start.replace(hour=start.hour // 4 * 4, minute=0) + 4 * HOUR  # Next full 4h

    labels = [start]
    i = 0
    while labels[-1] < end:
        labels.append(base + i * step)
        i += 1
    labels[-1] = end

    # Build the label line
    label_str = ""
    for label in labels:
        time_prop = (label - start) / (end - start)
        str_prop = len(label_str) / width

        if time_prop < str_prop:
            continue

        label_str = label_str.ljust(int(width * time_prop))

        if label.minute:
            label_str += "|{:02}h{:02} ".format(label.hour, label.minute)
        else:
            label_str += "|{:02}h ".format(label.hour)
    print(label_str)

    # labels = ""
    # for i in range(LABELS-1):
    #     t = start + (end - start) * len(labels) / WIDTH
    #     labels += "|{:02}h{:02}".format(t.hour, t.minute)
    #     labels = labels.ljust(int((i+1) * WIDTH / (LABELS - 1)))

    # end_label = "{:02}h{:02}|".format(end.hour, end.minute)
    # labels = labels[:-6] + end_label
    # print(labels)


def print_legend(categories):
    for c in categories:
        print(fmt(f" {c} ", c.fg, c.bg), end=" ")
    print()


def show_grouped(ctx, grouped: dict, kind: ViewTypes, **options):
    """Recursively show categorised logs.

    Uses types to determine what to show."""

    depth = 0
    g = grouped
    while not isinstance(g, list):
        g = next(iter((g.values())))
        depth += 1

    if depth >= 1:
        key_sample = next(iter(grouped))

    # Switch for view types
    if kind == ViewTypes.TOTAL and depth <= 1:
        if depth == 0:
            grouped = {"No tag": grouped}
        show_total(grouped, **options)

    elif kind == ViewTypes.LIST and depth == 0:
        print_group_logs(grouped, **options)

    elif kind == ViewTypes.TIMELINE and depth <= 1:
        print_time_line(ctx, grouped, **options)

    else:
        for key, ls in grouped.items():
            if isinstance(key, Category):
                options["category"] = key
            print("--" * depth, key, "--" * depth)
            show_grouped(ctx, ls, kind, **options)

    return

    if isinstance(grouped, dict):
        key_sample = tuple(grouped.keys())[0]
        sample = grouped[key_sample]

        if isinstance(sample, dict) or not kind:
            # Not the last level
            for key, ls in grouped.items():
                print()
                print(key)  # TODO: pretty print it
                show_grouped(ctx, ls, kind, **options)
        else:
            assert isinstance(sample, list)

            time_line = "L" in kind
            total = "T" in kind

            if isinstance(key_sample, Category):
                if time_line:
                    # So time lines are properly aligned
                    start = min(l.start for ls in grouped.values() for l in ls)
                    end = max(l.end for ls in grouped.values() for l in ls)

                    # Show timelines
                    print_labels(start, end)
                    for cat, ls in grouped.items():
                        print_time_line(ctx, ls, start, end, show_labels=False,
                                        **options)
                    print_labels(start, end)

                    # Show legend
                    print()
                    print("Legend:", end=" ")
                    print_legend(grouped)
                elif total:
                    show_total(grouped)
                else:
                    # if not total and not time_line:
                    for cat, ls in grouped.items():
                        print("----", cat, "----")
                        print_group_logs(ls, total)
                        print()

            elif isinstance(key_sample, datetime):
                pass




    elif isinstance(grouped, list):

        if "T" in kind:
            print_time_line(ctx, grouped, **options)
        else:
            print_group_logs(grouped, only_total=(kind == "T"))
