"""
This module defines the context class.
This class cointains all end-user input, like the categorize function,
and also methods to process logs and lists of logs to obtain relevant
information.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Callable

from src.core import Category, LogEntry

LogList = List[LogEntry]


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
