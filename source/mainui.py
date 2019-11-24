import sys

from PyQt5.Qt import QThread, QTimer, QApplication, pyqtSignal, QIcon, QFileDialog
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, QToolBar, QToolButton, QSlider, QLabel
from PyQt5.QtCore import Qt

from pyqtgraph import PlotWidget

from virtualmachine import Machine, AccelerationFromTime, SpeedFromTime
from gcode import GCode

import time


class MainWindow(QWidget):
    def __init__(self, appinst, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = appinst
        self.gcode = None
        self.machine = None

        self.backgroundTask = None
        self.postBackgroundTask = None

        self.toolbar_actions = dict()

        self.mainlayout = QVBoxLayout(self)
        self.mainlayout.setContentsMargins(0, 0, 0, 0)

        self.toolBar = QToolBar()
        self.toolBar.setStyleSheet("""QToolBar {background-color: white;
                                                border-top: 1px solid black}""")
        self.mainlayout.addWidget(self.toolBar)

        self.add_toolbar_action("./res/folder.svg", "Open", self.open_file_dialog)

        self.contentLayout = QHBoxLayout()
        self.contentLayout.setContentsMargins(10, 10, 10, 10)
        self.mainlayout.addLayout(self.contentLayout)

        self.layerSlider = QSlider()
        self.layerSlider.setMinimum(0)
        self.layerSlider.setValue(0)
        self.layerSlider.setDisabled(True)
        self.layerSlider.valueChanged.connect(self.show_layer)
        self.contentLayout.addWidget(self.layerSlider)

        self.coordPlot = PlotWidget()
        self.contentLayout.addWidget(self.coordPlot)

        self.sidebarlayout = QVBoxLayout()
        self.contentLayout.addLayout(self.sidebarlayout)

        self.sidebarheader = QLabel("Options")
        self.sidebarheader.setMinimumSize(300, 50)
        self.sidebarlayout.addWidget(self.sidebarheader)

        # self.finish_init()

    def add_toolbar_action(self, icon, text, function):
        open_icon = QIcon(icon)
        action = self.toolBar.addAction(open_icon, text)
        action.triggered.connect(function)

    def finish_init(self):
        self.run_in_background(self.load_data, after=self.show_layer)

    def finish_background_task(self):
        self.postBackgroundTask()
        self.postBackgroundTask = None
        self.backgroundTask = None

    def run_in_background(self, task, after=None, args=None):
        self.backgroundTask = BackgroundTask(task)
        if args:
            self.backgroundTask.set_arguments(args)
        self.backgroundTask.finished.connect(self.finish_background_task)
        self.postBackgroundTask = after
        self.backgroundTask.start()

    def open_file_dialog(self):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.ExistingFile)
        filters = ["G-code (*.gcode)", "Any files (*)"]
        dialog.setNameFilters(filters)
        dialog.selectNameFilter(filters[0])
        dialog.setViewMode(QFileDialog.Detail)

        filename = None
        if dialog.exec_():
            filename = dialog.selectedFiles()

        if filename:
            self.run_in_background(self.load_data, after=self.show_layer, args=filename)

    def load_data(self, filename):
        self.gcode = GCode()
        self.gcode.load_file(filename)
        self.machine = Machine(self.gcode)
        self.machine.create_path()

        self.layerSlider.setMaximum(len(self.machine.layers) - 1)
        self.layerSlider.setEnabled(True)

    def show_layer(self):
        # plot path
        x, y = self.machine.get_path_coordinates(layer_number=self.layerSlider.value())
        self.coordPlot.plot(x, y, clear=True)


class BackgroundTask(QThread):
    finished = pyqtSignal()

    def __init__(self, func, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.func = func
        self.arguments = list()

    def set_arguments(self, args):
        self.arguments = args

    def run(self):
        self.func(*self.arguments)
        self.finished.emit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow(app)
    window.setWindowTitle('AVS')
    window.show()
    app.exec()
