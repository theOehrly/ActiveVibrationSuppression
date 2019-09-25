
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

        # save original line for writing data again later or for debugging
        if self.keep_invalid or self.keep_raw:
            gcommand.original = line

        # ###################
        # #### clean up data

        # remove line breaks, they are not needed and may cause problems
        line = line.replace("\r", "").replace("\n", "").replace("\t", " ")

        # find first character in line. prevents fail in case of leading spaces
        i = 0  # should not be necessary; make sure i is defined after the for loop
        for i in range(len(line)):
            if not line[i].isspace():
                # yes this also accepts invalid first characters
                # but I want to keep data clean up and interpretation seperate
                break
        line = line[i:]

        # ####################
        # #### interpret data

        instruction, comment = self._split_instruction_comment(line)

        gcommand.comment = comment

        if instruction:
            success = self._parse_instruction(gcommand, instruction, line, linenumber)
            if not success:
                return

        gcommand.validate()
        self.commands.append(gcommand)

    @staticmethod
    def _split_instruction_comment(line):
        """Split the provided line of gcode into a instruction and a comment part

        :param line: line of gcode
        :type line: str
        :return: str, str: instruction, comment
        """
        i_split = line.find(';')  # get index for start of comment (if any)

        if i_split == -1:
            # line contains no comment
            instruction = line
            comment = str()
        else:
            # split instruction and comment
            instruction = line[0:i_split]  # start to comment start index
            comment = str(line[i_split:])  # comment start index to end

        return instruction, comment

    def _segment_instructions(self, gcommand, instruction, line, linenumber):
        """Segment a gcode instruction line into its parameters.

        Example: "G02 X6 Y70" --> ("G02 ", "X6 ", "Y70 ")

        :param gcommand: class instance of current gcommand
        :type gcommand: GCommand
        :param instruction: the instruction part of the current line
        :type instruction: str
        :param line: the full gcode line
        :type line: str
        :param linenumber: index of the line in the file
        :type linenumber: int
        :return: list of strings or None in case of error
        """
        # check that there is a space infront of every parameter (parameter -> alpha character)
        # also don't check the very first character as there are no leading spaces before (obviously)
        for i in range(1, len(instruction)):
            if instruction[i].isalpha() and not instruction[i - 1] == " ":
                self._invalid_line(gcommand, line, linenumber,
                                   add_msg="Invalid formatting - missing space character before parameter '{}' at "
                                           "postion {}".format(instruction[i], i + 1))
                return

        # segment instruction, therefore split string at alpha characters
        # each segement is appended to the "segmented" list
        segmented = list()
        i = 0
        while instruction:
            i += 1
            if i >= len(instruction):
                # We reached the end. The remaining part of instruction must therefore be one segment.
                segmented.append(instruction)
                break

            # recognize paramters by checking if character is a alpha character
            # if it is, the part infront(!) of it is considered to be one parameter
            # basically we're looking for the end of a parameter, copy the parameter to the list and
            # slice the parameter out of the list afterwards
            if instruction[i].isalpha():
                segmented.append(instruction[:i])
                instruction = instruction[i:]
                i = 0

        return segmented

    def _parse_instruction(self, gcommand, instruction, line, linenumber):
        """Parse the given instruction and add all parameters to the gcommand.

        :param gcommand: class instance of current gcommand
        :type gcommand: GCommand
        :param instruction: the instruction part of the current line
        :type instruction: str
        :param line: the full gcode line
        :type line: str
        :param linenumber: index of the line in the file
        :type linenumber: int
        :return: True if successfull, else False"""

        # replace multiple spaces with a single space so that only single spaces occur
        while " " * 2 in instruction:
            instruction = instruction.replace(" " * 2, " ")

        # split the instruction into mutliple segments, each containing one parameter
        segmented = self._segment_instructions(gcommand, instruction, line, linenumber)
        if not segmented:
            return False  # can happen in case of invalid lines

        # parse first parameter, i.e. Gcode type separate
        gtype = segmented.pop(0)
        if not gtype[0] in "GMTgmt":
            # first charcter needs to be one of upper or lower case G, M, T
            self._invalid_line(gcommand, line, linenumber,
                               add_msg="Missing G, M or T parameter or parameter is not in first position")
            return False

        # Set the gtype. This automatically also sets gcommand.gnumber and gcommand.g/m/t
        try:
            gcommand.set_gtype(gtype)
        except ValueError:
            self._invalid_line(gcommand, line, linenumber,
                               add_msg="Invalid command: '{}'".format(gtype))
            return False

        # split each parameter into a letter and a corresponding float
        for param in segmented:
            try:
                key = str(param[0])
                value = float(param[1:])
            except ValueError:
                self._invalid_line(gcommand, line, linenumber,
                                   add_msg="Failed to seperate variable name and value")
                return False

            # check for multiple commands on one line; T is allowed to occur with M or G commands
            if key.upper() == "G" or key.upper() == "M":
                self._invalid_line(gcommand, line, linenumber,
                                   add_msg="Command '{}' is not allowed as a parameter".format(param))
                return False

            gcommand.set_param(key, value)

        return True

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

        self._gtype = str()
        self._gnumber = int()
        self._g = False
        self._m = False
        self._t = False

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
        self._gtype = gtype.strip(" ").upper()
        self._set_gnumber(int(gtype[1:]))

        if self._gtype[0] == 'G':
            self._g = True
        elif self._gtype[0] == 'M':
            self._m = True
        elif self._gtype[0] == "T":
            self._t = True
        else:
            raise ValueError

    def get_gtype(self):
        """Returns this commands gtype.

        gtype is for example 'G15"

        :return: str
        """
        return self._gtype

    def is_gtype(self, gtype):         # TODO write test

        """Check if this is the same command as the provided gtype.

        This will treat G1 equal to G01 equal to G001 and so on.

        :param gtype: GCode command; example 'G15'
        :type gtype: str
        :return: bool
        """
        return True if (gtype[0] == self._gtype[0] and self.is_gnumber(int(gtype[1:]))) else False

    def _set_gnumber(self, gnumber):
        """Sets this command's gcode number.

        Don't use this directly. Always use set_gtype to prevent conflicting data.

        :param gnumber: Number of the gcode command. E.g. 15 for G15
        :type gnumber: int
        :return: None
        """
        self._gnumber = gnumber

    def get_gnumber(self):
        """Get this command's gcode number.

        :return: int: Number of this gcode command. E.g. 15 for G15
        """
        return self._gnumber

    def is_gnumber(self, gnumber):
        """Check if this command's gcode number is the same as the provided number.

        :param gnumber: Number of the gcode command. E.g. 15 for G15
        :type gnumber: int
        :return: bool
        """
        return True if gnumber == self._gnumber else False

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

    def g(self):
        """Check if this command is a G command.

        Example command: 'G01'
        """
        return True if self._g else False

    def m(self):
        """Check if this command is a M command.

        Example command: 'M01'
        """
        return True if self._m else False

    def t(self):
        """Check if this command is a T command.

        Example command: 'T01'
        """
        return True if self._t else False

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
