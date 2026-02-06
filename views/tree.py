from PySide6 import QtWidgets
from PySide6.QtCore import * 
from PySide6.QtGui import * 
import os
import json
import qjsonmodel


class Tree(QtWidgets.QWidget):
    """A widget that wraps a QTreeView and its JSON model."""
    def __init__(self, parent=None):
        super().__init__(parent)

        self.view = QtWidgets.QTreeView(self)
        self.model = qjsonmodel.QJsonModel()
        self.view.setModel(self.model)
        self.view.setHeaderHidden(True)


        json_path = os.path.join(os.path.dirname(__file__), "network.json")
        with open(json_path, 'r', encoding='utf-8') as f:
            document = json.load(f)
        self.model.load(document)

        
        self.button = QtWidgets.QLabel("BKA")

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.button)
        layout.addWidget(self.view)


