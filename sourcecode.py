"""
=============================================================================
  LIGHT PUZZLE CHALLENGE
  A hidden-state switch puzzle game built with Python Tkinter + pygame
=============================================================================
  Author  : Academic Project
  Version : 1.0
  Tech    : Python 3.x, Tkinter, pygame, CSV
=============================================================================

  GAME OVERVIEW:
  A set of switches has hidden binary states. A secret target configuration
  is generated at game start. The bulb lights ONLY when the player's current
  configuration exactly matches the target — without ever seeing states.
"""

import tkinter as tk
import random
import csv
import os
import datetime

# Base directory (so assets work regardless of cwd)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Optional pygame — gracefully disabled if not installed
# ---------------------------------------------------------------------------
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("[INFO] pygame not found — audio disabled.")


# ===========================================================================
#  CONSTANTS & COLOUR PALETTE (Deep Space / Neon theme)
# ===========================================================================

C_BG          = "#0d0d1a"    # main window background
C_PANEL       = "#13132b"    # card / panel colour
C_ACCENT      = "#7c3aed"    # purple accent
C_ACCENT2     = "#06b6d4"    # cyan accent
C_BTN         = "#1e1b4b"    # default button face
C_BTN_HOVER   = "#312e81"    # button on hover
C_TEXT        = "#e2e8f0"    # primary text
C_SUBTEXT     = "#94a3b8"    # secondary / muted text
C_GOLD        = "#fbbf24"    # score / highlight colour
C_GREEN       = "#22c55e"    # success / victory colour
C_SWITCH_OFF  = "#334155"    # switch face — hidden state
C_BULB_OFF    = "#1e293b"    # bulb when OFF
C_BULB_ON     = "#fbbf24"    # bulb when ON

# Maps difficulty label to switch count
DIFFICULTY_MAP = {"Easy": 3, "Medium": 5, "Hard": 7}

# Scoring constants
BASE_SCORE    = 1000
CLICK_PENALTY = 5
HINT_PENALTY  = 50
SOLVE_BONUS   = 200
SCORES_FILE   = "scores.csv"
SCORES_FILE   = os.path.join(BASE_DIR, "scores.csv")

# Font definitions
FONT_TITLE  = ("Segoe UI", 28, "bold")
FONT_BODY   = ("Segoe UI", 12)
FONT_SMALL  = ("Segoe UI", 10)
FONT_SWITCH = ("Segoe UI", 11, "bold")
FONT_SCORE  = ("Courier New", 13, "bold")


# ===========================================================================
#  AUDIO MANAGER
# ===========================================================================

class AudioManager:
    """
    Wraps pygame mixer for background music and sound effects.
    Every method silently degrades when pygame is unavailable or
    when the referenced audio file does not exist on disk.
    """

    def __init__(self):
        self.enabled = False
        self.base_dir = BASE_DIR
        if not PYGAME_AVAILABLE:
            return
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.enabled = True
        except Exception as exc:
            print(f"[AUDIO] Mixer init failed: {exc}")

    def _resolve_path(self, path: str) -> str:
        """
        Resolve an asset path robustly.
        - If already absolute, keep it.
        - Otherwise, try alongside this script first, then fall back to cwd.
        """
        if os.path.isabs(path):
            return path
        candidate = os.path.join(self.base_dir, path)
        if os.path.isfile(candidate):
            return candidate

        # Common Windows mistake: duplicate extension (e.g. bg.mp3.mp3)
        root, ext = os.path.splitext(path)
        if ext:
            doubled = os.path.join(self.base_dir, path + ext)
            if os.path.isfile(doubled):
                return doubled
        return path

    def _load_sound(self, path: str):
        """Load and return a pygame Sound, or None on any failure."""
        path = self._resolve_path(path)
        if not self.enabled or not os.path.isfile(path):
            return None
        try:
            return pygame.mixer.Sound(path)
        except Exception as exc:
            print(f"[AUDIO] Load error ({path}): {exc}")
            return None

    def play_music(self, path: str, loops: int = -1):
        """Start looping background music from *path*."""
        path = self._resolve_path(path)
        if not self.enabled or not os.path.isfile(path):
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(0.4)
            pygame.mixer.music.play(loops)
        except Exception as exc:
            print(f"[AUDIO] Music error: {exc}")

    def stop_music(self):
        if self.enabled:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    def play_click(self):
        """Play the click sound effect."""
        snd = self._load_sound("click.wav")
        if snd:
            snd.play()

    def play_win(self):
        """Play the victory sound effect."""
        snd = self._load_sound("win.wav")
        if snd:
            snd.play()


# ===========================================================================
#  LEADERBOARD  (CSV-based persistent storage)
# ===========================================================================

