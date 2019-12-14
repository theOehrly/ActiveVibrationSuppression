import sys

from PyQt5.Qt import QThread, QApplication, pyqtSignal, QIcon, QFileDialog, QComboBox
from PyQt5.QtWidgets import QSizePolicy, QHBoxLayout, QVBoxLayout, QWidget, QToolBar, QDialog, QSlider, QLabel, QMessageBox

from pyqtgraph import PlotWidget

from settingsdialog import SettingsDialog
from settings import readConfiguration
from virtualmachine import Machine
from gcode import GCode
import strings


class MainWindow(QWidget):
    def __init__(self, appinst, profilecon, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = appinst
        self.profilecon = profilecon  # connector class instance for reading/writing profile settings
        self.gcode = None
        self.machine = None

        self.backgroundTask = None
        self.postBackgroundTask = None

        self.coord_plot_items = list() # list of all plot items added to the coord plot

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
        self.toolBar.addSeparator()
        self.add_toolbar_action("./res/maximize.svg", "Fit to View", self.fit_plot_to_window)
        self.add_toolbar_action("./res/maximize-2.svg", "Reset View", self.reset_plot_view)
        self.toolBar.addSeparator()
        self.profileSelector = QComboBox()
        for name in self.profilecon.list_profiles():
            self.profileSelector.addItem(name)
        self.profilecon.select_profile(self.profileSelector.currentText())
        self.toolBar.addWidget(self.profileSelector)
        self.profileSelector.currentTextChanged.connect(self.selected_profile_changed)
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
        self.coordPlot.setAspectLocked(True)
        # self.coordPlot.setLimits(xMin=0, yMin=0)
        self.configure_plot()  # is done in a seperate funciton because values need to be updated after settings are changed
        self.contentLayout.addWidget(self.coordPlot)

        self.sidebarlayout = QVBoxLayout()
        self.contentLayout.addLayout(self.sidebarlayout)

        self.sidebarheader = QLabel("Options")
        self.sidebarheader.setFixedSize(300, 50)
        self.sidebarlayout.addWidget(self.sidebarheader)

    def configure_plot(self):
        self.coordPlot.invertX(self.profilecon.get_value("invert_x"))  # needs to be done before setting the axis ranges because
        self.coordPlot.invertY(self.profilecon.get_value("invert_y"))  # inverting does not update the viewbox, but setting the range does
        self.coordPlot.setXRange(self.profilecon.get_value("bed_min_x"), self.profilecon.get_value("bed_max_x"))
        self.coordPlot.setYRange(self.profilecon.get_value("bed_min_y"), self.profilecon.get_value("bed_max_y"))

    def selected_profile_changed(self, new_profile):
        # select the new profile in the settings connector and update the ui accordingly
        self.profilecon.select_profile(new_profile)
        self.configure_plot()

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
        # in case a file is open already, close it properly first
        if self.machine:
            ret = self.close_file()
            if not ret:
                # user canceled closing of current file; can't open new one
                return

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
        dialog = SettingsDialog(self, self.profilecon)
        dialog.exec()

        # update settings
        self.configure_plot()

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
        # close the current gcode file, discard all data
        # Before, ask for user confirmation
        cfmsgbox = QMessageBox()
        cfmsgbox.setWindowTitle("Close file?")
        cfmsgbox.setText("Are you sure you want to close the current file and discard all unsaved data?")
        cfmsgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        cfmsgbox.setDefaultButton(QMessageBox.No)
        ret = cfmsgbox.exec()

        if ret == QMessageBox.Yes:
            for item in self.coord_plot_items:
                self.coordPlot.removeItem(item)

            self.machine = None
            self.gcode = None
            # TODO: fix: this will not terminate a running background process
            return True

        return False

    def export(self):
        pass

    def start_simulation(self):
        pass

    def fit_plot_to_window(self):
        x, y = self.machine.get_path_coordinates(layer_number=self.layerSlider.value())
        self.coordPlot.setRange(xRange=(min(x), max(x)), yRange=(min(y), max(y)))

    def reset_plot_view(self):
        self.coordPlot.setXRange(self.profilecon.get_value("bed_min_x"), self.profilecon.get_value("bed_max_x"))
        self.coordPlot.setYRange(self.profilecon.get_value("bed_min_y"), self.profilecon.get_value("bed_max_y"))

    def load_data(self, filename):
        # initalizes a virtual machine from the gcode in the file given
        # all path data for this gcode is calculated; this is a cpu intensive task!
        self.gcode = GCode()
        self.gcode.load_file(filename)
        self.machine = Machine(self.gcode, self.profilecon)
        self.machine.create_path()

        # set the layer sliders maximum to represent the given amount of layers and enable the slider
        self.layerSlider.setMaximum(len(self.machine.layers) - 1)
        self.layerSlider.setEnabled(True)

    def show_layer(self):
        # plot path for the layer selected by the layer slider
        x, y = self.machine.get_path_coordinates(layer_number=self.layerSlider.value())
        pltitm = self.coordPlot.plot(x, y, clear=True)
        self.coord_plot_items.append(pltitm)


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
    app.setApplicationName("Active Vibration Suppression")
    app.setApplicationVersion("0.0.1")

    try:
        settingsconnector, profileconnector = readConfiguration()

    except PermissionError:
        # cannot read/create configuration and cannot start without
        msgbox = QMessageBox()
        msgbox.setWindowTitle("Application Error")
        msgbox.setText("Failed to read and/or create one or more configuration file(s). Cannot start application!")
        msgbox.setStandardButtons(QMessageBox.Ok)
        msgbox.exec()
        sys.exit(-1)

    else:
        window = MainWindow(app, profileconnector)
        window.show()

    app.exec()
