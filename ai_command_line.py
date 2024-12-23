import platform
import json
import requests
import os
from dotenv import load_dotenv
from typing import List, Optional
from dataclasses import dataclass
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.text import Text
from command_executor import CommandExecutor

_MASTER_PROMPT = """운영체제에서 활용 가능한 명령줄 스크립트를 작성하는 것이 당신의 목표입니다.
- 사용자의 요구사항에 맞게 명령어를 생성하고 실행하는 것이 중요합니다.
- 사용자가 기존의 명령어를 수정하거나 다시 작성하도록 요청할 수 있습니다.
  - 제공된 명령어와 출력을 보고 인과관계를 생각해서 수정사항을 확인하세요.
  - 오류를 수정해야하는 경우 여러가지 원인을 생각해보고, 새로운 방법을 시도하세요.

[출력 형식 규칙]
1. JSON 객체만을 출력하시오. (추가적인 설명, 문장, 부가 텍스트를 일절 넣지 마시오.)
2. 최상위 필드는 commands, options, 그리고 필요한 경우 다른 확장 필드를 포함할 수 있습니다.
  - 예: { "commands": ["...", "..."], "options": [...], "dangerous": false, "sudo_required": false, ... }
3. commands 필드에 실제 실행해야 할 명령어(들)를 작성하세요.
  - 파이프(|)나 리다이렉션(>, >>)도 모두 포함하여 정확히 한 줄에 작성합니다.
4. options 필드는 선택적으로 아래와 같은 형식을 따릅니다:
   "options": [ { "option_name": "...", "option_type": "...", "replacer": "...", "description": "..." // 필요한 경우 "dangerous": true, "sudo_required": true 등 추가 키를 둘 수 있음 }, ... ]
"""

@dataclass
class CommandOption:
    option_name: str
    option_type: Optional[str] = None
    sudo_required: Optional[bool] = False
    replacer: Optional[str] = None
    description: str = ""

@dataclass
class CommandResponse:
    commands: List[str]
    options: Optional[List[CommandOption]] = None
    dangerous: bool = False
    sudo_required: Optional[bool] = False
    description: Optional[str] = None

