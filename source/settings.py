import os
import json

DefaultSettings = {"App_Version": "0.0.1",
                   "Window_Position": [300, 500],
                   "Window_Size": [1000, 700],
                   "Current_Profile": None}

DefaultProfile = {"Default": {"bed_min_x": 0,
                              "bed_min_y": 0,
                              "bed_max_x": 200,
                              "bed_max_y": 200,
                              "invert_x": False,
                              "invert_y": False,
                              "min_speed": 10,
                              "acceleration": 2500,
                              "junction_dev": 0.05}
                  }


class JsonSettingsConnector:
    def __init__(self, filename):
        self._filename = filename
        self._data = None

        self.read_file(self._filename)

    def get_value(self, key):
        return self._data[key]

    def set_value(self, key, value):
        self._data[key] = value

    def read_file(self, filename):
        with open(filename, "r") as json_conf:  # read settings file
            self._data = json.load(json_conf)

    def save_to_file(self):
        with open(self._filename, "w") as json_conf:
            json.dump(self._data, json_conf)

    @staticmethod
    def create_empty_config(filename):
        with open(filename, "w") as json_conf:
            json.dump(DefaultSettings, json_conf)


class JsonProfilesConnector:
    def __init__(self, filename):
        self._filename = filename
        self._profile = None
        self._data = None

        self.read_file(self._filename)

        self.select_profile(list(self._data.keys())[0])  # select a profile by default TODO Remember last selected profile

    def list_profiles(self):
        return self._data.keys()

    def select_profile(self, profile):
        if profile in self.list_profiles():
            self._profile = profile
        else:
            raise ValueError("Invalid Profile Name!")

    def get_profile(self):
        return self._profile

    def add_profile(self, name):
        self._data[name] = dict()

    def delete_current_profile(self):
        # TODO prevent deletion if only one profile, or automatically recreate a default one
        del self._data[self._profile]

    def get_value(self, key):
        return self._data[self._profile][key]

    def set_value(self, key, value):
        self._data[self._profile][key] = value

    def read_file(self, filename):
        with open(filename, "r") as json_conf:  # read settings file
            self._data = json.load(json_conf)

    def save_to_file(self):
        with open(self._filename, "w") as json_conf:
            json.dump(self._data, json_conf)

    @staticmethod
    def create_empty_config(filename):
        with open(filename, "w") as json_conf:
            json.dump(DefaultProfile, json_conf)


def readConfiguration():
    # This function reads all configuration files and returns the associated conectors for reading and writing.
    #
    # The function will try to create missing directories and configuration files based on the defaults
    # This can cause a permission error. Permission errors are not caught in this function. Instead the are caught
    # in the startup part of the app which is calling this function.
    # If the permission error is thrown, a popup window with an error message will be shown.

    # Config file path is platform dependent
    # For now only windows gets properly treated
    if os.sys.platform == "win32":
        # create a application folder in appdata/roaming and save configuration files there
        conf_path = os.path.join(os.environ['APPDATA'], 'ActiveVibrationSuppression')
        if not os.path.isdir(conf_path):
            os.makedirs(conf_path)

    else:
        # all other systems save their config into the application folder for now
        conf_path = "./"

    profiles_path = os.path.join(conf_path, "profiles.conf")
    settings_path = os.path.join(conf_path, "settings.conf")

    ret = list()  # List for returing all connectors
    for connector, path in zip((JsonSettingsConnector, JsonProfilesConnector),
                               (settings_path, profiles_path)):
        try:
            inst = connector(path)
        except FileNotFoundError:
            # no config found, try creating an empty one
            connector.create_empty_config(path)
            inst = connector(path)

        ret.append(inst)

    return ret
