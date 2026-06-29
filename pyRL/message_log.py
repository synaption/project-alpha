from __future__ import annotations
import textwrap
import color


class Message:
    def __init__(self, text: str, fg: tuple[int, int, int]) -> None:
        self.plain_text = text
        self.fg = fg
        self.count = 1

    @property
    def full_text(self) -> str:
        return f"{self.plain_text} (x{self.count})" if self.count > 1 else self.plain_text


class MessageLog:
    def __init__(self) -> None:
        self.messages: list[Message] = []

    def add(self, text: str, fg: tuple[int, int, int] = color.WHITE, *, stack: bool = True) -> None:
        if stack and self.messages and text == self.messages[-1].plain_text:
            self.messages[-1].count += 1
        else:
            self.messages.append(Message(text, fg))

    def render(self, console, x: int, y: int, width: int, height: int) -> None:
        y_offset = height - 1
        for msg in reversed(self.messages):
            lines = textwrap.wrap(msg.full_text, width) or [msg.full_text[:width]]
            for line in reversed(lines):
                if y_offset < 0:
                    return
                console.print(x=x, y=y + y_offset, string=line, fg=msg.fg)
                y_offset -= 1
