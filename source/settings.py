import os
import json

from collections import OrderedDict

# Default Values for App Settings
DefaultSettingsConf = OrderedDict([("App_Version", "0.0.1"),
                                   ("Window_Position", [300, 500]),
                                   ("Window_Size", [1000, 700]),
                                   ("Current_Profile", None)])


# Default Values for Printer Profiles
default_profile = OrderedDict([("bed_min_x", 0),
                              ("bed_min_y", 0),
                              ("bed_max_x", 200),
                              ("bed_max_y", 200),
                              ("invert_x", False),
                              ("invert_y", False),
                              ("min_speed", 10),
                              ("acceleration", 2500),
                              ("junction_dev", 0.05)])

DefaultProfileConf = OrderedDict()["Default"] = default_profile


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
            self._data = json.load(json_conf, object_pairs_hook=OrderedDict)

        self.check_configuration()

    def save_to_file(self):
        with open(self._filename, "w") as json_conf:
            json.dump(self._data, json_conf, indent=4)

    def check_configuration(self):
        # this function makes sure that all keys present in the default configuration are also present in the current configuration file
        # new keys: if a key is missing, it will be added with the default value
        # old keys: if a key is not in the defaults but in the current config, it will be removed
        # this enables easily adding features afterwards which require new settings

        default_keys = list(DefaultSettingsConf)

        # old keys
        for key in list(self._data):
            if key not in default_keys:
                del self._data[key]

        # new keys
        for i in range(len(DefaultSettingsConf)):
            key = default_keys[i]
            if key not in self._data:
                # It is intentionally only checked if the key exists and NOT if it exists at the same position even though it should.
                # If the order of the configuration file gets messed up, the worst thing that can happen this way, is even worse order.
                # If it is checked for that specific index, keys might be created as duplicates.
                self._data = insert_into_dict(self._data, key, DefaultSettingsConf[key], i)

        self.save_to_file()

    @staticmethod
    def create_empty_config(filename):
        with open(filename, "w") as json_conf:
            json.dump(DefaultSettingsConf, json_conf, indent=4)


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
            self._data = json.load(json_conf, object_pairs_hook=OrderedDict)

    def save_to_file(self):
        with open(self._filename, "w") as json_conf:
            json.dump(self._data, json_conf, indent=4)

    @staticmethod
    def create_empty_config(filename):
        with open(filename, "w") as json_conf:
            json.dump(DefaultProfileConf, json_conf, indent=4)


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


def insert_into_dict(_dict, new_key, new_value, index):
    # This is not that nice of a solution because dictionaries are not really ordered. Still json.dump considers the "order" when dumping to a file.
    # When adding extra settings options it is nice if the can be inserted at specific positions in the current settings file to maintain
    # human readability. Therefore this function is needed.

    keys = list(_dict)
    temp = dict()

    # insert in the middle
    if index < len(_dict):
        for i in range(len(_dict)):
            if i == index:
                temp[new_key] = new_value
            temp[keys[i]] = _dict[keys[i]]

    # append to the end
    else:
        temp = {**_dict, new_key: new_value}

    return temp