class Leaderboard:
    """
    Manages score persistence using a plain CSV file.

    Schema (CSV columns):
        player_name | difficulty | score | attempts | hints | timestamp

    The CSV is created automatically on first run.
    Scores are sorted by descending score for top-N retrieval.
    """

    HEADERS = ["player_name", "difficulty", "score",
               "attempts", "hints", "timestamp"]

    def __init__(self, filepath: str = SCORES_FILE):
        self.filepath = filepath
        self._ensure_file()

    def _ensure_file(self):
        """Create CSV with header row if the file does not exist."""
        if not os.path.isfile(self.filepath):
            with open(self.filepath, "w", newline="") as f:
                csv.DictWriter(f, fieldnames=self.HEADERS).writeheader()

    def save_entry(self, player: str, difficulty: str,
                   score: int, attempts: int, hints: int):
        """Append one completed-game result to the CSV."""
        row = {
            "player_name": player,
            "difficulty":  difficulty,
            "score":       score,
            "attempts":    attempts,
            "hints":       hints,
            "timestamp":   datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        with open(self.filepath, "a", newline="") as f:
            csv.DictWriter(f, fieldnames=self.HEADERS).writerow(row)

    def load_top(self, n: int = 10) -> list:
        """Read all rows, sort by score descending, return top n."""
        rows = []
        try:
            with open(self.filepath, "r", newline="") as f:
                for row in csv.DictReader(f):
                    try:
                        row["score"] = int(row["score"])
                        rows.append(row)
                    except ValueError:
                        pass
        except FileNotFoundError:
            pass
        rows.sort(key=lambda r: r["score"], reverse=True)
        return rows[:n]


# ===========================================================================
#  PUZZLE ENGINE  (pure logic — no GUI dependencies)
# ===========================================================================

class PuzzleEngine:
    """
    Encapsulates the core hidden-state puzzle logic.

    Attributes
    ----------
    num_switches : int
        Number of switches in this puzzle instance.
    target : list[int]
        The randomly generated secret target configuration (0s and 1s).
    state : list[int]
        The player's current switch configuration (all zeros at start).
    attempts : int
        Total number of switch-click events.
    hints_used : int
        How many hints the player has requested.
    score : int
        Running score, starting at BASE_SCORE.
    solved : bool
        True once state == target.
    """

    def __init__(self, num_switches: int):
        self.num_switches = num_switches
        self.state        = [0] * num_switches
        self.target       = self._generate_target()
        self.attempts     = 0
        self.hints_used   = 0
        self.score        = BASE_SCORE
        self.solved       = False

    def _generate_target(self) -> list:
        """
        Generate a random target config with at least one ON switch.
        Uses rejection sampling to avoid the trivial all-zero config.
        """
        while True:
            t = [random.randint(0, 1) for _ in range(self.num_switches)]
            if any(t):
                return t

    def toggle(self, index: int):
        """
        Toggle switch at *index* using XOR and update score/attempts.
        No-op once the puzzle is already solved.
        """
        if self.solved:
            return
        self.state[index] ^= 1          # binary toggle
        self.attempts += 1
        self.score = max(0, self.score - CLICK_PENALTY)
        self._check_solved()

    def _check_solved(self):
        """Compare state to target; award bonus if matched."""
        if self.state == self.target:
            self.solved = True
            self.score += SOLVE_BONUS

    def get_hint(self) -> str:
        """
        Provide a partial hint: randomly reveal ONE incorrect switch.
        Deducts HINT_PENALTY from score.
        Returns a human-readable hint string.
        """
        self.hints_used += 1
        self.score = max(0, self.score - HINT_PENALTY)
        wrong = [i for i in range(self.num_switches)
                 if self.state[i] != self.target[i]]
        if not wrong:
            return "All switches are already correct!"
        idx = random.choice(wrong)
        return f"Hint: Try changing Switch {idx + 1}.  (-{HINT_PENALTY} pts)"

    def get_reveal_info(self) -> list:
        """
        Return full internal state info for Reveal Mode.
        Returns a list of dicts: {switch, current, target}.
        """
        return [
            {"switch":  i + 1,
             "current": "ON"  if self.state[i]  else "OFF",
             "target":  "ON"  if self.target[i] else "OFF"}
            for i in range(self.num_switches)
        ]


# ===========================================================================
#  ANIMATED STAR-FIELD BACKGROUND
# ===========================================================================

class StarField(tk.Canvas):
    """
    A self-animating parallax star field drawn on a tk.Canvas.
    Stars drift downward and wrap to the top, creating depth illusion.
    Runs at ~33 FPS using Tkinter's after() scheduler.
    """

    NUM_STARS = 100

    def __init__(self, master, **kwargs):
        super().__init__(master, bg=C_BG, highlightthickness=0, **kwargs)
        self._stars   = []
        self._running = True
        self.bind("<Configure>", self._on_resize)
        self._animate()

    def _on_resize(self, event):
        """Regenerate star positions whenever the canvas is resized."""
        self._stars = []
        w, h = event.width, event.height
        for _ in range(self.NUM_STARS):
            x     = random.uniform(0, w)
            y     = random.uniform(0, h)
            size  = random.choice([1, 1, 2, 2, 3])
            speed = random.uniform(0.2, 1.0)
            colour = random.choice(["#ffffff", "#c7d2fe",
                                    "#a5b4fc", "#818cf8"])
            self._stars.append([x, y, size, speed, colour])

    def _animate(self):
        """Main animation loop: move and redraw all stars."""
        if not self._running:
            return
        self.delete("star")
        w = self.winfo_width()
        h = self.winfo_height()
        if w > 1:
            for star in self._stars:
                x, y, size, speed, colour = star
                y += speed
                if y > h:
                    y  = 0
                    x  = random.uniform(0, w)
                star[1] = y
                self.create_oval(x - size, y - size,
                                 x + size, y + size,
                                 fill=colour, outline="", tags="star")
        self.after(30, self._animate)

    def stop(self):
        self._running = False


# ===========================================================================
#  ROUNDED BUTTON WIDGET
# ===========================================================================

class RoundedButton(tk.Canvas):
    """
    Custom canvas-drawn button with rounded corners and hover effect.
    Tkinter's built-in tk.Button cannot render rounded corners, so we
    use arc + rectangle drawing primitives to simulate modern UI buttons.
    """

    def __init__(self, master, text, command=None,
                 bg=C_BTN, hover=C_BTN_HOVER, fg=C_TEXT,
                 width=180, height=44, radius=12,
                 font=FONT_BODY, **kwargs):
        # Inherit master background so canvas border is invisible
        master_bg = C_BG
        try:
            master_bg = master["bg"]
        except Exception:
            pass
        super().__init__(master, width=width, height=height,
                         bg=master_bg, highlightthickness=0, **kwargs)
        self._text    = text
        self._command = command
        self._bg      = bg
        self._hover   = hover
        self._fg      = fg
        self._radius  = radius
        self._font    = font
        self._width   = width
        self._height  = height

        # FIX: defer first draw so canvas is fully registered by Tkinter
        self.after(10, lambda: self._draw(self._bg))

        self.bind("<Enter>",          lambda e: self._draw(self._hover))
        self.bind("<Leave>",          lambda e: self._draw(self._bg))
        self.bind("<ButtonPress-1>",  self._on_press)
        self.bind("<ButtonRelease-1>",self._on_release)

    def _draw(self, colour):
        """Redraw rounded rectangle with current colour."""
        # FIX: guard against drawing on a destroyed widget
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        self.delete("all")
        r, w, h = self._radius, self._width, self._height
        # Four corner arcs
        self.create_arc(0,     0,     2*r, 2*r, start=90,  extent=90,
                        fill=colour, outline="")
        self.create_arc(w-2*r, 0,     w,   2*r, start=0,   extent=90,
                        fill=colour, outline="")
        self.create_arc(0,     h-2*r, 2*r, h,   start=180, extent=90,
                        fill=colour, outline="")
        self.create_arc(w-2*r, h-2*r, w,   h,   start=270, extent=90,
                        fill=colour, outline="")
        # Fill rectangles connecting arcs
        self.create_rectangle(r, 0, w-r, h, fill=colour, outline="")
        self.create_rectangle(0, r, w, h-r, fill=colour, outline="")
        self.create_text(w//2, h//2, text=self._text,
                         fill=self._fg, font=self._font)

    def _on_press(self, _):
        self._draw(C_ACCENT)

    def _on_release(self, _):
        self._draw(self._hover)
        if self._command:
            self._command()


# ===========================================================================
#  BASE SCREEN CLASS
# ===========================================================================

class Screen(tk.Frame):
    """
    Abstract base for all application screens.
    Each screen is a tk.Frame that packs/unpacks itself for navigation.
    """

    def __init__(self, master, controller):
        super().__init__(master, bg=C_BG)
        self.controller = controller

    def show(self):
        self.pack(fill="both", expand=True)

    def hide(self):
        self.pack_forget()


# ===========================================================================
#  MAIN MENU SCREEN
# ===========================================================================

class MenuScreen(Screen):
    """
    Title/landing screen.
    Collects player name, difficulty selection, then launches game or
    navigates to the leaderboard.
    """

    def __init__(self, master, controller):
        super().__init__(master, controller)
        self._build()

    def _build(self):
        # Animated background
        self.canvas = StarField(self, width=800, height=600)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)

        # Central glass-morphism card
        card = tk.Frame(self, bg=C_PANEL, bd=0)
        # Slightly taller to avoid clipping on high-DPI / font scaling
        card.place(relx=0.5, rely=0.5, anchor="center", width=460, height=565)

        # Title
        tk.Label(card, text="💡 LIGHT PUZZLE",
                 bg=C_PANEL, fg=C_GOLD,
                 font=("Segoe UI", 30, "bold")).pack(pady=(26, 2))
        tk.Label(card, text="CHALLENGE",
                 bg=C_PANEL, fg=C_ACCENT2,
                 font=("Segoe UI", 18, "bold")).pack()
        tk.Label(card, text="Crack the hidden switch code",
                 bg=C_PANEL, fg=C_SUBTEXT,
                 font=FONT_SMALL).pack(pady=(4, 20))

        tk.Frame(card, bg=C_ACCENT, height=2).pack(fill="x", padx=40, pady=(0, 16))

        # Player name input
        tk.Label(card, text="Player Name",
                 bg=C_PANEL, fg=C_TEXT, font=FONT_BODY).pack()
        self.name_var = tk.StringVar(value="Player1")
        tk.Entry(card, textvariable=self.name_var,
                 bg="#1e293b", fg=C_TEXT,
                 insertbackground=C_TEXT,
                 relief="flat", font=FONT_BODY,
                 justify="center", width=22).pack(ipady=7, pady=(4, 16))

        # Difficulty radio buttons
        tk.Label(card, text="Select Difficulty",
                 bg=C_PANEL, fg=C_TEXT, font=FONT_BODY).pack()
        self.difficulty_var = tk.StringVar(value="Medium")
        diff_frame = tk.Frame(card, bg=C_PANEL)
        diff_frame.pack(pady=8)

        diff_styles = {
            "Easy":   ("#064e3b", "#6ee7b7"),
            "Medium": ("#1e1b4b", "#818cf8"),
            "Hard":   ("#450a0a", "#fca5a5"),
        }
        for label, (bg, fg) in diff_styles.items():
            tk.Radiobutton(diff_frame,
                           text=f"  {label}  ",
                           variable=self.difficulty_var, value=label,
                           bg=bg, fg=fg,
                           selectcolor=C_ACCENT,
                           activebackground=C_BTN_HOVER,
                           font=("Segoe UI", 11, "bold"),
                           relief="flat", indicatoron=False,
                           padx=12, pady=8).pack(side="left", padx=6)

        tk.Frame(card, bg=C_PANEL, height=12).pack()

        # Navigation buttons
        RoundedButton(card, text="▶  START GAME",
                      command=self._start_game,
                      bg=C_ACCENT, hover="#6d28d9",
                      fg="white", width=220, height=46,
                      font=("Segoe UI", 13, "bold")).pack(pady=4)

        RoundedButton(card, text="🏆  LEADERBOARD",
                      command=self.controller.show_leaderboard,
                      bg=C_BTN, hover=C_BTN_HOVER,
                      fg=C_TEXT, width=220, height=40).pack(pady=4)

        RoundedButton(card, text="✕  QUIT",
                      command=self.controller.root.quit,
                      bg="#450a0a", hover="#7f1d1d",
                      fg="#fca5a5", width=220, height=40).pack(pady=4)

    def _start_game(self):
        name = self.name_var.get().strip() or "Anonymous"
        diff = self.difficulty_var.get()
        self.controller.start_game(name, diff)


