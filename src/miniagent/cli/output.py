"""Terminal output helpers."""

from __future__ import annotations

from typing import Iterable


class Console:
    """A tiny wrapper that uses rich when available."""

    def __init__(self) -> None:
        try:
            from rich.console import Console as RichConsole
        except ModuleNotFoundError:
            self._rich = None
        else:
            self._rich = RichConsole()

    def print(self, *args, **kwargs) -> None:
        if self._rich:
            self._rich.print(*args, **kwargs)
        else:
            print(*args)

    def write(self, text: str) -> None:
        if self._rich:
            self._rich.print(text, end="")
        else:
            print(text, end="", flush=True)

    def confirm(self, prompt: str) -> bool:
        if self._rich:
            from rich.prompt import Confirm

            return Confirm.ask(prompt, default=False)
        answer = input(f"{prompt} [y/N] ")
        return answer.strip().lower() in {"y", "yes"}

    def table(self, title: str, columns: Iterable[str], rows: Iterable[Iterable[str]]) -> None:
        if self._rich:
            from rich.table import Table

            table = Table(title=title)
            for column in columns:
                table.add_column(column)
            for row in rows:
                table.add_row(*[str(item) for item in row])
            self._rich.print(table)
            return
        self.print(title)
        self.print(" | ".join(columns))
        for row in rows:
            self.print(" | ".join(str(item) for item in row))

