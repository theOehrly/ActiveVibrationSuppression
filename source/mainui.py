import sys

from PyQt5.Qt import QThread, QTimer, QApplication, pyqtSignal, QIcon, QFileDialog, QFont
from PyQt5.QtWidgets import QSizePolicy, QHBoxLayout, QVBoxLayout, QWidget, QToolBar, QDialog, QSlider, QLabel
from PyQt5.QtCore import Qt

from pyqtgraph import PlotWidget

from virtualmachine import Machine, AccelerationFromTime, SpeedFromTime
from gcode import GCode
import strings

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
        self.add_toolbar_action("./res/x-square.svg", "Close", self.close_file)
        self.add_toolbar_action("./res/save.svg", "Export", self.export)
        self.toolBar.addSeparator()
        self.add_toolbar_action("./res/sliders.svg", "Settings", self.open_settings_dialog)
        self.add_toolbar_action("./res/play.svg", "Simulate", self.start_simulation)
        divider = QWidget()
        divider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolBar.addWidget(divider)
        self.add_toolbar_action("./res/info.svg", "About", self.open_about_dialog)

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

    def add_toolbar_action(self, icon, text, function):
        # wrapper function for adding a toolbar button and connecting it to trigger a function
        open_icon = QIcon(icon)
        action = self.toolBar.addAction(open_icon, text)
        action.triggered.connect(function)

    def finish_background_task(self):
        # function is called when a background task finishes
        if self.postBackgroundTask:
            # run cleanup task (i.e. ui update); runs on main ui thread!
            self.postBackgroundTask()
        # reset variables
        self.postBackgroundTask = None
        self.backgroundTask = None

    def run_in_background(self, task, after=None, args=None):
        # wrapper function for creating and starting a thread to run a function in the background
        # arguments can be passed to the function in the thread and a cleanup function can be specified
        # which is run on the main ui thread when the background task is finished
        self.backgroundTask = BackgroundTask(task)
        if args:
            self.backgroundTask.set_arguments(args)
        self.backgroundTask.finished.connect(self.finish_background_task)
        self.postBackgroundTask = after
        self.backgroundTask.start()

    def open_file_dialog(self):
        # open dialog for selecting a gcode file to be loaded
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

    def open_settings_dialog(self):
        # open a dialog with settings
        pass

    def open_about_dialog(self):
        # open the about dialog
        dialog = QDialog()
        dialog.setWindowTitle("About...")

        layout = QVBoxLayout()
        dialog.setLayout(layout)

        text = QLabel(strings.about)
        layout.addWidget(text)

        dialog.exec()

    def close_file(self):
        pass

    def export(self):
        pass

    def start_simulation(self):
        pass

    def load_data(self, filename):
        # initalizes a virtual machine from the gcode in the file given
        # all path data for this gcode is calculated; this is a cpu intensive task!
        self.gcode = GCode()
        self.gcode.load_file(filename)
        self.machine = Machine(self.gcode)
        self.machine.create_path()

        # set the layer sliders maximum to represent the given amount of layers and enable the slider
        self.layerSlider.setMaximum(len(self.machine.layers) - 1)
        self.layerSlider.setEnabled(True)

    def show_layer(self):
        # plot path for the layer selected by the layer slider
        x, y = self.machine.get_path_coordinates(layer_number=self.layerSlider.value())
        self.coordPlot.plot(x, y, clear=True)


class BackgroundTask(QThread):
    # thread class for easily running cpu intensive functions in a second thread
    finished = pyqtSignal()

    def __init__(self, func, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.func = func
        self.arguments = list()

    def set_arguments(self, args):
        # set arguments that should be passed to the executed function
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
