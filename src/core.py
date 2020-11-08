import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Callable, List

from src.utils import sec2str, contrast, fmt

SEC = timedelta(seconds=1)
MIN = timedelta(minutes=1)
HOUR = timedelta(hours=1)
DAY = timedelta(days=1)



@dataclass
class LogEntry:
    start: datetime
    klass: str
    name: str
    end: datetime

    def __repr__(self):
        return f"{sec2str(self.duration)}: {self.klass} || {self.name}"

    @property
    def duration(self) -> float:
        return (self.end - self.start).total_seconds()

    def intersected(self, start, end) -> Optional["LogEntry"]:
        """Return a log entry contained in the interval [start, end].

        Return None if the intersection is empty"""

        if self.start >= start:
            start = self.start
        if self.end <= end:
            end = self.end

        if start < end:
            return LogEntry(start, self.klass, self.name, end)
        else:
            return None

    def write_log(self, file, last_line=False):
        if not last_line:
            txt = "\n".join([
                "---",
                self.start.isoformat(),
                self.klass,
                self.name
            ])
        else:
            txt = self.end.isoformat()

        with open(file, "a") as f:
            f.write(txt + "\n")

    @classmethod
    def from_logfile(cls, log) -> "LogEntry":
        lines = log.splitlines()
        assert len(lines) in (3, 4), lines

        start = datetime.fromisoformat(lines[0])
        return cls(
            datetime.fromisoformat(lines[0]),
            lines[1],
            lines[2],
            start + SEC if len(lines) == 3 else datetime.fromisoformat(lines[3])
        )

    @classmethod
    def from_xprop(cls, output, time_step) -> "LogEntry":

        wm_name = ""
        wm_class = ""
        for line in output.splitlines():
            if line.startswith("WM_NAME"):
                wm_name = line
            elif line.startswith("WM_CLASS"):
                wm_class = line

        wm_name = wm_name.partition(" = ")[2][1:-1]
        wm_class = wm_class.partition(" = ")[2]

        return cls(
            datetime.now(),
            wm_class,
            wm_name,
            datetime.now() + SEC * time_step,
        )

    @classmethod
    def get_log(cls, time_step=1) -> "LogEntry":
        a = subprocess.check_output("xprop -id $(xdotool getwindowfocus)", shell=True, text=True)
        return cls.from_xprop(a, time_step)


class Logs(list):
    def __init__(self, *args, file=None):
        super().__init__(*args)
        self.first = True
        self.file = file

    @classmethod
    def load(cls, file):
        txt = file.read_text()
        txt = txt[4:]  # Remove the first line of ---
        if txt:
            return cls([LogEntry.from_logfile(lines)
                        for lines in txt.split("---\n") if lines], file=file)
        return cls(file=file)

    def append(self, log: LogEntry):
        """Append a log to the list and sync the file where they are stored."""
        if self.first:
            list.append(self, log)
            if self.file:
                log.write_log(self.file)
        else:
            last = self[-1]

            if last.name == log.name and last.klass == log.klass and abs(last.end - log.start) < SEC:
                last.end = log.end
            else:
                list.append(self, log)
                if self.file:
                    # Write last line of last log
                    last.write_log(self.file, True)
                    log.write_log(self.file)

        self.first = False

    def __del__(self):
        if self.file and not self.first:
            self[-1].write_log(self.file, True)


@dataclass
class Category:
    name: str
    color: int

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.name == str(other)

    @property
    def bg(self):
        return self.color

    @property
    def fg(self):
        return contrast(self.color)

    def with_len(self, length, colorize=True):
        """Return a a string of given [length] with the category name that fits.

        If colorize is True, formats the string with ANSI escape codes."""

        txt = self.name[:length].center(length)

        if colorize:
            return fmt(txt, self.fg, self.bg)
        return txt

AFK = Category("AFK", 0x000000)
UNCAT = Category("! Uncategorised !", 0x008000)
