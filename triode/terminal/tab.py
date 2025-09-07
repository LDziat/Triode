# triode/terminal/tab.py
# Requires: pip install pyte

import os
import pty
import fcntl
import termios
import struct
import subprocess
import errno
import signal
import tty
import collections
from typing import Optional
import shlex

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PySide6.QtCore import Signal, Qt, QSocketNotifier, QTimer
from PySide6.QtGui import QTextCursor, QFont, QGuiApplication

import pyte

BRACKETED_PASTE_START = b'\x1b[200~'
BRACKETED_PASTE_END = b'\x1b[201~'


class TerminalWidget(QTextEdit):
    """A read-only QTextEdit optimized for terminal display."""
    def __init__(self, write_callback, parent=None):
        super().__init__(parent)
        self.write_callback = write_callback
        self.cwd = os.path.expanduser("~")

        self.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #FFFFFF;
                padding: 5px;
                border: none;
                font-family: Menlo, Monaco, 'Courier New', monospace;
                font-size: 11pt;
            }
        """)
        
        self.setAcceptRichText(False)
        self.setLineWrapMode(QTextEdit.NoWrap)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setReadOnly(True)
        self.setFocusPolicy(Qt.StrongFocus)

        font = QFont("Menlo", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        self.setFont(font)

        self.document().setMaximumBlockCount(10000)

    def set_plain_text_and_scroll(self, text: str):
        """Replaces the entire text and scrolls to the bottom."""
        self.setPlainText(text)
        QTimer.singleShot(0, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        """Moves the vertical scrollbar to its maximum value."""
        scroll_bar = self.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())

    def keyPressEvent(self, event):
        """Converts Qt key events to bytes and forwards them to the PTY."""
        try:
            key = event.key()
            mods = event.modifiers()

            if mods & Qt.ControlModifier:
                if key == Qt.Key_V:
                    text = QGuiApplication.clipboard().text()
                    if text:
                        data = BRACKETED_PASTE_START + text.encode('utf-8') + BRACKETED_PASTE_END
                        self.write_callback(data)
                    event.accept()
                    return
                if key == Qt.Key_C:
                    if self.textCursor().hasSelection():
                        self.copy()
                    else:
                        self.write_callback(b'\x03') # SIGINT
                    event.accept()
                    return
                if Qt.Key_A <= key <= Qt.Key_Z:
                    self.write_callback(bytes([key - Qt.Key_A + 1]))
                    event.accept()
                    return

            key_map = {
                Qt.Key_Return: b'\r', Qt.Key_Enter: b'\r', Qt.Key_Backspace: b'\x7f',
                Qt.Key_Tab: b'\t', Qt.Key_Up: b'\x1b[A', Qt.Key_Down: b'\x1b[B',
                Qt.Key_Right: b'\x1b[C', Qt.Key_Left: b'\x1b[D', Qt.Key_Home: b'\x1b[H',
                Qt.Key_End: b'\x1b[F', Qt.Key_Delete: b'\x1b[3~',
            }
            if key in key_map:
                self.write_callback(key_map[key])
            else:
                text = event.text()
                if text:
                    self.write_callback(text.encode('utf-8'))
            
            event.accept()
        except Exception as exc:
            print(f"Terminal keyPressEvent error: {exc}")
            event.accept()


class ScreenWithHistory(pyte.Screen):
    """A pyte.Screen subclass that manually manages a scrollback buffer."""
    def __init__(self, columns, lines, history_size=10000):
        super().__init__(columns, lines)
        self.history = collections.deque(maxlen=history_size)

    def scroll_up(self, n):
        """Overrides the default scroll_up to capture scrolled-off lines."""
        # This is called *before* the screen buffer is scrolled.
        # We capture the lines that are about to be lost from the top.
        for i in range(n):
            line_to_scroll = self.buffer.get(i)
            if line_to_scroll:
                line_text = "".join(char.data for char in line_to_scroll.values())
                self.history.append(line_text)
        
        super().scroll_up(n)


class TerminalTab(QWidget):
    """Manages a PTY session and renders its state to a TerminalWidget."""
    path_changed = Signal(str)

    def __init__(self, initial_path: Optional[str] = None, shell: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.cwd = os.path.abspath(initial_path or os.path.expanduser("~"))
        self.shell = shell or os.environ.get("SHELL", "/bin/bash")

        # Initialize with a standard default size. It will be resized immediately anyway.
        self.screen = ScreenWithHistory(80, 24, history_size=10000)
        self.stream = pyte.Stream()
        self.stream.attach(self.screen)

        self.master_fd, self.process = self._spawn_pty(self.shell, self.cwd)

        self.terminal = TerminalWidget(write_callback=self._write_to_master, parent=self)
        self.layout.addWidget(self.terminal)

        if self.master_fd is not None:
            flags = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
            fcntl.fcntl(self.master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            self.notifier = QSocketNotifier(self.master_fd, QSocketNotifier.Read, self)
            self.notifier.activated.connect(self._on_master_ready)

        self._render_timer = QTimer(self)
        self._render_timer.setInterval(16)
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._render_screen)

        QTimer.singleShot(0, self._do_initial_resize)
        self.path_changed.emit(self.cwd)

    def navigate_to(self, path: str):
        """
        Change the working directory inside the PTY shell session.
        Handles spaces and escape characters safely.
        """
        if not path:
            return

        # Expand ~ and relative paths
        new_path = os.path.abspath(os.path.expanduser(path))

        if not os.path.isdir(new_path):
            error_message = f"cd: no such file or directory: {new_path}\n"
            self.terminal.set_plain_text_and_scroll(
                self.terminal.toPlainText() + error_message
            )
            return

        # Safely escape the path for the shell
        escaped_path = shlex.quote(new_path)

        # Send the cd command

        self._write_to_master("\n".encode("utf-8"))
        cd_command = f"cd {escaped_path}\n".encode("utf-8")
        self._write_to_master(cd_command)

        # Update internal state and notify listeners
        self.cwd = new_path
        self.path_changed.emit(self.cwd)

        # Optional: confirm visually in terminal
        #self._write_to_master(b"pwd\n")

    def _spawn_pty(self, shell_cmd: str, cwd: str):
        master_fd, slave_fd = pty.openpty()
        
        try:
            tty.setraw(slave_fd)
            attrs = termios.tcgetattr(slave_fd)
            attrs[3] &= ~termios.ECHO
            termios.tcsetattr(slave_fd, termios.TCSANOW, attrs)
        except (termios.error, AttributeError):
            pass

        env = os.environ.copy()
        env.update({"TERM": "xterm-256color"})

        try:
            process = subprocess.Popen(
                [shell_cmd, "--login"],
                preexec_fn=os.setsid,
                stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
                env=env, cwd=cwd, close_fds=False
            )
        except FileNotFoundError:
            process = subprocess.Popen(
                [shell_cmd],
                preexec_fn=os.setsid,
                stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
                env=env, cwd=cwd, close_fds=False
            )

        os.close(slave_fd)
        return master_fd, process

    def _write_to_master(self, data: bytes):
        if self.master_fd is not None:
            try:
                os.write(self.master_fd, data)
            except OSError:
                pass

    def _on_master_ready(self):
        try:
            data = os.read(self.master_fd, 4096)
            if data:
                self.stream.feed(data.decode('utf-8', errors='replace'))
                if not self._render_timer.isActive():
                    self._render_timer.start()
        except (OSError, BlockingIOError):
            pass
        except Exception as exc:
            print(f"PTY read error: {exc}")

    def _render_screen(self):
        history_lines = [line.rstrip() for line in self.screen.history]
        # Use the .display property which is the canonical way to get screen content
        visible_lines = [line.rstrip() for line in self.screen.display]
        full_text = "\n".join(history_lines + visible_lines)
        self.terminal.set_plain_text_and_scroll(full_text)

    def _do_initial_resize(self):
        """
        Calculates terminal dimensions based on the widget's viewport size and font metrics.
        This is the critical method for ensuring the shell and the display agree on the size.
        """
        fm = self.terminal.fontMetrics()
        
        # Use averageCharWidth() for a more stable calculation than 'M'.
        char_width = fm.averageCharWidth()
        char_height = fm.height()

        # Abort if the widget is not ready and font metrics are invalid.
        if char_width <= 0 or char_height <= 0:
            return
        
        viewport = self.terminal.viewport()
        scrollbar = self.terminal.verticalScrollBar()

        # The effective drawable width is the viewport's width minus the scrollbar's width.
        # The viewport size already accounts for the stylesheet's padding.
        effective_width = viewport.width()
        if scrollbar.isVisible():
            effective_width -= scrollbar.width()

        # Calculate the final number of columns and rows.
        cols = max(10, int(effective_width / char_width))
        rows = max(5, int(viewport.height() / char_height))
        
        self.resize_terminal(rows, cols)

    def resize_terminal(self, rows: int, cols: int):
        self.screen.resize(lines=rows, columns=cols)
        winsz = struct.pack('HHHH', rows, cols, 0, 0)
        fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsz)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._do_initial_resize()

    def closeEvent(self, event):
        if self.master_fd:
            os.close(self.master_fd)
            self.master_fd = None
        if self.process and self.process.poll() is None:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except ProcessLookupError:
                pass
        super().closeEvent(event)
