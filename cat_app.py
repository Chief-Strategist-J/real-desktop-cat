#!/usr/bin/env python3
"""
Autonomous Photorealistic Desktop Cat Companion
===============================================
Features:
- Full 2D (X & Y Axis) Mouse Cursor Tracking & Following
- Active Keyboard Typing Detection with Cute Reactions
- 100+ Real Cat Library Gallery
- Photorealistic Transparency (GNOME / X11)
- Clean OOP Modular Architecture & Single-Instance Lock
"""

import ctypes
from enum import Enum, auto
import fcntl
import json
import math
import os
import random
import signal
import subprocess
import sys
import time

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib
import cairo

# ---------------------------------------------------------------------------
# Constants & Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(SCRIPT_DIR, 'assets')
CATS_GALLERY_DIR = os.path.join(ASSETS_DIR, 'cats')
LOCK_FILE_PATH = '/tmp/desktop_cat_instance.lock'

CONFIRMED_CATS = {
    "golden": "golden-chinchilla.gif",  # Real golden cat resting on mat
    "fluffy": "finn.gif",               # Real fluffy longhair cat standing
    "ragdoll": "ragdoll.gif",           # Real fluffy ragdoll cat
    "tuxedo": "mustache-cat.gif",       # Real tuxedo cat
    "bengal": "bengal.gif",             # Real Bengal cat
    "exotic": "garfield.gif"            # Real exotic shorthair cat
}

CAT_THOUGHTS = [
    "Purrrrr... following your cursor! 🐾",
    "Remember to stay hydrated! 💧",
    "Deep focus mode activated! 💻✨",
    "Stretch your shoulders for 5s! 🧘",
    "You're doing great today! 🌟",
    "Watching you code... very impressive! ⌨️",
    "Rest your eyes: look 20 feet away for 20s! 🌿",
    "*content cat purrs* ❤️",
    "Following your mouse anywhere on screen! 🐾"
]

TYPING_CHEERS = [
    "🔥 Typing frenzy! You're in the zone!",
    "💻 Speed coder at work! *paw cheers*",
    "⚡ Furious typing detected! Keep rocking!",
    "🐾 *tap tap tap* Bongo paws in sync!",
    "✨ 100x engineer speed unlocked!",
    "🚀 Rapid keystrokes! Let's ship it!"
]


# ---------------------------------------------------------------------------
# X11 Keyboard Activity Detector (Pure Ctypes, Zero sudo required)
# ---------------------------------------------------------------------------
class X11KeyboardDetector:
    """Detects global keyboard typing activity across any window in X11."""
    def __init__(self):
        self.available = False
        self.display = None
        try:
            self.x11 = ctypes.cdll.LoadLibrary('libX11.so.6')
            self.x11.XOpenDisplay.restype = ctypes.c_void_p
            self.x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
            self.x11.XQueryKeymap.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
            self.x11.XCloseDisplay.argtypes = [ctypes.c_void_p]

            self.display = self.x11.XOpenDisplay(None)
            if self.display:
                self.available = True
                self.prev_keys = (ctypes.c_char * 32)()
                self.x11.XQueryKeymap(self.display, self.prev_keys)
        except Exception:
            self.available = False

    def is_typing(self) -> bool:
        if not self.available or not self.display:
            return False
        current_keys = (ctypes.c_char * 32)()
        self.x11.XQueryKeymap(self.display, current_keys)
        
        for b in bytes(current_keys):
            if b != 0:
                return True
        return False

    def close(self):
        if self.available and self.display:
            try:
                self.x11.XCloseDisplay(self.display)
                self.display = None
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Single-Instance Guard
# ---------------------------------------------------------------------------
class SingleInstanceGuard:
    def __init__(self, lock_path: str):
        self.lock_path = lock_path
        self.lock_file = None

    def acquire(self) -> bool:
        try:
            self.lock_file = open(self.lock_path, 'w')
            fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_file.write(str(os.getpid()))
            self.lock_file.flush()
            return True
        except (IOError, OSError):
            return False

    def release(self):
        if self.lock_file:
            try:
                fcntl.flock(self.lock_file, fcntl.LOCK_UN)
                self.lock_file.close()
                if os.path.exists(self.lock_path):
                    os.remove(self.lock_path)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# State & Autonomous Behavior
# ---------------------------------------------------------------------------
class CatState(Enum):
    RESTING = auto()       # Lying down / resting on mat
    FOLLOWING = auto()     # Actively moving & following mouse in 2D (X & Y)
    TYPING_CHEER = auto()  # Cheering when typing is detected
    ALERT = auto()         # Sitting alert


