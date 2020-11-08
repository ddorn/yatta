"""
This module defines the context class.
This class cointains all end-user input, like the categorize function,
and also methods to process logs and lists of logs to obtain relevant
information.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Callable, Iterator

from src.core import Category, LogEntry

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
