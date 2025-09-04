# triode/terminal/command_wrapper.py
from typing import Optional
import re

class CommandWrapper:
    MARK_CWD = "[[TRIODE-CWD]]"
    MARK_END = "[[TRIODE-END]]"
    PATTERN = re.compile(r"\[\[TRIODE-CWD\]\](.*?)\[\[TRIODE-END\]\]")

    def wrap_posix(self, user_cmd: str) -> str:
        # Wrap a user command to print a sentinel with the cwd afterwards.
        # We use bash grouped command to ensure cd builtins take effect.
        safe_cmd = user_cmd.rstrip("\n")
        return f"{{ {safe_cmd}; }}; printf '{self.MARK_CWD}%s{self.MARK_END}\\n' \"$(pwd)\"\n"

    def wrap_windows(self, user_cmd: str) -> str:
        # For cmd.exe; powershell would be different (Phase-0 keep cmd/powershell separate)
        safe = user_cmd.rstrip("\r\n")
        return f"{safe} & echo {self.MARK_CWD}%CD%{self.MARK_END}\r\n"

    def extract_cwd(self, stream: str) -> Optional[str]:
        m = self.PATTERN.search(stream)
        if m:
            return m.group(1)
        return None
