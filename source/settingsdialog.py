from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QComboBox, QPushButton, QDoubleSpinBox, QSpinBox, QCheckBox, \
    QGridLayout, QLabel, QInputDialog, QFrame, QMessageBox
from PyQt5.Qt import QIcon


class SettingsDialog(QDialog):
    def __init__(self, main, profilecon):
        super().__init__()

        self.profilecon = profilecon
        self.main = main

        self.setWindowTitle("Settings")

        layout = QVBoxLayout()
        self.setLayout(layout)

        # BOX1 ##### profile selection #####
        box1 = QGroupBox("Profile")
        layout.addWidget(box1)
        box1_layout = QFormLayout()
        box1.setLayout(box1_layout)

        self.profile_selector = QComboBox()
        for name in self.profilecon.list_profiles():
            self.profile_selector.addItem(name)
        self.profile_selector.setCurrentIndex(self.main.profileSelector.currentIndex())
        self.profile_selector.currentTextChanged.connect(self.selected_profile_changed)
        box1_layout.addRow("", self.profile_selector)

        changes_layout = QHBoxLayout()
        save = QPushButton(QIcon("./res/save.svg"), "Save")
        save.setToolTip("Save changes")
        save_new_profile = QPushButton(QIcon("./res/plus-circle.svg"), "Save New")
        save_new_profile.setToolTip("Save changes to a new profile")
        undo = QPushButton(QIcon("./res/rotate-ccw.svg"), "Reset")
        undo.setToolTip("Reset unsaved changes")
        divider = QFrame()
        divider.setFrameShape(QFrame.VLine)
        delete = QPushButton(QIcon("./res/trash-2.svg"), "")
        delete.setToolTip("Delete current profile")

        changes_layout.addWidget(save)
        changes_layout.addWidget(save_new_profile)
        changes_layout.addWidget(undo)
        changes_layout.addWidget(divider)
        changes_layout.addWidget(delete)

        box1_layout.addRow("", changes_layout)

        save.pressed.connect(self.save_settings)
        save_new_profile.pressed.connect(self.save_new_profile)
        undo.pressed.connect(self.set_field_values)
        delete.pressed.connect(self.delete_profile)

        # BOX2 ##### bed size configuration #####
        box2 = QGroupBox("Bed")
        layout.addWidget(box2)
        self.box2_layout = QGridLayout(box2)

        self.bed_min_x = QSpinBox()
        self.bed_min_x.setProperty("key", "bed_min_x")
        lbl_min_x = QLabel("Minimum X")
        self.box2_layout.addWidget(lbl_min_x, 0, 0)
        self.box2_layout.addWidget(self.bed_min_x, 0, 1)

        self.bed_min_y = QSpinBox()
        self.bed_min_y.setProperty("key", "bed_min_y")
        lbl_min_y = QLabel("Minimum Y")
        self.box2_layout.addWidget(lbl_min_y, 1, 0)
        self.box2_layout.addWidget(self.bed_min_y, 1, 1)

        self.bed_max_x = QSpinBox()
        self.bed_max_x.setProperty("key", "bed_max_x")
        lbl_max_x = QLabel("Maximum X")
        self.box2_layout.addWidget(lbl_max_x, 2, 0)
        self.box2_layout.addWidget(self.bed_max_x, 2, 1)

        self.bed_max_y = QSpinBox()
        self.bed_max_y.setProperty("key", "bed_max_y")
        lbl_max_y = QLabel("Maximum Y")
        self.box2_layout.addWidget(lbl_max_y, 3, 0)
        self.box2_layout.addWidget(self.bed_max_y, 3, 1)

        for box in (self.bed_min_x, self.bed_min_y, self.bed_max_x, self.bed_max_y):
            box.setMinimum(-10000)
            box.setMaximum(10000)

        self.invert_x = QCheckBox()
        self.invert_x.setProperty("key", "invert_x")
        lbl_inv_x = QLabel("Invert X")
        self.box2_layout.addWidget(lbl_inv_x, 4, 0)
        self.box2_layout.addWidget(self.invert_x, 4, 1)

        self.invert_y = QCheckBox()
        self.invert_y.setProperty("key", "invert_y")
        lbl_inv_y = QLabel("Invert Y")
        self.box2_layout.addWidget(lbl_inv_y, 5, 0)
        self.box2_layout.addWidget(self.invert_y, 5, 1)

        self.bed_min_x.valueChanged.connect(lambda: self.field_value_changed(self.bed_min_x))
        self.bed_min_y.valueChanged.connect(lambda: self.field_value_changed(self.bed_min_y))
        self.bed_max_x.valueChanged.connect(lambda: self.field_value_changed(self.bed_max_x))
        self.bed_max_y.valueChanged.connect(lambda: self.field_value_changed(self.bed_max_y))
        self.invert_x.toggled.connect(lambda: self.field_value_changed(self.invert_x))
        self.invert_y.toggled.connect(lambda: self.field_value_changed(self.invert_y))

        # BOX 3 ##### speed, acceleration, ... limits #####
        box3 = QGroupBox("Kinematics")
        layout.addWidget(box3)
        self.box3_layout = QGridLayout(box3)

        self.min_speed = QSpinBox()
        self.min_speed.setProperty("key", "min_speed")
        self.min_speed.setMinimum(1)
        self.min_speed.setMaximum(5000)
        lbl_min_speed = QLabel("Minimum Speed [mm/s]")
        self.box3_layout.addWidget(lbl_min_speed, 0, 0)
        self.box3_layout.addWidget(self.min_speed, 0, 1)

        self.acceleration = QSpinBox()
        self.acceleration.setProperty("key", "acceleration")
        self.acceleration.setMinimum(1)
        self.acceleration.setMaximum(100000)
        lbl_acceleration = QLabel("Acceleration [mm/s²]")
        self.box3_layout.addWidget(lbl_acceleration, 1, 0)
        self.box3_layout.addWidget(self.acceleration, 1, 1)

        self.junction_dev = QDoubleSpinBox()
        self.junction_dev.setProperty("key", "junction_dev")
        self.junction_dev.setMinimum(0)
        self.junction_dev.setDecimals(2)
        self.junction_dev.setSingleStep(0.01)
        lbl_jdev = QLabel("Junction Deviation")
        self.box3_layout.addWidget(lbl_jdev, 2, 0)
        self.box3_layout.addWidget(self.junction_dev, 2, 1)

        self.min_speed.valueChanged.connect(lambda: self.field_value_changed(self.min_speed))
        self.acceleration.valueChanged.connect(lambda: self.field_value_changed(self.acceleration))
        self.junction_dev.valueChanged.connect(lambda: self.field_value_changed(self.junction_dev))

        # ##### List of All Settings Fields in This Dialog ##### #
        self.settings_fields = (self.bed_min_x, self.bed_min_y, self.bed_max_x, self.bed_max_y,
                                self.invert_x, self.invert_y, self.min_speed, self.acceleration,
                                self.junction_dev)

        self.set_field_values()

    def set_field_values(self):
        for field in self.settings_fields:
            if type(field) in (QSpinBox, QDoubleSpinBox):
                field.setValue(self.profilecon.get_value(field.property("key")))
            elif type(field) == QCheckBox:
                field.setChecked(self.profilecon.get_value(field.property("key")))

    def showEvent(self, event):
        self.finish_column_sizing()  # column width of QGridLayout is only known after parent widget is shown
        self.setFixedSize(self.size())  # disable possibility to resize the dialog
        super().showEvent(event)

    def finish_column_sizing(self):
        # align all columns in the QGridLayouts by setting the minimum width for all first columns to the width
        # of the widest first column
        max_width = 0
        for layout in (self.box2_layout, self.box3_layout):
            max_width = max(max_width, layout.cellRect(0, 1).x())
        for layout in (self.box2_layout, self.box3_layout):
            layout.setColumnMinimumWidth(0, max_width)

    def field_value_changed(self, field):
        # compare field value to settings value
        if type(field) in (QSpinBox, QDoubleSpinBox):
            if not field.value() == self.profilecon.get_value(field.property("key")):
                field.setStyleSheet("""QWidget {background-color: yellow;}""")
            else:
                field.setStyleSheet("""QWidget {background-color: None;}""")

        elif type(field) == QCheckBox:
            if not field.isChecked() == self.profilecon.get_value(field.property("key")):
                field.setStyleSheet("""QWidget {background-color: yellow;}""")
            else:
                field.setStyleSheet("""QWidget {background-color: None;}""")

    def selected_profile_changed(self, new_profile):
        self.profilecon.select_profile(new_profile)
        self.set_field_values()

        self.main.profileSelector.setCurrentIndex(self.profile_selector.currentIndex())  # update combobox in toolbar of mainwindow

    def save_settings(self):
        for field in self.settings_fields:
            if type(field) in (QSpinBox, QDoubleSpinBox):
                self.profilecon.set_value(field.property("key"), field.value())
            elif type(field) == QCheckBox:
                self.profilecon.set_value(field.property("key"), field.isChecked())

            self.field_value_changed(field)

        self.profilecon.save_to_file()

    def save_new_profile(self):
        name, ok = QInputDialog().getText(self, "Input", "Enter a name for the new profile:")
        if ok:  # only proceed if user didn't cancel
            self.profilecon.add_profile(name)
            self.profilecon.save_to_file()

            self.profilecon.select_profile(name)
            self.save_settings()

            self.profile_selector.addItem(name)
            self.main.profileSelector.addItem(name)
            self.profile_selector.setCurrentIndex(self.profile_selector.count() - 1)  # select last (i.e. newest) item

    def delete_profile(self):
        msgbox = QMessageBox()
        msgbox.setWindowTitle("Delete profile?")
        msgbox.setText("Are you sure you want to delete the current profile?")
        msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msgbox.setDefaultButton(QMessageBox.No)
        ret = msgbox.exec()

        if ret == QMessageBox.Yes:
            self.profilecon.delete_current_profile()
            self.profilecon.save_to_file()

            self.main.profileSelector.removeItem(self.main.profileSelector.currentIndex())  # update combobox in toolbar of mainwindow
            # needs to be done first, because modifying the combo box from the settings dialog updates the index of the combo box in the toolbar
            self.profile_selector.removeItem(self.profile_selector.currentIndex())

            self.profilecon.select_profile(self.profile_selector.currentText())
