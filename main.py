"""
Manuals

UI interaction:
- Hold left mouse button on circle and move cursor for moving this circle
- Press R on circle to remove it. You can't remove a photon source
- Click on Add button in bottom left corner for add new random circle
- Click on Set vars button in bottom left corner for set up some system parameters
- Spin wheel up and down with cursor on circle to resize it
- Press C to clear all photons
- Press right mouse button on photon source to start or stop emission
- Press Escape to exit

Vars:
- Random axis value is a range of random values (from -value to value) by which some parameters of photon motion are
  changed for their greater naturalness.
- Probability of photon absorption - the probability of photon absorption by an object in a collision
  (from 0 to 1, where 0 is never, 1 is always)
- Ticks period of photons spawn - once in how many frames a new generation of photons is created
- Degrees step of photons generation - the step of the degree of the photon flight angle (set to range(0, 360, step))
- Photon size - the length of the side of the square of the photon

"""

import math
import os
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
import random
from typing import Optional
import tkinter as tk

import pygame
import pygame_widgets
from pygame_widgets.button import Button

axis_value = 0.2
axis = lambda: random.uniform(-axis_value, axis_value)
pygame.init()


@dataclass
class Point:
    x: float
    y: float

    def distance(self, other: 'Point') -> float:
        return math.dist((self.x, self.y), (other.x, other.y))

    @property
    def as_t(self) -> tuple[float, float]:
        return self.x, self.y


class Figure(ABC):
    __objects__ = []
    mid: Point
    surface: pygame.Surface

    def __new__(cls, *args, **kwargs):
        o = super().__new__(cls)
        Figure.__objects__.append(o)
        cls.__objects__.append(o)
        return o

    @abstractmethod
    def collide(self, p: Point) -> bool:
        ...

    @abstractmethod
    def blit(self) -> None:
        ...

    @abstractmethod
    def listen(self, events: list[pygame.event.Event]) -> None:
        ...


class Circle(Figure):
    __objects__ = []
    ate_probability = 0.3

    def __init__(self, mid: Point, radius: int, surface: pygame.Surface, color: str = "white"):
        self.mid = mid
        self.radius = radius
        self.surface = surface
        self.activated_movement = False
        self.color = color

    def collide(self, p: Point) -> bool:
        return self.mid.distance(p) <= self.radius

    def blit(self) -> None:
        pygame.draw.circle(self.surface, self.color, self.mid.as_t, self.radius)

    def listen(self, events: list[pygame.event.Event]) -> None:
        for e in events:
            if e.type == pygame.MOUSEMOTION and self.activated_movement:
                self.mid = Point(*e.pos)
            if e.type == pygame.MOUSEBUTTONDOWN and self.collide(Point(*e.pos)) and e.button == 1:
                self.activated_movement = True
            if e.type == pygame.MOUSEBUTTONUP and self.activated_movement and e.button == 1:
                self.activated_movement = False
            if e.type == pygame.MOUSEWHEEL and self.collide(Point(*pygame.mouse.get_pos())):
                self.radius = max(5, self.radius + 5 * e.y)
            if e.type == pygame.KEYDOWN and e.key == pygame.K_r and self.collide(Point(*pygame.mouse.get_pos())):
                self.__objects__.remove(self)
                Figure.__objects__.remove(self)
                del self
                return

    def compute_photon(self, p: 'Photon') -> Optional['Photon']:
        if self.mid.distance(p.coord) <= self.radius - 1 or random.random() < self.ate_probability:
            return None
        r_vec = pygame.math.Vector2(p.coord.x - self.mid.x, p.coord.y - self.mid.y)
        p_vec = pygame.math.Vector2(math.cos(p.angle), math.sin(p.angle))
        reflection = p_vec.reflect(r_vec)
        p.angle = math.atan2(reflection.y, reflection.x) + axis()
        return p


class Photon:
    colors = ["white", "purple", "blue", "aqua", "green", "yellow", "orange", "red"]
    p_size = 1

    def __init__(self, coord: Point, angle: float, surface: pygame.Surface):
        self.coord = coord
        self.angle = angle
        self.surface = surface
        self.n_reflections = 0

    def blit(self) -> Optional[int]:
        self.coord = Point(self.coord.x + math.cos(self.angle) + axis() / 2,
                           self.coord.y + math.sin(self.angle) + axis() / 2)
        if not (0 <= self.coord.x <= d_w and 0 <= self.coord.y <= d_h):
            del self
            return -1
        for fig in Figure.__objects__:
            if fig.collide(self.coord):
                if not fig.compute_photon(self):
                    del self
                    return -1
                self.n_reflections += 1
                if self.n_reflections >= len(self.colors):
                    del self
                    return -1
        pixel = pygame.rect.Rect(*self.coord.as_t, self.p_size, self.p_size)
        self.surface.fill(self.colors[self.n_reflections], pixel)


class PhotonSource(Circle):
    __objects__ = []
    photons: list[Photon] = []
    ticks = 0
    frequency = 20
    rays_step = 2
    enabled = True

    def generate_photons(self):
        self.photons += [
            Photon(
                Point(self.mid.x + (self.radius + 1) * math.cos(a), self.mid.y + (self.radius + 1) * math.sin(a) + 1),
                a,
                self.surface) for a in map(lambda angle: math.pi * angle / 180 + axis(), range(0, 360, self.rays_step))]

    def move_photons(self) -> None:
        for p in self.photons:
            if p.blit() == -1:
                self.photons.remove(p)

    def emit(self) -> None:
        self.ticks += 1
        if self.ticks % self.frequency == 0:
            if self.enabled:
                self.generate_photons()
            self.ticks = 0
        self.move_photons()

    def listen(self, events: list[pygame.event.Event]) -> None:
        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 3 and self.collide(Point(*e.pos)):
                self.enabled = not self.enabled
            if e.type == pygame.KEYDOWN and e.key == pygame.K_c:
                self.photons.clear()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_r:
                return
        return super().listen(events)


