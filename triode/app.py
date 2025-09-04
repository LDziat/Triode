# triode/app.py
import sys
from PySide6.QtWidgets import QApplication
from .main_window import MainWindow
from .settings import load_settings

class TriodeApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("Triode")

def main():
    settings = load_settings()
    app = TriodeApp(sys.argv)
    win = MainWindow(settings=settings)
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
