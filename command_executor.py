from dataclasses import dataclass
import platform
import shlex
import subprocess
import time
import getpass
from typing import List, Tuple, Optional
from rich.console import Console
from rich.prompt import Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn


@dataclass
class CommandResult:
    stdout: Optional[str] = ""
    stderr: Optional[str] = ""
    returncode: Optional[int] = 0

class CommandExecutor:
    def __init__(self, console: Console):
        self.sudo_password = None
        self.last_sudo_time = 0
        self.sudo_timeout = 300  # 5 minutes timeout for cached sudo password
        self.console = console

    def _check_dangerous_keywords(self, command: str) -> List[str]:
        """Check for potentially dangerous command keywords"""
        dangerous_keywords = [
            'rm -rf', 'mkfs', 'dd', ':(){', 'fork', '> /dev',
            '> /proc', '> /sys', 'chmod -R 777', 'chmod -R 000',
        ]
        found = []
        for keyword in dangerous_keywords:
            if keyword in command.lower():
                found.append(keyword)
        return found

    def _validate_command(self, command: str) -> Tuple[bool, str]:
        """Validate command for basic safety checks"""
        # Check for empty or whitespace-only commands
        if not command or command.isspace():
            return False, "Empty command"

        # Check for shell script execution attempts
        if command.startswith("./"):
            return False, "Direct script execution not allowed"

        # Check for pipe to shell
        if " | sh" in command or " | bash" in command:
            return False, "Pipe to shell not allowed"

        # Basic path traversal check
        if "../" in command or "..\"" in command:
            return False, "Path traversal not allowed"

        return True, ""

    def _get_sudo_password(self) -> str:
        """Get sudo password with caching"""
        current_time = time.time()

        # Return cached password if still valid
        if self.sudo_password and (current_time - self.last_sudo_time) < self.sudo_timeout:
            return self.sudo_password

        # Get new password
        self.console.print("\n🔐 [yellow]Please enter sudo password:[/yellow]")
        password = getpass.getpass("")
        self.sudo_password = password
        self.last_sudo_time = current_time
        return password

    def _run_with_sudo(self, command: str) -> subprocess.CompletedProcess:
        """Execute command with sudo"""
        password = self._get_sudo_password()

        if command.startswith("sudo "):
            # Remove 'sudo' from the command to avoid double sudo
            command = command[5:].lstrip()

        # Prepare sudo command
        sudo_command = f"sudo -S {command}"

        # Run command with sudo
        process = subprocess.Popen(
            sudo_command,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Send password to stdin
        stdout, stderr = process.communicate(input=password + '\n')

        if process.returncode != 0:
            if "incorrect password" in stderr.lower():
                self.sudo_password = None  # Clear cached password
                self.console.print("[red]❌ Incorrect sudo password[/red]")
            raise subprocess.CalledProcessError(process.returncode, sudo_command)

        return subprocess.CompletedProcess(sudo_command, process.returncode, stdout, stderr)

    def execute_command(self, command: str, sudo_required: bool = False, is_dangerous: bool = False) -> Tuple[bool, subprocess.CompletedProcess]:
        """
        Execute a shell command with proper safety checks
        Returns True if execution was successful, False otherwise
        """
        try:
            # Validate command
            is_valid, error_msg = self._validate_command(command)
            if not is_valid:
                self.console.print(f"[red]❌ Invalid command: {error_msg}[/red]")
                return (False, None)

            # Check for dangerous operations
            dangerous_ops = self._check_dangerous_keywords(command)
            if dangerous_ops and not is_dangerous:
                self.console.print("[red]❌ Potentially dangerous operation detected:[/red]")
                for op in dangerous_ops:
                    self.console.print(f"[red]  • {op}[/red]")
                if not Confirm.ask("[red]⚠️ Are you absolutely sure you want to proceed?[/red]"):
                    return (False, None)

            if sudo_required:
                self._get_sudo_password()  # Prompt password before spinner

            # Execute command with progress spinner
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(description="🚀 Executing command...", total=None)

                try:

                    if sudo_required:
                        result = self._run_with_sudo(command)
                    else:
                      if platform.system().lower() == "windows":
                        # Windows specific command execution
                        if sudo_required:
                          # Use 'runas' for Windows instead of sudo
                          self.console.print("[yellow]Please note that you may be prompted by Windows UAC to enter the Administrator password.[/yellow]")
                          command = f'runas /user:Administrator "{command}"'
                        result = subprocess.run(
                            command,
                            shell=True,  # Enable shell mode for Windows
                            capture_output=True,
                            text=True,
                            check=True
                        )
                      else:
                        # Linux specific command execution
                        if '|' in command:
                            result = subprocess.run(
                                command,
                                shell=True,  # Enable shell mode for commands with pipes
                                capture_output=True,
                                text=True,
                                check=True
                            )
                        else:
                            result = subprocess.run(
                                shlex.split(command),
                                capture_output=True,
                                text=True,
                                check=True
                            )

                    # Display command output
                    if result.stdout or result.stderr:
                        self.console.print("\n[green]═══════════ Command Output ═══════════[/green]")

                        if result.stdout:
                            self.console.print("[green]📝 Output:[/green]")
                            self.console.print(result.stdout.rstrip())

                        if result.stderr:
                            self.console.print("\n[yellow]⚠️ Warnings/Errors:[/yellow]")
                            self.console.print(result.stderr.rstrip())

                        self.console.print("[green]══════════════════════════════════════[/green]")

                    # self.console.print("[green]✅ Command executed successfully![/green]")
                    return (True, result)

                except subprocess.CalledProcessError as e:
                    self.console.print("\n[red]═══════════ Command Failed ═══════════[/red]")
                    self.console.print(f"[red]❌ Exit code: {e.returncode}[/red]")

                    if e.stdout:
                        self.console.print("\n[yellow]📝 Output before failure:[/yellow]")
                        self.console.print(e.stdout.rstrip())
                    if e.stderr:
                        self.console.print("\n[red]❌ Error message:[/red]")
                        self.console.print(e.stderr.rstrip())

                    self.console.print("[red]══════════════════════════════════════[/red]")
                    result = CommandResult(stdout=e.stdout, stderr=e.stderr, returncode=e.returncode)
                    return (False, result)

        except Exception as e:
            self.console.print(f"[red]❌ Error executing command: {str(e)}[/red]")
            result = CommandResult(stdout="", stderr=str(e))
            return (False, result)