# ===========================================================================
#  GAME SCREEN
# ===========================================================================

class GameScreen(Screen):
    """
    The main gameplay view.

    Layout
    ------
    ┌─────────────────────────────────────────────────┐
    │  HUD Bar: ← Menu | Player/Diff | Score Clicks   │
    ├───────────────┬─────────────────────────────────┤
    │  LEFT PANEL   │  RIGHT PANEL                    │
    │  • Bulb       │  • Hint text                    │
    │  • Hint btn   │  • Switch grid  (normal mode)   │
    │  • Reveal btn │  • Reveal info  (reveal mode)   │
    │  • Restart    │  • Victory msg  (after solve)   │
    └───────────────┴─────────────────────────────────┘
    """

    SWITCH_W = 80
    SWITCH_H = 80

    def __init__(self, master, controller):
        super().__init__(master, controller)
        self.engine    : PuzzleEngine = None
        self.player    : str          = ""
        self.difficulty: str          = ""
        self._revealed : bool         = False
        self._switch_btns: list       = []
        self._build_skeleton()

    # ------------------------------------------------------------------
    # Layout construction (called once at instantiation)
    # ------------------------------------------------------------------

    def _build_skeleton(self):
        """Construct the persistent screen layout."""

        # Animated starfield background
        self.bg_canvas = StarField(self)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)

        # ---- HUD bar (top strip) ----
        hud = tk.Frame(self, bg="#0d1117", pady=8)
        hud.pack(fill="x", side="top")

        tk.Button(hud, text="← Menu",
                  bg=C_BTN, fg=C_TEXT, relief="flat",
                  font=FONT_SMALL, cursor="hand2",
                  command=self.controller.show_menu).pack(side="left", padx=12)

        self.lbl_player   = tk.Label(hud, text="", bg="#0d1117",
                                     fg=C_ACCENT2, font=("Segoe UI", 12, "bold"))
        self.lbl_player.pack(side="left", padx=12)

        self.lbl_score    = tk.Label(hud, text="Score: 1000",
                                     bg="#0d1117", fg=C_GOLD, font=FONT_SCORE)
        self.lbl_score.pack(side="right", padx=12)

        self.lbl_attempts = tk.Label(hud, text="Clicks: 0",
                                     bg="#0d1117", fg=C_SUBTEXT, font=FONT_SCORE)
        self.lbl_attempts.pack(side="right", padx=12)

        self.lbl_hints    = tk.Label(hud, text="Hints: 0",
                                     bg="#0d1117", fg=C_SUBTEXT, font=FONT_SCORE)
        self.lbl_hints.pack(side="right", padx=12)

        # ---- Content area (below HUD) ----
        content = tk.Frame(self, bg=C_BG)
        content.pack(expand=True, fill="both", padx=20, pady=10)

        # -- LEFT PANEL --
        left = tk.Frame(content, bg=C_PANEL, padx=20, pady=20)
        left.pack(side="left", fill="y", padx=(0, 16))

        tk.Label(left, text="BULB STATUS",
                 bg=C_PANEL, fg=C_SUBTEXT, font=FONT_SMALL).pack()

        # Bulb canvas
        self.bulb_canvas = tk.Canvas(left, width=140, height=160,
                                     bg=C_PANEL, highlightthickness=0)
        self.bulb_canvas.pack(pady=8)
        self._draw_bulb(on=False)

        self.lbl_bulb_status = tk.Label(left, text="● OFF",
                                        bg=C_PANEL, fg=C_SUBTEXT,
                                        font=("Segoe UI", 13, "bold"))
        self.lbl_bulb_status.pack(pady=(0, 20))

        tk.Frame(left, bg=C_ACCENT2, height=1).pack(fill="x", pady=8)

        # Action buttons (left panel)
        RoundedButton(left, text="💡 HINT",
                      command=self._use_hint,
                      bg="#78350f", hover="#92400e",
                      fg=C_GOLD, width=160, height=40).pack(pady=5)

        RoundedButton(left, text="👁  REVEAL",
                      command=self._toggle_reveal,
                      bg="#0f172a", hover="#1e293b",
                      fg=C_ACCENT2, width=160, height=40).pack(pady=5)

        RoundedButton(left, text="🔄 RESTART",
                      command=self._restart,
                      bg=C_BTN, hover=C_BTN_HOVER,
                      fg=C_TEXT, width=160, height=40).pack(pady=5)

        # -- RIGHT PANEL --
        right = tk.Frame(content, bg=C_BG)
        right.pack(side="left", expand=True, fill="both")

        tk.Label(right, text="SWITCH PANEL",
                 bg=C_BG, fg=C_SUBTEXT, font=FONT_SMALL).pack(pady=(0, 4))

        # Hint text display
        self.hint_lbl = tk.Label(right, text="",
                                 bg=C_BG, fg=C_GOLD,
                                 font=("Segoe UI", 11, "italic"),
                                 wraplength=440)
        self.hint_lbl.pack(pady=(0, 8))

        # Switch grid (shown during normal play)
        self.switch_frame = tk.Frame(right, bg=C_BG)
        self.switch_frame.pack(expand=True)

        # Reveal panel (hidden until reveal is activated)
        self.reveal_frame = tk.Frame(right, bg=C_PANEL, pady=12)
        self.reveal_lbl   = tk.Label(self.reveal_frame, text="",
                                     bg=C_PANEL, fg=C_TEXT,
                                     font=("Courier New", 11), justify="left")
        self.reveal_lbl.pack(padx=20)
        RoundedButton(self.reveal_frame, text="▶ RESUME",
                      command=self._toggle_reveal,
                      bg=C_GREEN, hover="#16a34a",
                      fg="white", width=150, height=36).pack(pady=8)

        # Victory panel (hidden until puzzle is solved)
        self.victory_frame = tk.Frame(right, bg=C_BG)
        tk.Label(self.victory_frame, text="🎉 PUZZLE SOLVED! 🎉",
                 bg=C_BG, fg=C_GREEN,
                 font=("Segoe UI", 22, "bold")).pack(pady=8)
        self.victory_detail = tk.Label(self.victory_frame, text="",
                                       bg=C_BG, fg=C_GOLD,
                                       font=("Segoe UI", 14))
        self.victory_detail.pack()
        RoundedButton(self.victory_frame, text="▶ PLAY AGAIN",
                      command=self._restart,
                      bg=C_GREEN, hover="#16a34a",
                      fg="white", width=200, height=44,
                      font=("Segoe UI", 13, "bold")).pack(pady=12)
        RoundedButton(self.victory_frame, text="🏠 MAIN MENU",
                      command=self.controller.show_menu,
                      bg=C_BTN, hover=C_BTN_HOVER,
                      fg=C_TEXT, width=200, height=40).pack(pady=4)

    # ------------------------------------------------------------------
    # Bulb rendering
    # ------------------------------------------------------------------

    def _draw_bulb(self, on: bool):
        """
        Render the light bulb on bulb_canvas.
        When on=True, draws layered glow rings around a bright core.
        When on=False, draws a dark inactive bulb.
        """
        c = self.bulb_canvas
        c.delete("all")
        cx, cy = 70, 75    # centre of bulb

        if on:
            # Glow rings (outermost to innermost)
            for r, colour in [(55, "#78350f"), (48, "#92400e"),
                               (42, "#b45309"), (36, "#d97706")]:
                c.create_oval(cx-r, cy-r, cx+r, cy+r,
                              fill=colour, outline="")
            # Bright core
            c.create_oval(cx-28, cy-28, cx+28, cy+28,
                          fill=C_BULB_ON, outline="#fef3c7", width=2)
            c.create_line(cx, cy-14, cx, cy+14, fill="white", width=2)
            c.create_line(cx-8, cy-6, cx+8, cy+6, fill="white", width=2)
        else:
            # Dark inactive bulb
            c.create_oval(cx-28, cy-28, cx+28, cy+28,
                          fill=C_BULB_OFF, outline=C_SUBTEXT, width=2)
            c.create_line(cx, cy-14, cx, cy+14, fill=C_SUBTEXT, width=2)

        # Bulb neck / base (same for both states)
        c.create_rectangle(cx-14, cy+26, cx+14, cy+44,
                            fill="#334155", outline="")
        c.create_rectangle(cx-16, cy+44, cx+16, cy+52,
                            fill="#475569", outline="")

    # ------------------------------------------------------------------
    # Round setup
    # ------------------------------------------------------------------

    def setup(self, player: str, difficulty: str):
        """
        Initialise a fresh puzzle round.
        Called by the App controller on Start and Restart.

        Steps:
          1. Create a new PuzzleEngine instance.
          2. Destroy previous switch buttons and build new ones.
          3. Reset all HUD labels, bulb, and panel visibility.
        """
        self.player     = player
        self.difficulty = difficulty
        n               = DIFFICULTY_MAP[difficulty]
        self.engine     = PuzzleEngine(n)
        self._revealed  = False

        # Destroy old switch buttons
        for w in self.switch_frame.winfo_children():
            w.destroy()
        self._switch_btns = []

        self._build_switches(n)

        # Reset HUD
        self.lbl_player.config(text=f"👤 {player}  |  {difficulty}")
        self._refresh_hud()
        self._draw_bulb(on=False)
        self.lbl_bulb_status.config(text="● OFF", fg=C_SUBTEXT)
        self.hint_lbl.config(text="")

        # Ensure only switch_frame is visible
        self.victory_frame.pack_forget()
        self.reveal_frame.pack_forget()
        self.switch_frame.pack(expand=True)

    # ------------------------------------------------------------------
    def _build_switches(self, n: int):
        """
        Create n switch canvases laid out in a responsive grid.
        Maximum 4 switches per row; overflow wraps to next row.
        Switches are cosmetically uniform — they never reveal internal state.
        """
        cols = min(n, 4)
        for i in range(n):
            row_idx = i // cols
            col_idx = i % cols

            wrapper = tk.Frame(self.switch_frame, bg=C_BG)
            wrapper.grid(row=row_idx, column=col_idx, padx=12, pady=12)

            tk.Label(wrapper, text=f"SW {i+1}",
                     bg=C_BG, fg=C_SUBTEXT, font=FONT_SMALL).pack()

            btn = tk.Canvas(wrapper,
                            width=self.SWITCH_W, height=self.SWITCH_H,
                            bg=C_SWITCH_OFF,
                            highlightthickness=2,
                            highlightbackground=C_ACCENT,
                            cursor="hand2")
            btn.pack()
            self._draw_switch_face(btn, clicked=False)

            # Bind events — use default-argument capture to freeze i, btn
            btn.bind("<Button-1>",
                     lambda e, idx=i, b=btn: self._on_switch_click(idx, b))
            btn.bind("<Enter>",
                     lambda e, b=btn: b.config(highlightbackground=C_ACCENT2))
            btn.bind("<Leave>",
                     lambda e, b=btn: b.config(highlightbackground=C_ACCENT))

            self._switch_btns.append(btn)

    # ------------------------------------------------------------------
    def _draw_switch_face(self, btn: tk.Canvas, clicked: bool):
        """
        Render the visual face of a switch.
        The appearance changes on click as visual feedback,
        but does NOT indicate the true internal ON/OFF state.
        """
        btn.delete("all")
        w, h = self.SWITCH_W, self.SWITCH_H

        if clicked:
            bg, icon, label, fg = C_ACCENT, "↺", "CLICKED", "white"
        else:
            bg, icon, label, fg = C_SWITCH_OFF, "?", "PRESS", C_SUBTEXT

        btn.config(bg=bg)
        btn.create_text(w//2, h//2 - 10, text=icon,
                        font=("Segoe UI", 22, "bold"), fill=fg)
        btn.create_text(w//2, h//2 + 16, text=label,
                        font=("Segoe UI", 8), fill=fg)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_switch_click(self, idx: int, btn: tk.Canvas):
        """
        Handle a player's switch click.
          1. Play click sound.
          2. Tell the engine to toggle switch at idx.
          3. Refresh visual feedback on the button.
          4. Update the HUD.
          5. If the engine reports solved → trigger victory.
        """
        if self.engine.solved or self._revealed:
            return

        self.controller.audio.play_click()
        self.engine.toggle(idx)

        # Visual feedback: show clicked state based on parity of state[idx]
        self._draw_switch_face(btn, clicked=(self.engine.state[idx] == 1))
        self._refresh_hud()

        if self.engine.solved:
            self._on_victory()

    def _refresh_hud(self):
        """Synchronise HUD labels with current engine values."""
        self.lbl_score.config(text=f"Score: {self.engine.score}")
        self.lbl_attempts.config(text=f"Clicks: {self.engine.attempts}")
        self.lbl_hints.config(text=f"Hints: {self.engine.hints_used}")

    def _use_hint(self):
        """Request a hint from engine and display the result message."""
        if self.engine.solved:
            return
        msg = self.engine.get_hint()
        self.hint_lbl.config(text=msg)
        self._refresh_hud()
        self.controller.audio.play_click()

    def _toggle_reveal(self):
        """
        Toggle Reveal Mode.
        When entering reveal mode:
          - Query engine for full internal state.
          - Display state in a formatted panel.
          - Disable switch interaction (checked in _on_switch_click).
        When leaving reveal mode:
          - Hide reveal panel, show switch panel.
        """
        self._revealed = not self._revealed

        if self._revealed:
            info  = self.engine.get_reveal_info()
            lines = ["── CURRENT HIDDEN STATES ──\n"]
            for item in info:
                sym = "🟢" if item["current"] == "ON" else "🔴"
                lines.append(
                    f"  Switch {item['switch']:>2d}:  "
                    f"{sym} {item['current']:<3s}   "
                    f"(target: {item['target']})")
            lines.append("\n── Press RESUME to continue ──")
            self.reveal_lbl.config(text="\n".join(lines))
            self.switch_frame.pack_forget()
            self.reveal_frame.pack(expand=True, fill="both", padx=20)
        else:
            self.reveal_frame.pack_forget()
            self.switch_frame.pack(expand=True)

    # ------------------------------------------------------------------
    # Victory sequence
    # ------------------------------------------------------------------

    def _on_victory(self):
        """
        Triggered when the engine detects state == target.
          1. Play win sound.
          2. Animate bulb ON with pulsing glow.
          3. Show victory panel with final stats.
          4. Persist score to leaderboard CSV.
        """
        self.controller.audio.play_win()
        self._draw_bulb(on=True)
        self.lbl_bulb_status.config(text="● ON", fg=C_GOLD)
        self._pulse_bulb(12)

        self.switch_frame.pack_forget()
        self.reveal_frame.pack_forget()
        self.victory_detail.config(
            text=(f"Final Score: {self.engine.score}  |  "
                  f"Clicks: {self.engine.attempts}  |  "
                  f"Hints: {self.engine.hints_used}"))
        self.victory_frame.pack(expand=True)

        self.controller.leaderboard.save_entry(
            player     = self.player,
            difficulty = self.difficulty,
            score      = self.engine.score,
            attempts   = self.engine.attempts,
            hints      = self.engine.hints_used,
        )

    def _pulse_bulb(self, ticks: int):
        """
        Recursive pulse animation for the bulb after victory.
        Alternates on/off state every 200ms for *ticks* frames.
        """
        if ticks <= 0:
            self._draw_bulb(on=True)
            return
        self._draw_bulb(on=(ticks % 2 == 0))
        self.after(200, lambda: self._pulse_bulb(ticks - 1))

    def _restart(self):
        """Restart the current player/difficulty combination."""
        self.setup(self.player, self.difficulty)


