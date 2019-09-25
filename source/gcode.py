# tests: G1/G01, tabs
# Todo: add function for checking equality where "G02" == "G2"
# Todo GCommand only access through functions for data sanity checking
# Todo: parser: split into multiple functions


class GCode:
    def __init__(self, keep_invalid=False, ignore_invalid=False, keep_raw=False):
        """ This class holds all current Gcode as a list of GCommands.

        :param keep_invalid: Should invalid lines be kept anyways as raw data?
        Can be usefull if gcode should be written to a file again.
        :type keep_invalid: bool
        :param ignore_invalid: Should invalid lines be ignored? Raises a ValueError if not.
        :type ignore_invalid: bool
        :param keep_raw: Keep unmodified original line. Usefull for debugging.
        :type keep_raw: bool
        """
        self.keep_invalid = keep_invalid
        self.ignore_invalid = ignore_invalid
        self.keep_raw = keep_raw

        self.commands = list()

    def load_file(self, fpath):
        """Reads a new file and parses all GCode in it.

        :param fpath: Filepath
        :type fpath: str
        :return: nothing
        """
        n = 1
        with open(fpath, 'r') as infile:
            for line in infile.readlines():
                self.parse_line(line, n)
                n += 1

    def parse_line(self, line, linenumber):
        """Parses a single gcode line and creates a GCommand from it if valid.

        The new GCommand is appended to GCode.commands

        :param line: The gcode line to be parsed
        :type line: str
        :param linenumber: Position of the line in the input text file
        :type linenumber: int
        :return: nothing
        """
        if not line:
            return

        gcommand = GCommand()
        gcommand.linenumber = linenumber

        # save original line for writing later or debugging
        if self.keep_invalid or self.keep_raw:
            gcommand.original = line

        # remove line breaks, they are not needed and may cause problems
        line = line.replace("\r", "").replace("\n", "")

        # find first character in line. prevents fail in case of leading spaces
        i = 0  # should not be necessary; make sure i is defined after the for loop
        for i in range(len(line)):
            if not line[i].isspace():
                # yes this also accepts invalid first characters
                # but I want to keep data clean up and interpretation seperate
                break
        line = line[i:]

        i_split = line.find(';')  # get index for start of comment (if any)

        if i_split == -1:
            # line contains no comment
            instruction = line
            comment = str()
        else:
            # split instruction and comment
            instruction = line[0:i_split]  # start to comment start index
            comment = str(line[i_split:])  # comment start index to end

        gcommand.comment = comment

        if instruction:
            # replace multiple spaces with a single space so that only single spaces occur
            while " " * 2 in instruction:
                instruction = instruction.replace(" " * 2, " ")

            # first character needs to be one of instruction G, M or T
            if instruction[0].upper() == "G":
                gcommand.g = True
            elif instruction[0].upper() == "M":
                gcommand.m = True
            elif instruction[0].upper() == "T":
                gcommand.t = True
            else:
                self._invalid_line(gcommand, line, linenumber,
                                   add_msg="Missing G, M or T parameter or parameter is not in first position")
                return

            # check that there is a space infront of every parameter (alpha character)
            for i in range(1, len(instruction)):
                if instruction[i].isalpha() and not instruction[i-1] == " ":
                    self._invalid_line(gcommand, line, linenumber,
                                       add_msg="Invalid formatting - missing space character before parameter '{}' at "
                                               "postion {}".format(instruction[i], i+1))
                    return

            # segment instruction; split string at alpha characters
            # each segement is appended to the "segmented" list
            segmented = list()
            i = 0
            while instruction:
                i += 1
                if i >= len(instruction):
                    # no more alpha characters after, remaining part of instruction is one segment
                    segmented.append(instruction)
                    break

                # check to ensure variable names are alpha characters
                if instruction[i].isalpha():
                    segmented.append(instruction[:i])
                    instruction = instruction[i:]
                    i = 0

            # parse first parameter, i.e. Gcode type separate
            gtype = segmented.pop(0)
            try:
                gcommand.set_gtype(gtype)
            except ValueError:
                self._invalid_line(gcommand, line, linenumber,
                                   add_msg="Invalid command: '{}'".format(gtype))
                return

            # split each parameter into a letter and a corresponding float
            for param in segmented:
                try:
                    key = str(param[0])
                    value = float(param[1:])
                except ValueError:
                    self._invalid_line(gcommand, line, linenumber,
                                       add_msg="Failed to seperate variable name and value")
                    return

                # check for multiple commands on one line; T is allowed to occur with M or G commands
                if key.upper() == "G" or key.upper() == "M":
                    self._invalid_line(gcommand, line, linenumber,
                                       add_msg="Command '{}' is not allowed as a parameter".format(param))
                    return

                gcommand.set_param(key, value)

        gcommand.validate()
        self.commands.append(gcommand)

    def _invalid_line(self, gcommand, line, linenumber, add_msg=str()):
        """Handles invalid lines depending on set options.

        Depending on self.keep_invalid and self.ignore_invalid, the lines are either

        - kept but not used and marked as invalid
        - ignored and discarded
        - a ValueError is thrown

        :param gcommand: class instance for the current line's GCommand
        :type gcommand: GCommand
        :param line: origninal line as read without any modifications
        :type line: str
        :param linenumber: position of the line in the input text file
        :type linenumber: int
        :param add_msg: Optional error message for further description when raising ValueError
        :type add_msg: str
        :returns: nothing
        """

        if self.ignore_invalid and not self.keep_invalid:
            # line is completely ignored and skipped
            return
        elif self.ignore_invalid and self.keep_invalid:
            # line is kept but not validated; command, parameters, comment can not be determined
            gcommand.original = line
            gcommand.clear_params()
            self.commands.append(gcommand)
        else:
            raise ValueError("\nLine {} in GCode is not valid: \n '{}' \n {}".format(linenumber, line, add_msg))


class GCommand:
    def __init__(self):
        """This class holds data for a single GCommand.
        """
        self._valid = False  # set to False by default; forced to actively mark commands as valid!

        self.gtype = str()
        self.gnumber = int()
        self.g = False
        self.m = False
        self.t = False

        self._parameters = dict()
        self.comment = str()

        self.linenumber = int()

        self.original = str()  # only used when debug option is set for class <GCode>

    def set_gtype(self, gtype):
        """Sets the gtype, also automatically sets the gnumber accordingly.

        :param gtype: GCode command; example 'G15'
        :type gtype: str
        :return: None
        """
        self.gtype = gtype.strip(" ")
        self.gnumber = int(gtype[1:])

    def set_param(self, param, value):
        """Add a parameter/value pair.

        This will create a new parameter or overwrite existing ones.

        :param param: GCode parameter; e.g. 'X' or 'E'
        :type param: str
        :param value: Value for Parameter
        :type value: int/float
        :return: None
        """
        self._parameters[param.upper()] = float(value)

    def get_param(self, param):
        """Return the value associated with the given parameter.

        :param param: GCode parameter; e.g. 'X' or 'E'
        :type param: str
        :return: float
        """
        return self._parameters[param.upper()]

    def has_param(self, param):
        """Has this command the specified parameter?

        :param param: GCode parameter; e.g. 'X' or 'E'
        :type param: str
        :return: bool
        """
        if param.upper() in self._parameters.keys():
            return True
        return False

    def clear_params(self):
        """Delete all paramters

        :return: None"""

        self._parameters.clear()

    def is_valid(self):
        """Is this a valid line/command?

        :return: bool
        """
        return self._valid

    def validate(self):
        """Validate this gcommand.

        This means the parser understood everything and it is uasable.

        :return: None"""
        self._valid = True
