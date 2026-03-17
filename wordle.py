# wordle_ui.py
# Python 3.x - Tkinter UI Wordle (5 harf, 6 deneme)
# UI klavye ile input; grid + klavye Wordle renkleri.
# Yeni Oyun butonu + messagebox yerine status bar

import random
import tkinter as tk

# -----------------------------
# Ayarlar
# -----------------------------
WORD_LENGTH = 5
MAX_GUESSES = 6

COL_BG = "#121213"
COL_TEXT = "#FFFFFF"
COL_TILE_BORDER = "#3A3A3C"
COL_EMPTY_TILE = "#121213"

COL_GREEN = "#538D4E"
COL_YELLOW = "#B59F3B"
COL_GRAY = "#3A3A3C"

COL_KEY_DEFAULT = "#818384"
COL_KEY_TEXT = "#FFFFFF"
COL_KEY_SPECIAL = "#565758"

WORDS = [
    "APPLE", "TRAIN", "PLANT", "BRICK", "CLOUD", "SHEEP", "STONE", "GRAPE",
    "LIGHT", "MOUSE", "SOUND", "WATER", "EARTH", "RIVER", "HOUSE", "BREAD",
    "SMILE", "HEART", "NURSE", "SMART", "CHAIR", "SUGAR", "BLADE", "FROST",
    "SHARK", "THING", "BRAVE", "CROWN", "SPICE", "SWEET", "TRACK", "SCOPE",
]
WORDS = [w for w in WORDS if len(w) == WORD_LENGTH and w.isalpha()]

KB_ROWS = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]


def evaluate_guess(guess: str, answer: str):
    guess = guess.upper()
    answer = answer.upper()

    result = ["gray"] * WORD_LENGTH
    remaining = {}

    # Yeşiller
    for i in range(WORD_LENGTH):
        if guess[i] == answer[i]:
            result[i] = "green"
        else:
            remaining[answer[i]] = remaining.get(answer[i], 0) + 1

    # Sarılar
    for i in range(WORD_LENGTH):
        if result[i] == "green":
            continue
        ch = guess[i]
        if remaining.get(ch, 0) > 0:
            result[i] = "yellow"
            remaining[ch] -= 1

    return result


def severity(state: str) -> int:
    order = {"default": 0, "gray": 1, "yellow": 2, "green": 3}
    return order.get(state, 0)


def key_color(state: str) -> str:
    if state == "green":
        return COL_GREEN
    if state == "yellow":
        return COL_YELLOW
    if state == "gray":
        return COL_GRAY
    return COL_KEY_DEFAULT


class WordleUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Wordle (UI)")
        self.root.configure(bg=COL_BG)
        self.root.resizable(False, False)

        if not WORDS:
            raise ValueError("WORDS listesi boş. 5 harfli kelimeler ekleyin.")

        # Status bar timer
        self._status_after_id = None

        self._build_topbar()
        self._build_grid()
        self._build_keyboard()
        self._build_statusbar()

        self.root.bind("<Key>", self._on_physical_key)

        self.new_game()

    # -----------------------------
    # UI Build
    # -----------------------------
    def _build_topbar(self):
        top = tk.Frame(self.root, bg=COL_BG)
        top.pack(fill="x", padx=14, pady=(12, 6))

        title = tk.Label(
            top, text="WORDLE",
            bg=COL_BG, fg=COL_TEXT,
            font=("Helvetica", 16, "bold")
        )
        title.pack(side="left")

        self.btn_new = tk.Button(
            top, text="Yeni Oyun",
            command=self.new_game,
            bg=COL_KEY_SPECIAL, fg=COL_KEY_TEXT,
            activebackground=COL_KEY_SPECIAL, activeforeground=COL_KEY_TEXT,
            bd=0, relief="flat",
            font=("Helvetica", 10, "bold"),
            cursor="hand2",
            padx=12, pady=6
        )
        self.btn_new.pack(side="right")

    def _build_grid(self):
        frame = tk.Frame(self.root, bg=COL_BG)
        frame.pack(padx=14, pady=(6, 10))

        self.tiles = [[None for _ in range(WORD_LENGTH)] for _ in range(MAX_GUESSES)]

        font = ("Helvetica", 20, "bold")
        for r in range(MAX_GUESSES):
            for c in range(WORD_LENGTH):
                lbl = tk.Label(
                    frame,
                    text="",
                    width=2,
                    height=1,
                    font=font,
                    bg=COL_EMPTY_TILE,
                    fg=COL_TEXT,
                    bd=2,
                    relief="solid",
                    highlightthickness=0
                )
                lbl.grid(row=r, column=c, padx=6, pady=6, ipadx=8, ipady=10)
                lbl.configure(highlightbackground=COL_TILE_BORDER)
                self.tiles[r][c] = lbl

    def _build_keyboard(self):
        kb_frame = tk.Frame(self.root, bg=COL_BG)
        kb_frame.pack(padx=14, pady=(0, 8))
        self.key_buttons = {}

        self._make_kb_row(kb_frame, KB_ROWS[0], row=0, left_pad=0)
        self._make_kb_row(kb_frame, KB_ROWS[1], row=1, left_pad=20)

        row3 = tk.Frame(kb_frame, bg=COL_BG)
        row3.grid(row=2, column=0, pady=6)

        self.btn_enter = tk.Button(
            row3, text="ENTER",
            command=self.on_enter,
            bg=COL_KEY_SPECIAL, fg=COL_KEY_TEXT,
            activebackground=COL_KEY_SPECIAL, activeforeground=COL_KEY_TEXT,
            width=7, height=2, bd=0, relief="flat",
            font=("Helvetica", 10, "bold"),
            cursor="hand2"
        )
        self.btn_enter.pack(side="left", padx=4)

        for ch in KB_ROWS[2]:
            b = tk.Button(
                row3, text=ch,
                command=lambda x=ch: self.on_letter(x),
                bg=COL_KEY_DEFAULT, fg=COL_KEY_TEXT,
                activebackground=COL_KEY_DEFAULT, activeforeground=COL_KEY_TEXT,
                width=4, height=2, bd=0, relief="flat",
                font=("Helvetica", 11, "bold"),
                cursor="hand2"
            )
            b.pack(side="left", padx=4)
            self.key_buttons[ch] = b

        self.btn_bk = tk.Button(
            row3, text="⌫",
            command=self.on_backspace,
            bg=COL_KEY_SPECIAL, fg=COL_KEY_TEXT,
            activebackground=COL_KEY_SPECIAL, activeforeground=COL_KEY_TEXT,
            width=5, height=2, bd=0, relief="flat",
            font=("Helvetica", 12, "bold"),
            cursor="hand2"
        )
        self.btn_bk.pack(side="left", padx=4)

    def _make_kb_row(self, parent, letters: str, row: int, left_pad: int):
        rowf = tk.Frame(parent, bg=COL_BG)
        rowf.grid(row=row, column=0, pady=6, padx=(left_pad, 0))

        for ch in letters:
            b = tk.Button(
                rowf, text=ch,
                command=lambda x=ch: self.on_letter(x),
                bg=COL_KEY_DEFAULT, fg=COL_KEY_TEXT,
                activebackground=COL_KEY_DEFAULT, activeforeground=COL_KEY_TEXT,
                width=4, height=2, bd=0, relief="flat",
                font=("Helvetica", 11, "bold"),
                cursor="hand2"
            )
            b.pack(side="left", padx=4)
            self.key_buttons[ch] = b

    def _build_statusbar(self):
        bar = tk.Frame(self.root, bg=COL_BG)
        bar.pack(fill="x", padx=14, pady=(0, 12))

        self.status_label = tk.Label(
            bar,
            text="",
            bg=COL_BG,
            fg=COL_TEXT,
            font=("Helvetica", 11),
            anchor="w"
        )
        self.status_label.pack(fill="x")

    # -----------------------------
    # Game Loop
    # -----------------------------
    def new_game(self):
        self.answer = random.choice(WORDS).upper()

        self.current_row = 0
        self.current_col = 0
        self.game_over = False

        self.grid_letters = [["" for _ in range(WORD_LENGTH)] for _ in range(MAX_GUESSES)]
        self.key_state = {ch: "default" for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"}

        # Grid temizle
        for r in range(MAX_GUESSES):
            for c in range(WORD_LENGTH):
                lbl = self.tiles[r][c]
                lbl.config(text="", bg=COL_EMPTY_TILE, fg=COL_TEXT, highlightbackground=COL_TILE_BORDER)

        # Klavye temizle
        for ch, btn in self.key_buttons.items():
            btn.config(bg=COL_KEY_DEFAULT, activebackground=COL_KEY_DEFAULT)

        self.set_status("Yeni oyun başladı!", timeout_ms=1500)

    # -----------------------------
    # Status bar
    # -----------------------------
    def set_status(self, msg: str, timeout_ms: int = 0):
        # Eski timer varsa iptal et
        if self._status_after_id is not None:
            try:
                self.root.after_cancel(self._status_after_id)
            except Exception:
                pass
            self._status_after_id = None

        self.status_label.config(text=msg)

        if timeout_ms and timeout_ms > 0:
            self._status_after_id = self.root.after(timeout_ms, self.clear_status)

    def clear_status(self):
        self.status_label.config(text="")
        self._status_after_id = None

    # -----------------------------
    # Input handlers
    # -----------------------------
    def _on_physical_key(self, event):
        if self.game_over:
            return

        key = event.keysym.upper()
        if key == "RETURN":
            self.on_enter()
            return
        if key in ("BACKSPACE", "DELETE"):
            self.on_backspace()
            return

        if len(event.char) == 1 and event.char.isalpha():
            self.on_letter(event.char.upper())

    def on_letter(self, ch: str):
        if self.game_over:
            return
        if self.current_row >= MAX_GUESSES or self.current_col >= WORD_LENGTH:
            return

        ch = ch.upper()
        self.grid_letters[self.current_row][self.current_col] = ch
        self._update_tile(self.current_row, self.current_col, ch)
        self.current_col += 1
        self.clear_status()

    def on_backspace(self):
        if self.game_over:
            return
        if self.current_col <= 0:
            return
        self.current_col -= 1
        self.grid_letters[self.current_row][self.current_col] = ""
        self._update_tile(self.current_row, self.current_col, "")
        self.clear_status()

    def on_enter(self):
        if self.game_over:
            return

        if self.current_col < WORD_LENGTH:
            self.set_status("5 harf tamamla.", timeout_ms=2000)
            return

        guess = "".join(self.grid_letters[self.current_row]).upper()
        if guess not in WORDS:
            self.set_status("Sözlükte yok.", timeout_ms=2000)
            return

        states = evaluate_guess(guess, self.answer)
        self._apply_row_colors(self.current_row, states)
        self._apply_keyboard_colors(guess, states)

        if guess == self.answer:
            self.game_over = True
            self.set_status(f"Kazandın! Cevap: {self.answer}")
            return

        self.current_row += 1
        self.current_col = 0

        if self.current_row >= MAX_GUESSES:
            self.game_over = True
            self.set_status(f"Bitti! Cevap: {self.answer}")
        else:
            self.clear_status()

    # -----------------------------
    # UI updates
    # -----------------------------
    def _update_tile(self, r: int, c: int, ch: str):
        lbl = self.tiles[r][c]
        lbl.config(text=ch, bg=COL_EMPTY_TILE, fg=COL_TEXT, highlightbackground=COL_TILE_BORDER)

    def _apply_row_colors(self, r: int, states):
        for c in range(WORD_LENGTH):
            st = states[c]
            if st == "green":
                bg = COL_GREEN
            elif st == "yellow":
                bg = COL_YELLOW
            else:
                bg = COL_GRAY
            lbl = self.tiles[r][c]
            lbl.config(bg=bg, fg=COL_TEXT, highlightbackground=bg)

    def _apply_keyboard_colors(self, guess: str, states):
        for ch, st in zip(guess, states):
            prev = self.key_state.get(ch, "default")
            if severity(st) > severity(prev):
                self.key_state[ch] = st
                btn = self.key_buttons.get(ch)
                if btn:
                    col = key_color(st)
                    btn.config(bg=col, activebackground=col)


def main():
    root = tk.Tk()
    WordleUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()