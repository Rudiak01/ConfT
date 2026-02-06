from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsRectItem, QGraphicsLineItem, QApplication, QGraphicsItem
from PySide6.QtCore import Qt, QPointF, QLineF, QRectF
from PySide6.QtGui import QPen, QBrush, QPainter


class Node(QGraphicsRectItem):
    def __init__(self, name, rect=QRectF(-50, -25, 100, 50)):
        super().__init__(rect)
        self.name = name
        self.edges = []
        self.setBrush(QBrush(Qt.lightGray))
        self.setPen(QPen(Qt.black))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)

    def add_edge(self, edge):
        self.edges.append(edge)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            for edge in self.edges:
                edge.adjust()
        return super().itemChange(change, value)


class Edge(QGraphicsLineItem):
    def __init__(self, source_node, dest_node):
        super().__init__()
        self.source = source_node
        self.dest = dest_node
        self.source.add_edge(self)
        self.dest.add_edge(self)
        self.setPen(QPen(Qt.blue, 2))
        self.adjust()

    def adjust(self):
        self.prepareGeometryChange()
        self.setLine(
            QLineF(
                self.source.pos() + self.source.boundingRect().center(),
                self.dest.pos() + self.dest.boundingRect().center(),
            )
        )


class GraphView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)

        # Create nodes
        node1 = Node("Node 1")
        node1.setPos(100, 100)
        node2 = Node("Node 2")
        node2.setPos(300, 150)
        # Add nodes to scene
        self.scene.addItem(node1)
        self.scene.addItem(node2)
        
        # Create and add edge
        edge = Edge(node1, node2)
        self.scene.addItem(edge)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    view = GraphView()
    view.resize(600, 400)
    view.show()
    sys.exit(app.exec())