# ===========================================================================
#  LEADERBOARD SCREEN
# ===========================================================================

class LeaderboardScreen(Screen):
    """
    Displays the top 10 all-time scores read from the CSV file.
    A tabular layout is rendered using tk.Label grids inside a Frame.
    """

    def __init__(self, master, controller):
        super().__init__(master, controller)
        self._build()

    def _build(self):
        bg = StarField(self)
        bg.place(x=0, y=0, relwidth=1, relheight=1)

        card = tk.Frame(self, bg=C_PANEL)
        card.place(relx=0.5, rely=0.5, anchor="center", width=680, height=520)

        tk.Label(card, text="🏆  LEADERBOARD",
                 bg=C_PANEL, fg=C_GOLD, font=FONT_TITLE).pack(pady=(24, 8))

        tk.Frame(card, bg=C_ACCENT, height=2).pack(fill="x", padx=40)

        # Table header row
        header = tk.Frame(card, bg=C_BTN)
        header.pack(fill="x", padx=20, pady=(12, 0))
        for col, w in [("Rank", 6), ("Name", 14), ("Diff", 8),
                       ("Score", 8), ("Clicks", 7), ("Hints", 6),
                       ("Date", 14)]:
            tk.Label(header, text=col, bg=C_BTN, fg=C_ACCENT2,
                     font=("Courier New", 10, "bold"),
                     width=w, anchor="w").pack(side="left", padx=4)

        # Scrollable rows container
        self.rows_frame = tk.Frame(card, bg=C_PANEL)
        self.rows_frame.pack(fill="both", expand=True, padx=20)

        RoundedButton(card, text="← BACK",
                      command=self.controller.show_menu,
                      bg=C_BTN, hover=C_BTN_HOVER,
                      fg=C_TEXT, width=160, height=38).pack(pady=16)

    def refresh(self):
        """Reload and redisplay scores whenever this screen becomes visible."""
        for w in self.rows_frame.winfo_children():
            w.destroy()

        rows = self.controller.leaderboard.load_top(10)
        if not rows:
            tk.Label(self.rows_frame,
                     text="No scores recorded yet. Play a game first!",
                     bg=C_PANEL, fg=C_SUBTEXT, font=FONT_BODY).pack(pady=20)
            return

        for rank, row in enumerate(rows, start=1):
            bg  = C_PANEL if rank % 2 == 0 else "#1a1a35"
            r   = tk.Frame(self.rows_frame, bg=bg)
            r.pack(fill="x", pady=1)
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")
            vals   = [medal,
                      str(row.get("player_name", "?"))[:13],
                      str(row.get("difficulty",  "?"))[:7],
                      str(row.get("score",       "?")),
                      str(row.get("attempts",    "?")),
                      str(row.get("hints",       "?")),
                      str(row.get("timestamp",   "?"))[:13]]
            widths = [6, 14, 8, 8, 7, 6, 14]
            for val, w in zip(vals, widths):
                tk.Label(r, text=val, bg=bg, fg=C_TEXT,
                         font=("Courier New", 10),
                         width=w, anchor="w").pack(side="left", padx=4)


