"""
This module defines the context class.
This class cointains all end-user input, like the categorize function,
and also methods to process logs and lists of logs to obtain relevant
information.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Iterator, Tuple

from src.core import Category, LogEntry, DAY
from src.utils import start_of_day

LogList = List[LogEntry]
LogIterator = Iterator[LogEntry]


@dataclass
class Context:
    get_cat: Callable[[LogEntry], Category]
    shortcuts: Callable
    path: str = ""

    @classmethod
    def load(cls, path):

        with open(path, "r") as f:
            code = f.read()

        compiled = compile(code, path, "exec")
        globs = {"__file__": path}
        exec(compiled, globs)

        try:
            categorize = globs["categorize"]
        except KeyError:
            print(globs)
            raise KeyError(f"No function [categorize] in {path}.")

        shortcuts = globs.get("shortcuts", lambda e: 0)

        return cls(categorize, shortcuts, path)

    def reload(self):
        assert self.path, "Cannot reload context without path"

        new = self.load(self.path)
        self.get_cat = new.get_cat
        self.shortcuts = new.shortcuts

    @staticmethod
    def tot_secs(logs: LogList) -> float:
        """Return the total duration of all logs."""
        return sum(log.duration for log in logs)

    def group_category(self, logs: LogList) -> Dict[Category, List[LogEntry]]:
        """Group logs in a dict by category."""
        categs = defaultdict(list)
        for log in logs:
            cat = self.get_cat(log)
            categs[cat].append(log)

        return categs

    def sort_categories(self, cats: Dict[Category, LogList], best=None, reverse=False) -> List[Tuple[Category, LogList]]:
        """Return a list of categories and logs sorted by total time.

        If [best] is given, return only the [best] categories with the most time."""

        cats = sorted(cats.items(), key=lambda x: self.tot_secs(x[1]), reverse=not reverse)

        if best:
            return cats[:best]

        return cats

    @staticmethod
    def filter_time(logs: LogList, start, end, clamp=True) -> LogIterator:
        """Yields all logs between start and end.

        If [clamp] is True, each log is clamped to the interval,
        otherwise they can have a part outside [start, end]."""

        for log in logs:
            intersected = log.intersected(start, end)

            if intersected is not None:
                if clamp:
                    yield intersected
                else:
                    yield log

    @staticmethod
    def filter_pattern(logs: LogIterator, name_pattern=None, class_pattern=None) -> LogIterator:
        """Yield all logs containing name_pattern or class_pattern in their name/class."""

        for log in logs:
            if name_pattern is not None and name_pattern in log.name \
                    or class_pattern is not None and class_pattern in log.klass:
                yield log

    def filter_category(self, logs: LogIterator, *categories) -> LogIterator:
        """Yield logs that belong to any of the given categories."""

        for log in logs:
            cat = self.get_cat(log)
            if cat in categories:
                yield log

    def exclude_categories(self, logs: LogIterator, *categories) -> LogIterator:
        """Yield logs that belong to none of the given categories."""

        for log in logs:
            cat = self.get_cat(log)
            if cat not in categories:
                yield log

    @staticmethod
    def filter_duration(logs: LogIterator, min_time: float) -> LogIterator:
        """Yield logs lasting at least [min_time]."""

        for log in logs:
            if log.duration >= min_time:
                yield log

    @staticmethod
    def filter_today(logs, shift=0, day_start_hour=4):
        """Yield all logs that happend today.

        if [shift] is given, shifts the day relatively to today.
        [day_start_hour] is the first hour in a day."""

        day = datetime.now() + shift * DAY
        day = start_of_day(day)

        yield from Context.filter_time(logs, day, day + DAY)

    def group_by(self, logs: LogIterator, classifications: str):
        if not classifications:
            return list(logs)

        classification = classifications[0]
        classifications = classifications[1:]

        groups = defaultdict(list)
        for log in logs:
            if classification == "C":
                c = self.get_cat(log)
            elif classification == "D":
                c = start_of_day(log.start).date()
            else:
                raise ValueError(f"'{classification}' is not a valid classification. "
                                 f"Use:"
                                 f"\n - C for categories"
                                 f"\n - D for days"
                                 # f"\n - M for months"
                                 )

            groups[c].append(log)

        for cat, ls in groups.items():
            groups[cat] = self.group_by(ls, classifications)

        return groups
