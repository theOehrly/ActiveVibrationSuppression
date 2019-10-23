# ##################################
# AVS GCode Parser
#
# Copyright 2019, Philipp Schaefer
# ##################################
# GLine class: Data from a single line of GCode
# GCode class: Holds multiple GLines and does parsing of input text data
#
# ########################################################
# GCode Naming Conventions According to NIST RS274NGC V3
# ------------------------------------------------------
# see "https://www.nist.gov/publications/nist-rs274ngc-interpreter-version-3" for comparison
#
#
# Example Line: N01 G02 X50 Y60 ; example line
#
#
# Block:        Lines are also sometimes called Blocks
# Word:         A letter followed by a number is considered a Word, e.g 'G02' or 'X50'
# Commands:     Words starting with "G", "M" or "T" are Commands.
# Arguments:    Words starting with orther characters than "G", "M", "T" or "N" are Arguments
# Line Number:  "N01" or in genreral "N*" is a Line Number. They are optional and not considered to be a word.
#                Line Numbers must be at the very beginning of a Line
#
# The input is NOT case sensitive. That means "G01 X50" is the same as "g01 x50".
#
#
# ##########################################################
# Explanantions concerning specifically this software
# ---------------------------------------------------
# Where this code uses a variable called "linenumber" this refers to the actual line number in a file.
# If the Line Number as defined above ("N*") is meant this is specifically refered to as "linenumber_gcode".
# The line number in a file is, where both versions are used, also refered to as "linenumber_file" for clarity.


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

        self._lines = list()
        self._i_iter_lines = 0

    def __iter__(self):
        """Get the iterator for iterating through all lines of GCode.

        :return: self
        """
        self._i_iter_lines = 0
        return self

    def __next__(self):
        """Get the next line of GCode.

        :returns: GLine
        """
        self._i_iter_lines += 1
        if self._i_iter_lines <= len(self._lines):
            return self._lines[self._i_iter_lines - 1]
        else:
            raise StopIteration

    def __getitem__(self, key):
        """Get the GLine object at the specified position.

        :param key: (List)index of GLine object
        :type key: int
        :returns: GLine"""
        return self._lines[key]

    def __len__(self):
        """Get the number of glines.

        :returns int"""
        return len(self._lines)

    def load_file(self, fpath):
        """Reads a new file and parses all GCode in it.

        :param fpath: Filepath
        :type fpath: str
        """
        n = 1
        with open(fpath, 'r') as infile:
            for line in infile.readlines():
                self.parse_line(line, n)
                n += 1

    def parse_line(self, line, linenumber):
        """Parses a single gcode line and creates a GLine from it if valid.

        The new GLine is appended to GCode._lines

        :param line: The gcode line to be parsed
        :type line: str
        :param linenumber: Position of the line in the input text file
        :type linenumber: int
        """

        gline = GLine()
        gline.linenumber_file = linenumber

        # save original line for writing data again later or for debugging
        if self.keep_invalid or self.keep_raw:
            gline.original = line

        # ###################
        # #### clean up data

        # remove line breaks and tabs, they are not needed and may cause problems
        line = line.replace("\r", "").replace("\n", "").replace("\t", " ")
        if not line:
            return  # line was empty

        # ####################
        # #### interpret data

        words, comment = self._split_words_from_comment(line)

        gline.comment = comment

        if words:
            success = self._parse_words(gline, words, line, linenumber)
            if not success:
                return

        gline.validate()
        self._lines.append(gline)

    @staticmethod
    def _split_words_from_comment(line):
        """Split the provided line of gcode into a part containing all words and a comment part

        :param line: line of gcode
        :type line: str
        :return: word, comment
        """
        i_split = line.find(';')  # get index for start of comment (if any)

        if i_split == -1:
            # line contains no comment
            word = line
            comment = str()
        else:
            # split word and comment
            word = line[0:i_split]  # start to comment start index
            comment = line[i_split:]  # comment start index to end

        return word, comment

    @staticmethod
    def _segment_words(line):
        """Segment a string of words into a list of independent words.

        Example: "G02X6Y70" --> ("G02", "X6", "Y70")
        (Space or tab characters are already remvoved beforehand

        :param line: a line containing multiple words but NO comment (are removed before)
        :type line: str
        :return: list of strings (words)
        """

        # segment line, therefore split string at alpha characters
        # each segement is one word is appended to the "words" list
        words = list()
        i = 0
        while line:
            i += 1
            if i >= len(line):
                # We reached the end. The remaining part of line must therefore be one word.
                words.append(line)
                break

            # recognize words by checking if character is a alpha character
            # if it is, the part infront(!) of it is considered to be one word
            # basically we're looking for the beginning of the following word not the end of the current one
            # the word is then sliced out of the line
            if line[i].isalpha():
                words.append(line[:i])
                line = line[i:]
                i = 0

        return words

    def _parse_words(self, gcommand, instruction, line, linenumber):
        """Parse the given instruction and add all parameters to the gcommand.

        :param gcommand: class instance of current gcommand
        :type gcommand: GLine
        :param instruction: the instruction part of the current line
        :type instruction: str
        :param line: the full gcode line
        :type line: str
        :param linenumber: index of the line in the file
        :type linenumber: int
        :return: True if successfull, else False"""

        # replace multiple spaces with a single space so that only single spaces occur
        instruction = instruction.replace(" ", "")

        # split the instruction into mutliple segments, each containing one parameter
        words = self._segment_words(instruction)
        if not words:
            return False  # can happen in case of invalid lines

        # split each parameter into a letter and a corresponding float
        for word in words:
            try:
                letter = str(word[0])
                value = float(word[1:])
            except ValueError:
                self._invalid_line(gcommand, line, linenumber,
                                   add_msg="Failed to seperate letter and value of word: '{}'".format(word))
                return False

            try:
                gcommand.set_word(letter, value)
            except ValueError:
                # intentionally raised when a word occurs for the second time on the same line
                self._invalid_line(gcommand, line, linenumber, add_msg="Invalid parameter '{}'".format(word))
                return False

        return True

    def _invalid_line(self, gline, line, linenumber, add_msg=str()):
        """Handles invalid lines depending on set options.

        Depending on self.keep_invalid and self.ignore_invalid, the lines are either

        - kept but not used and marked as invalid
        - ignored and discarded
        - a ValueError is thrown

        :param gline: class instance for the current GLine
        :type gline: GLine
        :param line: origninal line as read without any modifications
        :type line: str
        :param linenumber: position of the line in the input text file
        :type linenumber: int
        :param add_msg: Optional error message for further description when raising ValueError
        :type add_msg: str
        """

        if self.ignore_invalid and not self.keep_invalid:
            # line is completely ignored and skipped
            return
        elif self.ignore_invalid and self.keep_invalid:
            # line is kept but not validated; command, parameters, comment can not be determined
            gline.original = line
            gline.clear_words()
            self._lines.append(gline)
        else:
            raise ValueError("\nLine {} in GCode is not valid: \n '{}' \n {}".format(linenumber, line, add_msg))


