import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from time import time, sleep

import click

from src.context import Context
from src.core import Logs, LogEntry, DAY, UNCAT
from src.show import print_group_logs, print_labels, print_time_line, print_legend, show_categ

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

        with open(value, "r") as f:
            code = f.read()

        compiled = compile(code, value, "exec")
        globs = {}
        exec(compiled, globs)

        try:
            categorize = globs["categorize"]
        except KeyError:
            print(globs)
            self.fail("No function categorize defined in the config.")

        return Context(categorize)


config_option = click.option(
    "--config", "ctx",
    default=CONFIG.as_posix(),
    type=ConfigType(),
    help="Python config file."
)


@click.group()
def app_watch():
    pass


@app_watch.command()
@logfile_option
def compress(logfile):
    logs = Logs.load(logfile)

    compressed = Logs(file=LOG.with_suffix(".compressed"))

    for log in logs:
        compressed.append(log)


@app_watch.command()
@click.option("--time-step", "-t", default=1, help="Seconds between window title check")
@logfile_option
@config_option
def start(ctx: Context, logfile, time_step):
    assert time_step >= 1

    logs = Logs.load(logfile)

    categ = ctx.group_category(logs)
    print_group_logs(categ[UNCAT])
    show_categ(categ)

    try:

        last = time()
        while True:
            try:
                log = LogEntry.get_log(time_step)
            except subprocess.CalledProcessError as e:
                print(e)
                sleep(1)
            else:
                logs.append(log)

                cat = ctx.get_cat(log)
                if cat is UNCAT:
                    print(logs[-1])

            time_taken = time() - last
            if time_taken >= time_step:  # for instance lid closed
                time_taken = 0
                last = time()
            else:
                last += time_step

            sleep(time_step - time_taken)

    except BaseException:
        subprocess.call(["notify-send", 'App Watch stopped !', "-a", "app_watch.py"])
        raise


@app_watch.command()
@click.option("--day", "-d", default=0, help="How many days ago. Negative value means all time.")
@click.option("--category", "-c", help="Search only in this category")
@click.option("--pattern", "-p", help="Should contain this pattern")
@click.option("--by-category", "-C", default=False, is_flag=True, help="Whether to print results by category")
@click.option("--total", "-T", default=False, is_flag=True, help="Print only total values, not log entries")
@click.option("--time-line", "-L", default=False, is_flag=True, help="Display logs in a timeline")
@click.option("--time-line-thresold", "-D", default=15,
              help="Minimum seconds of activity to show data on the timeline.")
@logfile_option
@config_option
def query(ctx: Context, logfile, pattern, day, category, total, by_category, time_line, time_line_thresold):
    """Get informations about time spent.

    Lowercase option are for filterning, and uppercase are for the display format."""
    logs = Logs.load(logfile)

    if day >= 0:
        day = datetime.now() + timedelta(days=-day)
        # Start the day at 4AM
        if day.hour < 4:
            day -= DAY
        day = day.replace(hour=4, minute=0)

        logs = ctx.filter_time(logs, day, day + DAY)

    if pattern:
        logs = ctx.filter_pattern(logs, pattern)

    if category:
        logs = ctx.filter_category(logs, category)

    logs = list(logs)

    if not logs:
        print("No matching logs")
        quit(1)

    if by_category:
        categ = ctx.group_category(logs)

        if time_line:
            print_labels(logs[0].start, logs[-1].end)
            for cat, ls in categ.items():
                print_time_line(ctx, ls, logs[0].start, logs[-1].end, show_labels=False,
                                min_sec_to_show=time_line_thresold)
            print_labels(logs[0].start, logs[-1].end)

            print()
            print("Legend:", end=" ")
            print_legend(categ)

        if total:
            show_categ(categ)

        if not total and not time_line:
            for cat, ls in categ.items():
                print("----", cat, "----")
                print_group_logs(ls, total)
                print()
    else:
        if time_line:
            print_time_line(ctx, logs, min_sec_to_show=time_line_thresold)
        else:
            print_group_logs(logs, total)


@app_watch.command("list-cat")
@logfile_option
@config_option
def list_cat(ctx, logfile):
    logs = Logs.load(logfile)

    cats = set()
    for log in logs:
        cats.add(ctx.get_cat(log))

    print(*cats, sep="\n")
