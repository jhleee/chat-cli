# chat-cli
LLM을 이용한 chat cli 입니다.

## 사용 예시

```sh
chat-cli:~/chat-cli$ python3 main.py
╭──────────── ✨ Welcome! ✨ ─────────────╮
│ ✨ AI Command Assistant ✨              │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━         │
│ 🤖 Ask commands in natural language     │
│ 💡 Use 'ask <question>' format          │
│ 🚪 Type 'exit', 'quit', or 'q' to close │
│                                         │
│ 📍 Command Indicators:                  │
│    🟢 (>) Normal Command                │
│    🔒 ($) Requires Sudo                 │
│    🚨 (!) High Risk Command             │
╰─────────────────────────────────────────╯

>> Print out the process ID and name of the process using port 5678, numbered.
╭────────────────────────────────────── 🤖 Command to Execute ──────────────────────────────────────╮
│ 🟢 netstat -tulpn 2>/dev/null | grep ':5678' | awk '{print NR ". PID: " $7 " - Process: " $7}' |  │
│ sed 's/\/.*$//'                                                                                   │
╰─────────────────────────────────────── ✨ Safe to Execute ────────────────────────────────────────╯
실행하시겠습니까? [y/n/?] (n): y
🚀 Starting command execution...

⚡ Executing command (1/1): netstat -tulpn 2>/dev/null | grep ':5678' | awk '{print NR ". PID: " $7 "
⠋ 🚀 Executing command...
═══════════ Command Output ═══════════
📝 Output:
1. PID: - - Process: -
2. PID: - - Process: -
══════════════════════════════════════
All commands completed. Next action? (d=done, r=retry) [d/r] (d): r
╭────────────────────────────────────── 🤖 Command to Execute ──────────────────────────────────────╮
│ 🔒 sudo lsof -i :5678 | tail -n +2 | awk '{print NR ". PID: " $2 " - Process: " $1}'              │
╰──────────────────────────────────────── 🔒 Requires Sudo ─────────────────────────────────────────╯
실행하시겠습니까? [y/n/?] (n): y
🚀 Starting command execution...

⚡ Executing command (1/1): sudo lsof -i :5678 | tail -n +2 | awk '{print NR ". PID: " $2 " -
Process: " $1}'
🔐 Please enter sudo password:

⠙ 🚀 Executing command...
═══════════ Command Output ═══════════
📝 Output:
1. PID: 2908449 - Process: docker-pr
2. PID: 2908475 - Process: docker-pr
══════════════════════════════════════
```