class GLine:
    def __init__(self):
        """This class holds data of a single line of gcode."""

        self._valid = False  # set to False by default; forced to actively mark commands as valid!

        self._words = dict()
        self.comment = str()

        self.linenumber_file = int()  # linenumber in file; also counts comment only lines and blank lines
        self.linenumber_gcode = -1  # does not exist by default; is provided optionally in gcode

        self.original = str()  # only used when debug option is set for class <GCode>

    def is_comment_only(self):
        """Check if this line only consists of a comment and has no actual gcode."""
        return True if not self._words else False

    def set_word(self, letter, value, overwrite=False):
        """Add a parameter/value pair.

        This will create a new parameter or overwrite existing ones.

        :param letter: Letter of a gcode word; e.g. 'X' or 'E'
        :type letter: str
        :param value: Value (Number) of a gcode word.
        :type value: int/float
        :param overwrite: Only overwrite existing words if set to true
        :type overwrite: bool
        """
        if letter.upper() == "N":
            self.linenumber_gcode = int(value)  # line numbers are treated seperately

        elif self.has_word(letter) and not overwrite:
            raise ValueError
        else:
            self._words[letter.upper()] = float(value)

    def get_word(self, letter):
        """Return the value associated with the specified word.

        :param letter: Letter of a gcode word; e.g. 'X' or 'E'
        :type letter: str
        :return: Value of the specified word
        """
        return self._words[letter.upper()]

    def has_word(self, letter):
        """Has this line the specified word?

        :param letter: Letter of a gcode word; e.g. 'X' or 'E'
        :type letter: str
        :return: True or False
        """
        if letter.upper() in self._words.keys():
            return True
        return False

    def clear_words(self):
        """Delete all words of this line."""
        self._words.clear()

    def is_valid(self):
        """Returns whether this is a valid gcode line?

        :return: True or False
        """
        return self._valid

    def validate(self):
        """Validate this gline.

        This means the parser understood everything and it is usable.
        """
        self._valid = True