class VarsRegistry(tk.Tk):
    __instance__ = None

    def __new__(cls):
        if cls.__instance__ is None:
            cls.__instance__ = super().__new__(cls)
        return cls.__instance__

    def __init__(self, *args, **kwargs):
        self.active = False
        tk.Tk.__init__(self, *args, **kwargs)
        self.title("Settings")
        self.axis_d = tk.Label(text="Random axis value (float)")
        self.axis_e = tk.Entry()
        self.axis_d.pack(anchor=tk.NW, padx=20, pady=2)
        self.axis_e.pack(anchor=tk.NW, padx=20, pady=2)
        self.axis_e.insert(0, str(axis_value))
        self.ate_d = tk.Label(text="Probability of photon absorption (float)")
        self.ate_e = tk.Entry()
        self.ate_e.insert(0, str(Circle.ate_probability))
        self.ate_d.pack(anchor=tk.NW, padx=20, pady=2)
        self.ate_e.pack(anchor=tk.NW, padx=20, pady=2)
        self.ticks_d = tk.Label(text="Ticks period of photons spawn (int)")
        self.ticks_e = tk.Entry()
        self.ticks_e.insert(0, str(PhotonSource.frequency))
        self.ticks_d.pack(anchor=tk.NW, padx=20, pady=2)
        self.ticks_e.pack(anchor=tk.NW, padx=20, pady=2)
        self.ray_d = tk.Label(text="Degrees step of photons generation (int)")
        self.ray_e = tk.Entry()
        self.ray_e.insert(0, str(PhotonSource.rays_step))
        self.ray_d.pack(anchor=tk.NW, padx=20, pady=2)
        self.ray_e.pack(anchor=tk.NW, padx=20, pady=2)
        self.p_size_d = tk.Label(text="Photon size (int)")
        self.p_size_e = tk.Entry()
        self.p_size_e.insert(0, str(Photon.p_size))
        self.p_size_d.pack(anchor=tk.NW, padx=20, pady=2)
        self.p_size_e.pack(anchor=tk.NW, padx=20, pady=2)
        self.btn = tk.Button(text="   Set   ", command=self.accept_all)
        self.btn.pack(anchor=tk.NW, padx=20, pady=10)
        self.geometry("320x300")
        self.resizable(width=False, height=False)
        self.protocol("WM_DELETE_WINDOW", self.deactivate)
        self.withdraw()

    def deactivate(self):
        self.active = False
        self.withdraw()

    def accept_all(self):
        global axis_value

        try:
            axis_value = float(self.axis_e.get().strip().replace(",", "."))
        except ValueError:
            self.axis_e.delete(0, tk.END)
            self.axis_e.insert(0, str(axis_value))
        try:
            Circle.ate_probability = float(self.ate_e.get().strip().replace(",", "."))
        except ValueError:
            self.ate_e.delete(0, tk.END)
            self.ate_e.insert(0, str(Circle.ate_probability))
        try:
            PhotonSource.frequency = int(self.ticks_e.get().strip())
        except ValueError:
            self.ticks_e.delete(0, tk.END)
            self.ticks_e.insert(0, str(PhotonSource.frequency))
        try:
            PhotonSource.rays_step = int(self.ray_e.get().strip())
        except ValueError:
            self.ray_e.delete(0, tk.END)
            self.ray_e.insert(0, str(PhotonSource.rays_step))
        try:
            Photon.p_size = int(self.p_size_e.get().strip())
        except ValueError:
            self.p_size_e.delete(0, tk.END)
            self.p_size_e.insert(0, str(Photon.p_size))

    def activate(self):
        if self.active:
            self.focus_force()
            return
        self.active = True
        self.deiconify()


def editor_runner():
    editor = VarsRegistry()
    editor.mainloop()


threading.Thread(target=editor_runner).start()
screen = pygame.display.set_mode()
d_w, d_h = pygame.display.Info().current_w, pygame.display.Info().current_h
PhotonSource(Point(d_w // 2, d_h // 2), 5, screen, color="lightyellow")

gen_circle = lambda: Circle(Point(random.randint(0, d_w), random.randint(0, d_h)), random.randint(10, 100), screen,
                            "dimgray")
for i in range(4):
    gen_circle()

b_add = Button(screen, d_w - 150, d_h - 75, 100, 50, text="Add", colour="darkslateblue", radius=20,
               hoverColour="darkorchid4",
               onClick=gen_circle)
b_vars = Button(screen, d_w - 275, d_h - 75, 100, 50, text="Set vars", colour="darkslateblue", radius=20,
                hoverColour="darkorchid4",
                onClick=lambda: VarsRegistry.__instance__.activate())

running = True
clock = pygame.time.Clock()
fps_font = pygame.font.SysFont("monospace", 25)

while running:
    event_list = pygame.event.get()
    for event in event_list:
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False
    for obj in Figure.__objects__:
        obj.listen(event_list)
    screen.fill("black")
    for obj in Figure.__objects__:
        obj.blit()
    for obj in PhotonSource.__objects__:
        obj.emit()
    pygame_widgets.update(event_list)
    text = fps_font.render(f"{clock.get_fps():.2f} FPS", True, "white")
    screen.blit(text, text.get_rect(center=(d_w - 100, 50)))
    pygame.display.update()
    clock.tick()

getattr(os, "_exit")(0)