# ===========================================================================
#  APPLICATION CONTROLLER  (top-level orchestrator)
# ===========================================================================

class App:
    """
    Central controller that owns:
      - The Tkinter root window.
      - Shared services: AudioManager, Leaderboard.
      - All Screen instances.
      - Navigation logic (show_menu, show_leaderboard, start_game).
    """

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("💡 Light Puzzle Challenge")
        self.root.geometry("820x640")
        self.root.resizable(False, False)
        self.root.configure(bg=C_BG)

        # Shared services
        self.audio       = AudioManager()
        self.leaderboard = Leaderboard()

        # Instantiate all screens (hidden by default)
        self.menu_screen = MenuScreen(self.root, self)
        self.game_screen = GameScreen(self.root, self)
        self.lb_screen   = LeaderboardScreen(self.root, self)

        # Show the main menu to begin
        self.show_menu()

        # Start background music (silently no-ops if file is missing)
        self.audio.play_music("bg.mp3")

    # ------------------------------------------------------------------
    def show_menu(self):
        """Navigate to the main menu screen."""
        self.game_screen.hide()
        self.lb_screen.hide()
        self.menu_screen.show()

    def show_leaderboard(self):
        """Navigate to the leaderboard screen (refreshes data)."""
        self.menu_screen.hide()
        self.game_screen.hide()
        self.lb_screen.refresh()
        self.lb_screen.show()

    def start_game(self, player: str, difficulty: str):
        """Navigate to the game screen and initialise a new puzzle."""
        self.menu_screen.hide()
        self.lb_screen.hide()
        self.game_screen.setup(player, difficulty)
        self.game_screen.show()

    # ------------------------------------------------------------------
    def run(self):
        """Enter the Tkinter main event loop."""
        self.root.mainloop()


# ===========================================================================
#  ENTRY POINT
# ===========================================================================

if __name__ == "__main__":
    app = App()
    app.run()