class AutonomousCatBrain:
    def __init__(self, screen_w: int, screen_h: int):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.current_state = CatState.RESTING
        self.state_time_remaining = 6.0
        self.follow_mouse = True
        self.target_x = 0.0
        self.target_y = 0.0
        self.last_typing_time = 0.0

    def tick(self, dt: float, current_x: float, current_y: float, mouse_x: int, mouse_y: int, is_typing: bool) -> tuple[CatState, bool]:
        now = time.time()

        # Handle Keyboard Typing Detection
        if is_typing:
            self.last_typing_time = now
            if self.current_state != CatState.TYPING_CHEER:
                self.current_state = CatState.TYPING_CHEER
                self.state_time_remaining = 3.0
                return self.current_state, True

        if now - self.last_typing_time < 2.5:
            return self.current_state, False

        # Real-time Full 2D (X & Y) Mouse Cursor Tracking
        if self.follow_mouse:
            # Position cat slightly offset from cursor so it doesn't cover click targets
            target_x = float(max(20, min(self.screen_w - 300, mouse_x + 40)))
            target_y = float(max(40, min(self.screen_h - 220, mouse_y - 30)))

            dx = target_x - current_x
            dy = target_y - current_y
            dist = math.hypot(dx, dy)

            # Relaxed cat behavior: only get up and follow when mouse is far enough
            if dist > 140:
                self.target_x = target_x
                self.target_y = target_y
                if self.current_state != CatState.FOLLOWING:
                    self.current_state = CatState.FOLLOWING
                    return self.current_state, True
            elif dist <= 75 and self.current_state == CatState.FOLLOWING:
                # Reached comfortably near cursor -> sit down and relax
                self.current_state = CatState.RESTING
                self.state_time_remaining = random.uniform(10.0, 20.0)
                return self.current_state, True
            elif self.current_state == CatState.FOLLOWING:
                # Keep tracking target smoothly while walking
                self.target_x = target_x
                self.target_y = target_y

        # Autonomous gentle roaming when mouse is still
        self.state_time_remaining -= dt
        if self.state_time_remaining <= 0:
            if self.current_state == CatState.RESTING:
                self.current_state = CatState.FOLLOWING
                self.state_time_remaining = random.uniform(8.0, 14.0)
                self.target_x = float(random.randint(80, max(120, self.screen_w - 360)))
                self.target_y = float(random.randint(60, max(100, self.screen_h - 240)))
                return self.current_state, True
            else:
                self.current_state = CatState.RESTING
                self.state_time_remaining = random.uniform(15.0, 30.0)
                return self.current_state, True

        return self.current_state, False


