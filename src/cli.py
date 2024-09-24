import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from time import time, sleep

from dateutil.relativedelta import *
import click

from src.context import Context
from src.core import AFK, Logs, LogEntry, DAY, UNCAT
from src.show import print_group_logs, print_labels, print_time_line, print_legend, show_total, show_grouped, ViewTypes
from src.utils import start_of_day

DATA_DIR = Path(__file__).parent.parent / "data"
LOG = DATA_DIR / "log"
CONFIG = DATA_DIR / "config.py"

LOG.touch()

logfile_option = click.option(
    "--logfile", "-l",
    default=LOG.as_posix(),
    type=Path,
    help="File to store the logs",
)


class ConfigType(click.ParamType):
    """Click type for the categorize function."""

    name = "Config"

    def convert(self, value, param, ctx):
        if isinstance(value, Context):
            return value

        return Context.load(value)


config_option = click.option(
    "--config", "ctx",
    default=CONFIG.as_posix(),
    type=ConfigType(),
    help="Python config file."
)

time_step_option = click.option("--time-step", "-t", default=1, help="Seconds between window title check")


class DateRangeType(click.ParamType):
    name = "Range"

    def convert(self, value: str, param, ctx):
        if isinstance(value, tuple):
            return value

        now = datetime.now()
        now_start = start_of_day(now)

        # Special cases
        value = value.lower()
        kind, _, offset = value.partition("-")
        try:
            offset = int(offset)
        except ValueError:
            offset = 0

        if kind in ("week", "w"):
            start = now_start + relativedelta(weeks=-offset-1, weekday=MO)
            end = now_start + relativedelta(weeks=-offset, weekday=SU, days=+1)
            return (start, end)
        elif kind in ("month", "m"):
            start = now_start + relativedelta(months=-offset, day=1)
            end = now_start + relativedelta(months=-offset, day=31, days=+1)
            return (start, end)
        elif kind in ("year", "y"):
            start = now_start + relativedelta(years=-offset, yearday=1)
            end = now_start + relativedelta(years=-offset, days=+1, yearday=366)
            return (start, end)
        elif kind in ("all", "a"):
            return (datetime.min, datetime.max)

        # Single integer
        try:
            start = int(value)
        except ValueError:
            pass
        else:
            if start < 0:
                return (datetime.min, datetime.max)
            start = now_start - start * DAY
            return (start, now)

        # Two integers
        a, _, b = value.partition("..")
        try:
            a = int(a)
            b = int(b)
        except ValueError:
            pass
        else:
            if a < b:
                ctx.fail(f"Empty range given for {param}.")
            start = now_start - a * DAY
            end = now_start - b * DAY
            return (start, end)

        ctx.fail(f"Could not parse the range for {param}."
                 f"You can specify:"
                 f"\n - an integer => last N days until now"
                 f"\n - a range A..B => A days ago until B days ago"
                 f"\n - a period-N, where period is year/month/week "
                 f"=> N years/month/weeks/ ago"
                 )


class ViewTypeType(click.ParamType):
    name = "View"

    def convert(self, value, param, ctx):
        if isinstance(value, ViewTypes):
            return value

        try:
            return ViewTypes(value)
        except ValueError:
            ctx.fail(f"'{value}' for {param.name} is not a valid view type. "
                     f"Try one of {'|'.join(v.value for v in ViewTypes)}.")


@click.group()
def yatta():
    pass


@yatta.command()
@logfile_option
def compress(logfile):
    logs = Logs.load(logfile)

    compressed = Logs(file=LOG.with_suffix(".compressed"))

    for log in logs:
        compressed.append(log)


@yatta.command()
@time_step_option
@logfile_option
@config_option
def start(ctx: Context, logfile, time_step):
    """Record active windows forever.

    If you start the recording twice, it will corrupt the log file."""

    logs = Logs.load(logfile)

    categ = ctx.group_category(logs)
    print_group_logs(categ.get(UNCAT), [])
    show_total(categ)

    logs.watch_apps()


@yatta.command()
@logfile_option
@config_option
def gui(ctx, logfile):
    logs = Logs.load(logfile)

    from src.gui import Gui

    Gui(ctx, logs).run()


@yatta.command()
@click.argument("graph-kind", default="list", type=ViewTypeType())
# @click.option("--day", "-d", default=0, help="How many days ago. Negative value means all time.")
@click.option("--range", "-r", default="0", type=DateRangeType(), help="Time range for the logs, -1 for all time.")
@click.option("--category", "-c", help="Search only in this category")
@click.option("--pattern", "-p", help="Should contain this pattern")
@click.option("--keep-afk", help="Don't exclude AFK logs")
# @click.option("--by-category", "-C", default=False, is_flag=True, help="Whether to print results by category")
# @click.option("--total", "-T", default=False, is_flag=True, help="Print only total values, not log entries")
# @click.option("--time-line", "-L", default=False, is_flag=True, help="Display logs in a timeline")
@click.option("--time-line-thresold", "-D", default=15,
              help="Minimum seconds of activity to show data on the timeline.")
@click.option("--group-by", "--by", "-b", default="", help="How to group logs before showing. Substring of 'CD'.")
@logfile_option
@config_option
def query(graph_kind, ctx: Context, logfile, pattern, range, category, time_line_thresold, group_by, keep_afk):
    """Get informations about time spent.

    graph-kind is the visualisation method and can be one of:
     - list: print logs
     - total: print total duration for each group
     - timeline: print logs in a timeline (you probably want to use --by D)

    Lowercase options are for filterning, and uppercase are to control the display format."""
    logs = Logs.load(logfile)

    # Filter the logs
    logs = ctx.filter_time(logs, *range, True)
    if pattern:
        logs = ctx.filter_pattern(logs, pattern)
    if category:
        logs = ctx.filter_category(logs, category)
    if not keep_afk:
        logs = ctx.exclude_categories(logs, AFK)

    logs = list(logs)

    if not logs:
        print("No matching logs")
        quit(1)
    else:
        print("From", logs[0].start, "to", logs[-1].end, ":", len(logs), "logs")

    # Classify them
    grouped = ctx.group_by(logs, group_by)

    # Display the groups
    show_grouped(ctx, grouped, graph_kind, time_line_thresold=time_line_thresold)

@yatta.command("list-cat")
@logfile_option
@config_option
def list_cat(ctx, logfile):
    logs = Logs.load(logfile)

    cats = set()
    for log in logs:
        cats.add(ctx.get_cat(log))

    print(*cats, sep="\n")
