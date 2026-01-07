import sys
import os
from PySide6.QtWidgets import QApplication

# Ensure project root is on sys.path even if launched from elsewhere
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from resources.ui_main import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())