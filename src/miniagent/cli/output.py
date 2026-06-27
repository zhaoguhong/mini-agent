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
        """Print text using Rich when it is installed."""

        if self._rich:
            self._rich.print(*args, **kwargs)
        else:
            print(*args)

    def write(self, text: str) -> None:
        """Write streaming text without adding a newline."""

        if self._rich:
            self._rich.print(text, end="")
        else:
            print(text, end="", flush=True)

    def input(self, prompt: str = "You") -> str:
        """Read one user input line with a styled prompt when Rich is available."""

        if self._rich:
            from rich.prompt import Prompt

            return Prompt.ask(f"[bold green]{prompt}[/]")
        return input(f"{prompt} > ")

    def intro(self) -> None:
        """Render the REPL welcome message."""

        if self._rich:
            from rich.panel import Panel

            self._rich.print(
                Panel.fit(
                    "[bold cyan]miniagent[/]\n[dim]Type /help for commands. Ctrl+C or /exit to quit.[/]",
                    border_style="cyan",
                )
            )
            return
        self.print("miniagent interactive session. Type /help for commands.")

    def render_assistant(self, text: str, render_markdown: bool = True) -> None:
        """Render a complete assistant message."""

        if not render_markdown or not self._rich:
            self.print(text)
            return
        from rich.markdown import Markdown
        from rich.panel import Panel

        self._rich.print(Panel(Markdown(text), title="miniagent", border_style="cyan", padding=(1, 2)))

    def markdown_stream(self, render_markdown: bool = True):
        """Create a streaming renderer for assistant Markdown."""

        if not render_markdown or not self._rich:
            return PlainTextStream(self)
        return RichMarkdownStream(self._rich)

    def confirm(self, prompt: str) -> bool:
        """Ask the user to confirm a potentially unsafe action."""

        if self._rich:
            from rich.prompt import Confirm

            return Confirm.ask(prompt, default=False)
        answer = input(f"{prompt} [y/N] ")
        return answer.strip().lower() in {"y", "yes"}

    def table(self, title: str, columns: Iterable[str], rows: Iterable[Iterable[str]]) -> None:
        """Render a small table with a plain-text fallback."""

        if self._rich:
            from rich.table import Table

            table = Table(title=title, border_style="cyan", header_style="bold cyan")
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


class PlainTextStream:
    """Fallback stream that writes raw text chunks."""

    def __init__(self, console: Console) -> None:
        self.console = console

    def __enter__(self) -> "PlainTextStream":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.console.print("")

    def write(self, text: str) -> None:
        self.console.write(text)


class RichMarkdownStream:
    """Render streaming Markdown by refreshing one Rich panel."""

    def __init__(self, rich_console) -> None:
        self._rich = rich_console
        self._buffer = ""
        self._live = None

    def __enter__(self) -> "RichMarkdownStream":
        from rich.live import Live

        self._live = Live(self._render(), console=self._rich, refresh_per_second=8)
        self._live.__enter__()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self._live:
            self._live.update(self._render())
            self._live.__exit__(exc_type, exc, traceback)

    def write(self, text: str) -> None:
        self._buffer += text
        if self._live:
            self._live.update(self._render())

    def _render(self):
        from rich.markdown import Markdown
        from rich.panel import Panel

        body = self._buffer or "*Thinking...*"
        return Panel(Markdown(body), title="miniagent", border_style="cyan", padding=(1, 2))
