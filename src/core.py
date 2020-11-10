import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from time import time, sleep
from typing import Optional, Callable, List, NoReturn

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

    def __str__(self):
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
    def get_log(cls, time_step=1) -> "LogEntry":
        a = subprocess.check_output("xprop -id $(xdotool getwindowfocus) -notype WM_NAME WM_CLASS", shell=True, text=True).splitlines()

        wm_name = a[0].partition(" = ")[2][1:-1]
        wm_class = a[1].partition(" = ")[2]

        start = datetime.now()
        return cls(
            start,
            wm_class,
            wm_name,
            start + SEC * time_step,
        )


class Logs(list):
    DELTA = SEC

    def __init__(self, *args, file=None):
        super().__init__(*args)
        self.first = True
        self.file = file
        self._stop = False

    def stop(self):
        """Stop the app monitoring."""
        self._stop = True

    def watch_apps(self, step=1, callback: Optional[Callable[[LogEntry], None]]=None) -> NoReturn:
        """Check for the active windows undefinetly.

        [time_step] is the duration to sleep between checks.
        [callback] is called every time a log entry is created,
            with the entry as only parameter."""

        assert self.file
        assert step >= 1

        try:
            self._watch_apps(step, callback)
        except BaseException:
            raise
        finally:
            subprocess.call(["notify-send", 'Yatta stopped !', 'Active window monitoring has stopped.',"-a", "yatta.py"])

    def _watch_apps(self, time_step, callback):
        last = time()
        self._stop = False
        while not self._stop:
            try:
                log = LogEntry.get_log(time_step)
            except subprocess.CalledProcessError as e:
                print(e)
            else:
                self.append(log)
                if callback:
                    callback(log)

            time_taken = time() - last

            # for instance lid closed
            if time_taken >= time_step:
                last = time()
                print("skip")
                continue

            # This keeps the average between calls exactly time_step
            last += time_step
            sleep(time_step - time_taken)

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
            if not self.merge(log):
                if self.file:
                    # Write last line of last log
                    self[-2].write_log(self.file, True)
                    log.write_log(self.file)

        self.first = False

    def merge(self, log) -> bool:
        """Append a log to the list, and merge it with the previous one if possible.

        Returns whether the log was merged.
        This method can be called with a regular list as argument, if requiered,
        but keep in mind that it modifies the last log... (it CAN cause bugs...)."""

        if not self:
            list.append(self, log)
            return False

        last = self[-1]
        if abs(last.end - log.start) < self.DELTA:
            if last.name == log.name and last.klass == log.klass:
                last.end = log.end
                return True
            else:
                last.end = log.start

        list.append(self, log)
        return False

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
