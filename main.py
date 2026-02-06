from PySide6.QtCore import * 
from PySide6.QtGui import * 
from PySide6 import __version__
import sys

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
)

from views.tree import Tree
from views.helloworld import hello



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("My App")

        MAIN_hor = QHBoxLayout()
        left = QVBoxLayout()
        right = QVBoxLayout()

        left.addWidget(Tree())

        MAIN_hor.addLayout( left )
        MAIN_hor.setStretch(0, 1)

        right.addWidget(hello())
        right.addWidget(hello())

        MAIN_hor.addLayout( right )
        MAIN_hor.setStretch(1, 1)

        widget = QWidget()
        widget.setLayout(MAIN_hor)
        self.setCentralWidget(widget)



if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    window.setWindowState(Qt.WindowMaximized)
    sys.exit(app.exec())