"""
This module contains all function to show logs in a meaning full way,
after they have been processed.
"""
from collections import defaultdict
from itertools import groupby
from operator import itemgetter
from typing import List

from src.context import Context
from src.core import LogEntry, HOUR, MIN, DAY, AFK
from src.utils import *


def show_categ(categ: dict):
    """Print a summary of time spent in each category."""

    tot_time = {}
    for cat, logs in categ.items():
        tot_time[cat] = Context.tot_secs(logs)

    del tot_time[AFK]

    total = sum(tot_time.values())
    lines = [[cat, sec2str(s), 100 * s // total]
             for cat, s in sorted(tot_time.items(), key=itemgetter(1))]

    pad = [max(len(str(c)) for c in col) for col in zip(*lines)]

    print("Time tracked:", sec2str(total))
    for cat, *line in lines:
        cat_fmt = fmt(" {:>{pad[0]}} ".format(str(cat), pad=pad), cat.fg, cat.bg)
        print("{} {:<{pad[1]}} {}%".format(cat_fmt, *line, pad=pad))


def print_group_logs(logs, only_total=False):
    """Print logs with idientical names/class grouped together."""

    groups = defaultdict(int)

    for log in logs:
        groups[log.name, log.klass] += log.duration

    if not only_total:
        for (n, cl), dur in sorted(groups.items(), key=itemgetter(1)):
            print(sec2str(dur), n, "||", cl)

    print("Total:", sec2str(sum(groups.values())))


def print_time_line(ctx: Context, logs: List[LogEntry], start=None, end=None, show_labels=True, width=206,
                    min_sec_to_show=10):
    """Print all lllogs in a timeline form."""

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

    if show_labels:
        print_labels(start, end, width)


def print_labels(start, end, width=206):
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
