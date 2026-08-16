"""Modern, professional terminal UI components and progress formatting."""

import os
import sys
from typing import Optional, List, Dict, Any, Callable

# Ensure UTF-8 output encoding for modern Unicode block characters on Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.progress import (
        Progress,
        SpinnerColumn,
        BarColumn,
        TextColumn,
        TaskProgressColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
    )
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class TerminalUI:
    """Manages modern CLI rendering, banners, progress bars, and completion summaries."""

    def __init__(self, quiet: bool = False):
        self.quiet = quiet
        if RICH_AVAILABLE:
            self.console = Console(force_terminal=True)
        else:
            self.console = None

    def print_banner(self, version: str = "1.0.0") -> None:
        """Displays a modern CLI banner."""
        if self.quiet:
            return
        if not RICH_AVAILABLE or self.console is None:
            print(f"=== NOTEBOOKLM WATERMARK REMOVER v{version} ===")
            return

        header = Text()
        header.append("✦ ", style="bold cyan")
        header.append("NOTEBOOKLM WATERMARK REMOVER", style="bold white")
        header.append(f"  v{version}\n", style="dim cyan")
        header.append("Fast, pure-CLI document & presentation watermark cleaner", style="dim white")

        banner = Panel(
            header,
            box=box.ROUNDED,
            border_style="cyan",
            padding=(0, 2),
        )
        self.console.print(banner)

    def print_file_info(
        self,
        input_path: str,
        output_path: str,
        format_name: str,
        use_patch_heal: bool = True
    ) -> None:
        """Prints a structured metadata table for the task."""
        if self.quiet:
            return
        if not RICH_AVAILABLE or self.console is None:
            print(f"Input:  {input_path}")
            print(f"Output: {output_path}")
            return

        table = Table(box=box.SIMPLE_HEAD, show_header=False, padding=(0, 1), expand=False)
        table.add_column("Key", style="dim cyan", no_wrap=True)
        table.add_column("Value", style="bold white")

        table.add_row("Input File", os.path.abspath(input_path))
        table.add_row("Format", format_name)
        table.add_row("Output Destination", os.path.abspath(output_path))
        table.add_row("Strategy", "Texture Donor Patch Healing" if use_patch_heal else "Telea Inpainting")

        panel = Panel(
            table,
            title="[bold cyan]Task Information[/bold cyan]",
            title_align="left",
            box=box.ROUNDED,
            border_style="dim cyan",
            padding=(0, 1),
        )
        self.console.print(panel)

    def create_progress(self, description: str = "Processing", unit: str = "items") -> Any:
        """Creates and returns a modern styled Rich progress bar or fallback."""
        if self.quiet or not RICH_AVAILABLE or self.console is None:
            return None

        return Progress(
            SpinnerColumn(spinner_name="dots", style="cyan"),
            TextColumn(f"[bold cyan]{description}[/bold cyan]"),
            BarColumn(
                bar_width=28,
                style="dim cyan",
                complete_style="cyan",
                finished_style="bold green",
            ),
            TaskProgressColumn(),
            TextColumn(f"• [bold white]{{task.completed}}/{{task.total}}[/bold white] {unit}"),
            TextColumn("• [dim]patched:[/dim] [bold green]{task.fields[patched]}[/bold green]"),
            TimeElapsedColumn(),
            console=self.console,
            transient=False,
        )

    def print_completion(
        self,
        output_path: str,
        patched_count: int,
        total_count: int,
        elapsed_seconds: float,
        unit: str = "items"
    ) -> None:
        """Prints a clean summary card upon completion."""
        if self.quiet:
            return
        if not RICH_AVAILABLE or self.console is None:
            print(f"Done: {output_path} ({patched_count}/{total_count} {unit} patched in {elapsed_seconds:.2f}s)")
            return

        file_size_str = ""
        if os.path.exists(output_path):
            size_kb = os.path.getsize(output_path) / 1024
            if size_kb > 1024:
                file_size_str = f" ({size_kb / 1024:.2f} MB)"
            else:
                file_size_str = f" ({size_kb:.1f} KB)"

        summary = Text()
        summary.append("  [OK] Status:          ", style="bold green")
        summary.append("Completed Successfully\n", style="bold white")

        summary.append("  [OK] Output Saved:    ", style="bold green")
        summary.append(f"{os.path.basename(output_path)}{file_size_str}\n", style="cyan")

        summary.append("  [OK] Cleaned Media:   ", style="bold green")
        summary.append(f"{patched_count} / {total_count} {unit} patched\n", style="bold white")

        summary.append("  [OK] Time Elapsed:    ", style="bold green")
        summary.append(f"{elapsed_seconds:.2f} seconds\n", style="dim white")

        panel = Panel(
            summary,
            title="[bold green] Processing Complete [/bold green]",
            title_align="left",
            box=box.ROUNDED,
            border_style="green",
            padding=(0, 1),
        )
        self.console.print(panel)

    def print_batch_summary(self, results: Dict[str, bool], elapsed_seconds: float) -> None:
        """Prints a clean summary table for batch processing."""
        if self.quiet:
            return
        if not RICH_AVAILABLE or self.console is None:
            success_count = sum(1 for v in results.values() if v)
            print(f"Batch complete: {success_count}/{len(results)} in {elapsed_seconds:.2f}s")
            return

        table = Table(box=box.ROUNDED, border_style="cyan", title="Batch Processing Results")
        table.add_column("File", style="bold white")
        table.add_column("Status", justify="center")

        for path, success in results.items():
            fname = os.path.basename(path)
            status_text = "[bold green]✔ Cleaned[/bold green]" if success else "[bold red]✘ Failed[/bold red]"
            table.add_row(fname, status_text)

        self.console.print(table)
        success_count = sum(1 for v in results.values() if v)
        self.console.print(
            f"\n[bold green]✔ Batch Complete:[/bold green] [bold white]{success_count}/{len(results)}[/bold white] files successfully processed in [dim]{elapsed_seconds:.2f}s[/dim]\n"
        )

    def print_error(self, message: str) -> None:
        """Prints a formatted error message."""
        if not RICH_AVAILABLE or self.console is None:
            print(f"ERROR: {message}", file=sys.stderr)
            return

        panel = Panel(
            f"[bold red]✘ Error:[/bold red] [white]{message}[/white]",
            box=box.ROUNDED,
            border_style="red",
            padding=(0, 1),
        )
        self.console.print(panel)

    def print_warning(self, message: str) -> None:
        """Prints a formatted warning message."""
        if not RICH_AVAILABLE or self.console is None:
            print(f"WARNING: {message}")
            return

        self.console.print(f"[bold yellow]⚠ Warning:[/bold yellow] [white]{message}[/white]")