class AICommandLine:
    def __init__(self, console: Console):
        self.console = console
        load_dotenv()
        self.api_url = os.getenv('API_URL', 'https://xyevph4z54ojekrgfjnekkuxta0ddbkl.lambda-url.eu-central-1.on.aws/generate')
        self.headers = {
            "Content-Type": "application/json",
        }
        self.command_executor = CommandExecutor(self.console)

    def _detect_system_info(self):
        """Detect and store system information"""
        self.os_system = platform.system().lower()
        self.os_release = platform.release()
        self.os_version = platform.version()
        self.machine = platform.machine()
        self.processor = platform.processor()

        # Get more detailed OS information
        if self.os_system == "linux":
            try:
                with open("/etc/os-release") as f:
                    os_info = dict(line.strip().split('=', 1) for line in f if '=' in line)
                    self.os_name = os_info.get('PRETTY_NAME', '').strip('"')
            except:
                self.os_name = f"Linux {self.os_release}"
        elif self.os_system == "darwin":
            self.os_name = f"macOS {platform.mac_ver()[0]}"
        elif self.os_system == "windows":
            self.os_name = f"Windows {platform.win32_ver()[0]}"
        else:
            self.os_name = f"{self.os_system} {self.os_release}"

        return f"{self.os_name} ({self.machine})"

    def ask_ai(self, query: str) -> CommandResponse:
        sys_info = self._detect_system_info()
        prompt_system = sys_info + _MASTER_PROMPT
        payload = {
            "temperature": 0.2,
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": -1,
            "prompt_system": prompt_system,
            "inputs": [{"role": "user", "content": query}]
        }

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="✧･ﾟ: *✧･ﾟ:* AI is thinking... *:･ﾟ✧*:･ﾟ✧", total=None)
            response = requests.post(self.api_url, json=payload, headers=self.headers)

        if response.status_code != 200:
            raise Exception(f"API 호출 실패: {response.status_code}")

        json_response = response.json()
        data = json.loads(json_response["data"])
        return CommandResponse(
            commands=data["commands"],
            options=([CommandOption(**opt) for opt in data["options"]] if "options" in data else []),
            dangerous=data.get("dangerous", False),
            sudo_required=data.get("sudo_required", False),
            description=data.get("description")
        )

    def display_command(self, cmd_response: CommandResponse):
        # Create styled command text
        cmd_text = Text()

        for cmd in cmd_response.commands:
            # Add prefix based on command type
            if cmd_response.dangerous and cmd_response.sudo_required:
                prefix = "🚨🔒 "
            elif cmd_response.dangerous:
                prefix = "🚨 "
            elif cmd_response.sudo_required:
                prefix = "🔒 "
            else:
                prefix = "🟢 "

            cmd_text.append(prefix, style="bold")
            cmd_text.append(cmd, style="bold cyan")
            if cmd != cmd_response.commands[-1]:
              cmd_text.append("\n")

        # Add status indicators
        status = []
        if cmd_response.dangerous:
            status.append("🚨 [red]High Risk Command![/red]")
        if cmd_response.sudo_required:
            status.append("🔒 [yellow]Requires Sudo[/yellow]")
        if not (cmd_response.dangerous or cmd_response.sudo_required):
            status.append("✨ [green]Safe to Execute[/green]")

        # Create command panel
        panel = Panel(
            cmd_text,
            title="🤖 Command to Execute",
            subtitle=" ".join(status) if status else None,
            style="bold green" if not cmd_response.dangerous else "bold red"
        )
        self.console.print(panel)

    def display_help(self, cmd_response: CommandResponse):
        if cmd_response.description:
            self.console.print(f"\n[yellow]📝 Command Description:[/yellow]")
            self.console.print(f"╰─➤ {cmd_response.description}\n")

        if cmd_response.options:
            self.console.print("[yellow]⚙️  Options:[/yellow]")
            for opt in cmd_response.options:
                self.console.print(f"╰─➤ {opt.option_name}: {opt.description}")

    def reask_ai_with_last_command(self, ask:str, command_stack: List[str], last_output: str, return_code: int = 0) -> CommandResponse:
        """Re-ask AI with the last command and output"""
        last_command = command_stack[-1]
        used_command = "\n".join(map(lambda s: f"`{s}`", command_stack))
        query = f"\n\n[Goal]\n{ask}\n\n[FIX or REVISE]\ncommand:\n`{last_command}`\n" \
              + f"ReturnCode: {return_code}\n다음 출력을 참고하시오:\n```{last_output}```\n\n" \
              + f"다음 커맨드는 이미 시도해 보았습니다.:\n{used_command}"
        return self.ask_ai(query)

    def run(self):
        command_stack = []
        last_command = ""
        last_output = ""
        return_code = 0
        while True:
            try:
                # Get user input
                user_input = self.console.input("\n[bold green]>> [/bold green]").strip()

                # Exit condition
                if user_input.lower() in ['exit', 'quit', 'q']:
                    command_stack = []
                    self.console.print("[yellow]프로그램을 종료합니다...[/yellow]")
                    break

                # Handle AI query
                query = user_input
                if not query:
                    self.console.print("[red]질문을 입력해주세요.[/red]")
                    continue

                try:
                    response = self.ask_ai(query)
                    self.display_command(response)

                    while True:
                        choice = Prompt.ask(
                            "실행하시겠습니까?",
                            choices=["y", "n", "?"],
                            default="n"
                        )

                        if choice == "?":
                            self.display_help(response)
                            continue
                        elif choice.lower() == "y":
                            self.console.print("[green]🚀 Starting command execution...[/green]")

                            # Execute each command with proper error handling
                            execution_success = True
                            for index, cmd in enumerate(response.commands, 1):
                                command_stack.append(cmd)
                                # Show current command
                                command_status = Text.from_markup(f"\n[cyan]⚡ Executing command ({index}/{len(response.commands)}):[/cyan] {cmd}")
                                self.console.print(command_status, end="", crop=False)

                                # Execute the command using CommandExecutor
                                try:
                                    success, result = self.command_executor.execute_command(
                                        cmd,
                                        sudo_required=response.sudo_required,
                                        is_dangerous=response.dangerous
                                    )

                                    last_command = cmd
                                    return_code = result.returncode
                                    if result:
                                        last_output = "STDOUT:\n" + (result.stdout or "") + "\nSTDERR:\n" + (result.stderr or "")

                                    else:
                                        execution_success = success
                                        choices = ["continue", "retry", "abort"]
                                        action = Prompt.ask(
                                            "[yellow]💫 Command failed. What would you like to do?[/yellow]",
                                            choices=choices,
                                            default="abort"
                                        )

                                        if action == "retry":
                                            # Re-ask AI with last command/output
                                            new_response = self.reask_ai_with_last_command(query, command_stack, last_output, return_code)
                                            self.display_command(new_response)
                                            continue
                                        elif action == "abort":
                                            command_stack = []
                                            self.console.print("[yellow]⚠️ Execution aborted by user[/yellow]")
                                            break
                                        # "continue" will move to next command

                                except KeyboardInterrupt:
                                    self.console.print("\n[yellow]⚠️ Command interrupted by user[/yellow]")
                                    if not Confirm.ask("[yellow]Continue with remaining commands?[/yellow]"):
                                        break
                                    continue

                            # After all commands
                            if execution_success:
                                choices = ["d", "r"]
                                action = Prompt.ask("[green]All commands completed. Next action?[/green] (d=done, r=retry)", choices=choices, default="d")
                                if action == "d":
                                    break
                                elif action == "r":
                                    response = self.reask_ai_with_last_command(query, command_stack, last_output, return_code)

                                    self.display_command(response)
                                    continue
                            else:
                                self.console.print("\n[yellow]⚠️ Some commands encountered issues.[/yellow]")
                            break
                        else:
                            self.console.print("[yellow]명령어 실행을 취소했습니다.[/yellow]")
                            break
                except Exception as e:
                    self.console.print(f"[red]Error occurred: {str(e)}[/red]")


            except KeyboardInterrupt:
                self.console.print("\n[yellow]Exiting program...[/yellow]")
                break

            except Exception as e:
                self.console.print(f"[red]Unexpected error occurred: {str(e)}[/red]")