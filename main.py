import sys
import platform
import shlex
import json
import time
import requests
import subprocess
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from ai_command_line import AICommandLine


if __name__ == "__main__":
    console = Console()
    console.print(Panel.fit(
        "✨ [bold green]AI Command Assistant[/bold green] ✨\n" +
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n" +
        "🤖 Ask commands in natural language\n" +
        "💡 Use 'ask <question>' format\n" +
        "🚪 Type 'exit', 'quit', or 'q' to close\n\n" +
        "📍 Command Indicators:\n" +
        "   🟢 [green](>)[/green] Normal Command\n" +
        "   🔒 [yellow]($)[/yellow] Requires Sudo\n" +
        "   🚨 [red](!)[/red] High Risk Command",
        title="✨ Welcome! ✨",
        width=60,
        border_style="green"
    ))

    cli = AICommandLine(console)
    cli.run()