"""Windows mouse and keyboard control through pyautogui."""

from typing import Any


class MouseController:
    def __init__(
        self,
        sensitivity: float = 1.5,
        scroll_speed: float = 3.0,
        gui: Any = None,
        clipboard: Any = None,
    ) -> None:
        if gui is None:
            try:
                import pyautogui as gui
            except ImportError as exc:
                raise RuntimeError(
                    "pyautogui is required. Install dependencies with "
                    "'pip install -r requirements.txt'."
                ) from exc
        if clipboard is None:
            try:
                import pyperclip as clipboard
            except ImportError as exc:
                raise RuntimeError(
                    "pyperclip is required. Install dependencies with "
                    "'pip install -r requirements.txt'."
                ) from exc

        self._gui = gui
        self._clipboard = clipboard
        self.sensitivity = sensitivity
        self.scroll_speed = scroll_speed
        self._gui.FAILSAFE = False
        self._gui.PAUSE = 0.0
        self._scroll_remainder = 0.0

    def move(self, dx: float, dy: float) -> None:
        self._gui.moveRel(dx * self.sensitivity, dy * self.sensitivity)

    def left_click(self) -> None:
        self._gui.click()

    def right_click(self) -> None:
        self._gui.rightClick()

    def scroll(self, dy: float) -> None:
        self._scroll_remainder += dy * self.scroll_speed
        amount = int(self._scroll_remainder)
        if amount != 0:
            self._gui.scroll(amount)
            self._scroll_remainder -= amount

    def type_text(self, text: str) -> None:
        if not text:
            return
        self._clipboard.copy(text)
        self._gui.hotkey("ctrl", "v")
