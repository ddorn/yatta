from collections import defaultdict
from datetime import datetime
from operator import itemgetter
from threading import Thread
from time import sleep

import pygame
from pygame import Vector2 as V

from src.context import Context
from src.core import Logs, DAY, LogEntry, AFK, UNCAT
from src.utils import start_of_day, sec2str, int_to_rgb


def gui(ctx: Context, logs: Logs):
    SIZE = (200, 300)
    ROWS = 5

    pygame.init()
    display = pygame.display.set_mode(SIZE)
    pygame.display.set_caption("Yatta")

    font = pygame.font.SysFont("sourcecodeproforpowerline", 20)
    print(pygame.font.get_fonts(), sep="\n")

    def draw_cat(cat, seconds):
        bg = int_to_rgb(cat.bg)
        fg = int_to_rgb(cat.fg)

        # Background
        drawing = pygame.Surface((SIZE[0], SIZE[1] // ROWS))
        drawing.fill(bg)
        rect = drawing.get_rect()

        # Time
        txt = sec2str(seconds)
        surf = font.render(txt, True, fg, bg)
        r = surf.get_rect(bottomright=rect.bottomright - V(5, 5))
        drawing.blit(surf, r)

        # Category
        surf = font.render(str(cat), True, fg, bg)
        drawing.blit(surf, (5, 5))

        return drawing

    def draw_screen(log: LogEntry):
        cat = ctx.get_cat(log)

        if cat is UNCAT:
            print(log)
        durs[cat] += log.duration

        surf = draw_cat(cat, durs[cat])
        display.blit(surf, (0, 0))

        bests = sorted(durs.items(), key=itemgetter(1), reverse=True)
        bests = [x for x in bests if x[0] not in (cat, AFK)]

        for i, (c, dur) in enumerate(bests):
            surf = draw_cat(c, dur)
            display.blit(surf, (0, SIZE[1] // ROWS * (i + 1)))

    cats = ctx.group_category(ctx.filter_today(logs))
    durs = defaultdict(int, {c: ctx.tot_secs(ls) for c, ls in cats.items()})
    next_day = start_of_day(datetime.now()) + DAY

    thread = Thread(target=logs.watch_apps, args=(1, draw_screen))
    thread.start()

    try:
        while thread.is_alive():
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    logs.stop()
                elif event.type == pygame.KEYDOWN:
                    pass

            # If day changes, take the cats for the correct day
            if datetime.now() >= next_day:
                cats = ctx.group_category(ctx.filter_today(logs))
                durs.clear()
                durs.update({c: ctx.tot_secs(ls) for c, ls in cats.items()})
                next_day = start_of_day(datetime.now()) + DAY
                display.fill(0)

            pygame.display.update()
            sleep(0.5)  # We don't need more than 2 FPS :P
    finally:
        logs.stop()