# ---------------------------------------------------------------------------
# Desktop Cat Window & Controller
# ---------------------------------------------------------------------------
class DesktopCatWindow(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)

        self.set_title("Real Desktop Cat")
        self.set_decorated(False)
        self.set_keep_above(True)
        self.stick()  # Visible on all workspaces
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_app_paintable(True)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)

        display = Gdk.Display.get_default()
        self.pointer_device = display.get_default_seat().get_pointer()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        geom = monitor.get_geometry()
        self.screen_w = geom.width
        self.screen_h = geom.height

        self.brain = AutonomousCatBrain(self.screen_w, self.screen_h)
        self.kb_detector = X11KeyboardDetector()

        # Layout
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.add(self.vbox)

        # Thought / Cheer Bubble
        self.bubble_box = Gtk.EventBox()
        self.bubble_label = Gtk.Label()
        self.bubble_box.add(self.bubble_label)
        self.bubble_box.set_halign(Gtk.Align.CENTER)
        self.vbox.pack_start(self.bubble_box, False, False, 0)
        self.bubble_box.hide()

        # Real Cat Image Widget
        self.image_widget = Gtk.Image()
        self.vbox.pack_start(self.image_widget, True, True, 0)

        # Initial Position
        self.pos_x = float(self.screen_w - 380)
        self.pos_y = float(self.screen_h - 240)
        self.move(int(self.pos_x), int(self.pos_y))

        self.speed = 1.5  # Gentle, calm walking pace (smooth 2D strolling)
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.last_click_time = 0
        self.last_cheer_time = 0

        self._load_cat_anim("golden")

        # Events
        self.connect('draw', self._on_draw)
        self.connect('button-press-event', self._on_button_press)
        self.connect('button-release-event', self._on_button_release)
        self.connect('motion-notify-event', self._on_motion_notify)
        self.connect('destroy', self._on_destroy)

        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
        )

        # 30 FPS Main Loop
        GLib.timeout_add(33, self._on_frame_tick)
        GLib.timeout_add_seconds(45, self._on_thought_tick)
        GLib.timeout_add_seconds(1, lambda: self.show_bubble("Purrrrr... gentle 2D tracking active! 🐾", 5))

    def _load_cat_anim(self, cat_key: str):
        fname = CONFIRMED_CATS.get(cat_key, "golden-chinchilla.gif")
        full_path = os.path.join(ASSETS_DIR, fname)
        if os.path.exists(full_path):
            anim = GdkPixbuf.PixbufAnimation.new_from_file(full_path)
            self.image_widget.set_from_animation(anim)
            self.resize(anim.get_width() + 20, anim.get_height() + 50)

    def _load_random_gallery_cat(self):
        if os.path.exists(CATS_GALLERY_DIR):
            files = [f for f in os.listdir(CATS_GALLERY_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
            if files:
                choice = random.choice(files)
                full_path = os.path.join(CATS_GALLERY_DIR, choice)
                try:
                    pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(full_path, 220, 160, True)
                    self.image_widget.set_from_pixbuf(pb)
                    self.show_bubble(f"📸 Gallery Cat: {choice}", 3)
                except Exception:
                    pass

    def _on_frame_tick(self) -> bool:
        dt = 0.033
        now = time.time()

        # 1. Query Mouse Position (Both X and Y)
        try:
            _, mouse_x, mouse_y = self.pointer_device.get_position()
        except Exception:
            mouse_x, mouse_y = int(self.pos_x), int(self.pos_y)

        # 2. Query Keyboard Typing Activity
        is_typing = self.kb_detector.is_typing()
        if is_typing and (now - self.last_cheer_time > 8.0):
            self.last_cheer_time = now
            self.show_bubble(random.choice(TYPING_CHEERS), 3)

        # 3. Brain Tick (Full 2D)
        state, changed = self.brain.tick(dt, self.pos_x, self.pos_y, mouse_x, mouse_y, is_typing)

        if changed and not self.dragging:
            if state == CatState.FOLLOWING:
                self._load_cat_anim("fluffy")  # Standing fluffy cat when moving
            elif state == CatState.TYPING_CHEER:
                self._load_cat_anim("bengal")  # Active alert Bengal cat when coding
            else:
                self._load_cat_anim("golden")  # Resting golden cat on mat

        # 4. Gentle & Smooth 2D Vector Movement towards target with easing
        if state == CatState.FOLLOWING and not self.dragging:
            dx = self.brain.target_x - self.pos_x
            dy = self.brain.target_y - self.pos_y
            dist = math.hypot(dx, dy)

            # Smooth deceleration easing when getting close
            step = min(self.speed, max(0.4, dist * 0.015))

            if dist <= step:
                self.pos_x = self.brain.target_x
                self.pos_y = self.brain.target_y
            else:
                self.pos_x += (dx / dist) * step
                self.pos_y += (dy / dist) * step

                min_x = 20.0
                max_x = float(self.screen_w - 300)
                min_y = 30.0
                max_y = float(self.screen_h - 220)

                self.pos_x = max(min_x, min(max_x, self.pos_x))
                self.pos_y = max(min_y, min(max_y, self.pos_y))
                self.move(int(self.pos_x), int(self.pos_y))

        self.queue_draw()
        return True

    def _on_thought_tick(self) -> bool:
        if not self.dragging and self.brain.current_state == CatState.RESTING:
            self.show_bubble(random.choice(CAT_THOUGHTS), 4)
        return True

    def show_bubble(self, text: str, duration: int = 4):
        styled = f"<span background='#11111bcc' foreground='#f5e0dc' weight='bold' size='medium'>  {text}  </span>"
        self.bubble_label.set_markup(styled)
        self.bubble_box.show_all()
        try:
            subprocess.Popen(['paplay', '/usr/share/sounds/sound-icons/gummy-cat-2.wav'], stderr=subprocess.DEVNULL)
        except Exception:
            pass

        GLib.timeout_add_seconds(duration, lambda: (self.bubble_box.hide(), False)[1])

    def _on_draw(self, widget, cr):
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        return False

    def _on_button_press(self, widget, event):
        now = time.time()
        if event.button == 1:
            if now - self.last_click_time < 0.35:
                self.brain.current_state = CatState.RESTING
                self.brain.state_time_remaining = 15.0
                self._load_cat_anim("golden")
                self.show_bubble("Purrrrrr... ❤️ (Happy cat purrs!)", 4)
            else:
                self.dragging = True
                pos = self.get_position()
                self.drag_start_x = event.x_root - pos[0]
                self.drag_start_y = event.y_root - pos[1]
            self.last_click_time = now
        elif event.button == 3:
            self._show_context_menu(event)

    def _on_button_release(self, widget, event):
        if event.button == 1:
            self.dragging = False
            pos = self.get_position()
            self.pos_x = float(pos[0])
            self.pos_y = float(pos[1])

    def _on_motion_notify(self, widget, event):
        if self.dragging:
            self.pos_x = float(event.x_root - self.drag_start_x)
            self.pos_y = float(event.y_root - self.drag_start_y)
            self.move(int(self.pos_x), int(self.pos_y))

    def _show_context_menu(self, event):
        menu = Gtk.Menu()

        follow_item = Gtk.CheckMenuItem(label="Full 2D Mouse Cursor Following 🖱️🐾")
        follow_item.set_active(self.brain.follow_mouse)
        def toggle_follow(w):
            self.brain.follow_mouse = w.get_active()
            msg = "Following mouse everywhere in 2D! 🐾" if self.brain.follow_mouse else "Staying in place! 💤"
            self.show_bubble(msg, 3)
        follow_item.connect("toggled", toggle_follow)
        menu.append(follow_item)

        speed_item = Gtk.MenuItem(label="Walking Pace / Speed 🐾")
        speed_menu = Gtk.Menu()
        speed_item.set_submenu(speed_menu)
        speed_levels = [
            ("🐾 Gentle Stroll (Default - Slow & Cute)", 1.5),
            ("🍃 Super Slow & Calm Meander", 0.9),
            ("🚶 Moderate Pace", 2.4),
        ]
        for label, spd in speed_levels:
            it = Gtk.MenuItem(label=label)
            it.connect("activate", lambda w, s=spd: (setattr(self, 'speed', s), self.show_bubble(f"Speed set to {s} px/frame 🐾", 3)))
            speed_menu.append(it)
        menu.append(speed_item)

        gallery_item = Gtk.MenuItem(label="Random 100+ Cat Gallery 📸")
        gallery_item.connect("activate", lambda w: self._load_random_gallery_cat())
        menu.append(gallery_item)

        menu.append(Gtk.SeparatorMenuItem())

        pet_item = Gtk.MenuItem(label="Pet Cat ❤️ (or Double-Click)")
        pet_item.connect("activate", lambda w: (
            setattr(self.brain, 'current_state', CatState.RESTING),
            setattr(self.brain, 'state_time_remaining', 15.0),
            self._load_cat_anim("golden"),
            self.show_bubble("Purrrrr... ❤️", 3)
        ))
        menu.append(pet_item)

        feed_item = Gtk.MenuItem(label="Feed Tuna Fish 🐟")
        feed_item.connect("activate", lambda w: (
            setattr(self.brain, 'current_state', CatState.RESTING),
            setattr(self.brain, 'state_time_remaining', 20.0),
            self._load_cat_anim("golden"),
            self.show_bubble("🐟 *munch munch* Delicious tuna! Thank you! 😋", 4)
        ))
        menu.append(feed_item)

        menu.append(Gtk.SeparatorMenuItem())

        # Select favorite cat
        cats_item = Gtk.MenuItem(label="Choose Real Cat Breed 🐱")
        cats_menu = Gtk.Menu()
        cats_item.set_submenu(cats_menu)

        cat_list = [
            ("Golden Tabby Cat (Resting on Mat) 🐱", "golden"),
            ("Fluffy Longhair Cat 🐱", "fluffy"),
            ("Fluffy Ragdoll Cat 🐱", "ragdoll"),
            ("Tuxedo Mustache Cat 🐱", "tuxedo"),
            ("Bengal Leopard Cat 🐱", "bengal"),
            ("Exotic Shorthair Cat 🐱", "exotic")
        ]
        for label, key in cat_list:
            it = Gtk.MenuItem(label=label)
            it.connect("activate", lambda w, k=key: self._load_cat_anim(k))
            cats_menu.append(it)
        menu.append(cats_item)

        menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="Close Cat ❌")
        quit_item.connect("activate", lambda w: Gtk.main_quit())
        menu.append(quit_item)

        menu.show_all()
        menu.popup_at_pointer(event)

    def _on_destroy(self, widget):
        self.kb_detector.close()
        Gtk.main_quit()


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.signal(signal.SIGTERM, lambda s, f: Gtk.main_quit())

    guard = SingleInstanceGuard(LOCK_FILE_PATH)
    if not guard.acquire():
        try:
            with open(LOCK_FILE_PATH, 'r') as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, signal.SIGTERM)
            time.sleep(0.5)
        except Exception:
            pass
        if not guard.acquire():
            sys.exit(0)

    try:
        window = DesktopCatWindow()
        window.show_all()
        window.present()
        Gtk.main()
    finally:
        guard.release()


if __name__ == '__main__':
    main()
