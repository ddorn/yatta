import os
from collections import defaultdict
from datetime import datetime
from operator import itemgetter
from threading import Thread
from time import sleep

import pygame
from pygame import Vector2 as Vec

from src.context import Context
from src.core import AFK, DAY, LogEntry, Logs, UNCAT
from src.utils import int_to_rgb, notify, sec2str, start_of_day


class Gui:
    ROW_IDEAL_SIZE = 60
    FPS = 1 / 3  # We don't need more than 3 FPS :P

    def __init__(self, ctx: Context, logs: Logs):
        pygame.init()

        self.ctx = ctx
        self.logs = logs
        self.size = (200, 300)
        self.durs = defaultdict(int)
        self.next_day = start_of_day(datetime.now()) + DAY

        self.display = self.get_display(self.size)
        pygame.display.set_caption("Yatta")
        self.font = pygame.font.SysFont("sourcecodeproforpowerline", 20, bold=True)

    @property
    def rows(self):
        return self.size[1] // self.ROW_IDEAL_SIZE or 1

    def get_display(self, size) -> pygame.Surface:
        self.size = size
        return pygame.display.set_mode(self.size, pygame.RESIZABLE)

    def run(self):
        self.compute_durs()

        thread = Thread(target=self.logs.watch_apps, args=(1, self.draw))
        thread.start()

        try:
            while thread.is_alive():
                for event in pygame.event.get():
                    self.process_event(event)

                # If day changes, take the cats for the correct day
                if datetime.now() >= self.next_day:
                    self.compute_durs()
                    self.next_day = start_of_day(datetime.now()) + DAY
                    self.display.fill(0)

                pygame.display.update()
                sleep(self.FPS)

                # Note: we don't draw the screen here. It is redrawn only on new
                # Log entries (callback of the thread)
        finally:
            self.logs.stop()

    def process_event(self, event):
        if event.type == pygame.QUIT:
            self.logs.stop()
        elif event.type == pygame.VIDEORESIZE:
            self.display = self.get_display(event.size)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                self.ctx.reload()
                self.compute_durs()
            elif event.unicode.isdigit():
                self.display = self.get_display((self.size[0], int(event.unicode) * self.ROW_IDEAL_SIZE))

        self.ctx.shortcuts(event)

    def draw_cat(self, cat, seconds):
        """Return a surface with the caegory drawn."""
        bg = int_to_rgb(cat.bg)
        fg = int_to_rgb(cat.fg)

        # Background
        drawing = pygame.Surface((self.size[0], self.size[1] // self.rows))
        drawing.fill(bg)
        rect = drawing.get_rect()

        # Time
        txt = sec2str(seconds)
        surf = self.font.render(txt, True, fg, bg)
        r = surf.get_rect(bottomright=rect.bottomright - Vec(5, 5))
        drawing.blit(surf, r)

        # Category
        surf = self.font.render(str(cat), True, fg, bg)
        drawing.blit(surf, (5, 5))

        return drawing

    def draw(self, log: LogEntry):
        """Render the whole screen."""

        self.display.fill(0)
        # The screen is drawn every time there is a new log entry
        # since there is no point in painting it more
        cat = self.ctx.get_cat(log)

        if cat is UNCAT:
            print(log)
        self.durs[cat] += log.duration

        # Send a notification every 15 minutes of an activity
        if self.durs[cat] % (15 * 60) < 1:
            notify(f"Déjà {self.durs[cat] // 60}min passées sur {cat}.")
            if cat in self.ctx.lock15:
                os.system("i3lock")

        # Draw the current actvity on top
        surf = self.draw_cat(cat, self.durs[cat])
        self.display.blit(surf, (0, 0))

        # Then the rest, sorted
        bests = sorted(self.durs.items(), key=itemgetter(1), reverse=True)
        bests = [x for x in bests if x[0] not in (cat, AFK)]

        for i, (c, dur) in enumerate(bests):
            surf = self.draw_cat(c, dur)
            self.display.blit(surf, (0, self.size[1] // self.rows * (i + 1)))

    def compute_durs(self):
        """Populate the duration dict"""
        cats = self.ctx.group_category(self.ctx.filter_today(self.logs))
        self.durs.clear()
        self.durs.update({c: self.ctx.tot_secs(ls) for c, ls in cats.items()})
