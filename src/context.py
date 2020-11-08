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
    def filter_pattern(logs: LogList, name_pattern=None, class_pattern=None) -> LogIterator:
        """Yield all logs containing name_pattern or class_pattern in their name/class."""

        for log in logs:
            if name_pattern is not None and name_pattern in log.name \
                    or class_pattern is not None and class_pattern in log.klass:
                yield log

    def filter_category(self, logs: LogList, *categories) -> LogIterator:
        """Yield logs that belong to any of the given categories."""

        for log in logs:
            cat = self.get_cat(log)
            if cat in categories:
                yield log

    @staticmethod
    def filter_duration(logs: LogList, min_time: float) -> LogIterator:
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
