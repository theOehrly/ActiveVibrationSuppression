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
    Default = DefaultSettingsConf

    def __init__(self, filename):
        self._filename = filename
        self._data = self.read_file(self._filename)

        self.check_configuration()  # check for new or deprecated settings keys an update the config accordingly
        self.save_to_file()  # save, in case any changes were made

    def get_value(self, key):
        return self._data[key]

    def set_value(self, key, value):
        self._data[key] = value

    def read_file(self, filename):
        with open(filename, "r") as json_conf:  # read settings file
            data = json.load(json_conf, object_pairs_hook=OrderedDict)
        return data

    def save_to_file(self):
        with open(self._filename, "w") as json_conf:
            json.dump(self._data, json_conf, indent=4)

    def check_configuration(self):
        # this function makes sure that all keys present in the default configuration are also present in the current configuration file
        # new keys: if a key is missing, it will be added with the default value
        # old keys: if a key is not in the defaults but in the current config, it will be removed
        # this enables easily adding features afterwards which require new settings

        default_keys = list(self.Default)

        # old keys
        for key in list(self._data):
            if key not in default_keys:
                del self._data[key]

        # new keys
        for i in range(len(self.Default)):
            key = default_keys[i]
            if key not in self._data:
                # It is intentionally only checked if the key exists and NOT if it exists at the same position even though it should.
                # If the order of the configuration file gets messed up, the worst thing that can happen this way, is even worse order.
                # If it is checked for that specific index, keys might be created as duplicates.
                self._data = insert_into_dict(self._data, key, self.Default[key], i)

    def create_empty_config(self, filename):
        with open(filename, "w") as json_conf:
            json.dump(self.Default, json_conf, indent=4)


class JsonProfilesConnector(JsonSettingsConnector):
    Default = DefaultProfileConf

    def __init__(self, filename):
        # super().__init__() is intentionally not called as parts of this init would need
        # to run in the middle of the super classes init function
        # init is therefore fully implemented here
        self._filename = filename
        self._data = self.read_file(self._filename)

        self._profile = str()  # name of the currently selected profile
        self._data = None  # data of the current profile; equals _all_profiles[_profile]
        self._all_profiles = self.read_file(self._filename)  # data of all profiles

        self.select_profile(list(self._all_profiles.keys())[0])  # select a profile by default TODO Remember last selected profile

        self.check_configuration()  # check for new or deprecated settings keys an update the config accordingly
        self.save_to_file()  # save, in case any changes were made

    def list_profiles(self):
        return list(self._all_profiles)

    def select_profile(self, profile):
        self.sync_to_all()
        if profile in self.list_profiles():
            self._profile = profile
            self._data = self._all_profiles[self._profile]
        else:
            raise ValueError("Invalid Profile Name!")

    def get_profile(self):
        return self._profile

    def add_profile(self, name):
        self._all_profiles[name] = OrderedDict()

    def delete_current_profile(self):
        # TODO prevent deletion if only one profile, or automatically recreate a default one
        del self._all_profiles[self._profile]

    def check_configuration(self):
        # iterate through all profiles and check them seperately
        profile_before = self._profile
        for profile in self.list_profiles():
            self.select_profile(profile)
            super().check_configuration()

        self.select_profile(profile_before)  # select the previously selected profile again

    def sync_to_all(self):
        # all functions read and modify self._data which is a copy of self._all_profiles[self.profile]
        # any modifications made to it need to be copied back to self._all_profiles before saving or changing profile
        if self._profile and self._data:
            self._all_profiles[self._profile] = self._data

    def save_to_file(self):
        self.sync_to_all()
        with open(self._filename, "w") as json_conf:
            json.dump(self._all_profiles, json_conf, indent=4)


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
