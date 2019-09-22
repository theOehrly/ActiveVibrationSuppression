import unittest

from gcode import GCode


class GcodeParserTest(unittest.TestCase):
    def test_single_int(self):
        gcode = GCode()
        gcode.load_file("gc_single_int.gcode")

        # check if only one command
        self.assertEqual(len(gcode.commands), 1)

        # check command recognized correctly
        self.assertEqual(gcode.commands[0].g, True)
        self.assertEqual(gcode.commands[0].gtype, "G5")
        self.assertEqual(gcode.commands[0].gnumber, 5)

        # check parameters recognized correctly and upper/lowercase compatibility
        self.assertEqual(gcode.commands[0].has_param("X"), True)
        self.assertEqual(gcode.commands[0].has_param("x"), True)
        self.assertEqual(gcode.commands[0].has_param("Y"), True)
        self.assertEqual(gcode.commands[0].has_param("y"), True)

        self.assertEqual(gcode.commands[0].get_param("X"), 500)
        self.assertEqual(gcode.commands[0].get_param("Y"), 400)

        # check validity
        self.assertEqual(gcode.commands[0].is_valid(), True)

    def test_multi_int(self):
        gcode = GCode()
        gcode.load_file("gc_multi_int.gcode")

        # check correct number of commands
        self.assertEqual(len(gcode.commands), 4)

        # check correct command recognition
        self.assertEqual(gcode.commands[0].gtype, "G1")
        self.assertEqual(gcode.commands[1].gtype, "G0")
        self.assertEqual(gcode.commands[2].gtype, "G10")
        self.assertEqual(gcode.commands[3].gtype, "G16")

        for i in range(4):
            # check if parameters were found
            self.assertEqual(gcode.commands[i].has_param("X"), True)
            self.assertEqual(gcode.commands[i].has_param("Y"), True)

            # check if values were found
            self.assertEqual(gcode.commands[i].get_param("X"), 500)
            self.assertEqual(gcode.commands[i].get_param("Y"), 400)

            # check validity
            self.assertEqual(gcode.commands[i].is_valid(), True)

        # check if comment was found
        # last line has no comment, therefore only test three lines
        for i in range(3):
            self.assertEqual("Test comment" in gcode.commands[i].comment, True)

    def test_weird_comments(self):
        gcode = GCode()
        gcode.load_file("gc_weird_comments.gcode")

        # check correct number of commands
        self.assertEqual(len(gcode.commands), 6)

        g_lines = 0
        for i in range(6):
            if gcode.commands[i].g:
                g_lines += 1

                # check correct command recognition
                self.assertEqual(gcode.commands[i].gtype, "G1")

                # check if parameters were found
                self.assertEqual(gcode.commands[i].has_param("X"), True)
                self.assertEqual(gcode.commands[i].has_param("Y"), True)
                self.assertEqual(gcode.commands[i].has_param("E"), True)

                # check if values were found
                self.assertEqual(gcode.commands[i].get_param("X"), 50)
                self.assertEqual(gcode.commands[i].get_param("Y"), 50)
                self.assertEqual(gcode.commands[i].get_param("E"), 50.75)

            # check validity
            self.assertEqual(gcode.commands[i].is_valid(), True)

        self.assertEqual(g_lines, 4)

        for i in range(5):
            # check if a comment was found (last line has none there fore only range(5))
            self.assertNotEqual(gcode.commands[i].comment, None)

    def test_invalid_commands(self):
        # none of the lines should load with default parameters
        # therefore every line needs to be checked seperatly
        with open("gc_invalid_commands.gcode", "r") as fobj:
            linenumber = 0
            for line in fobj.readlines():
                gcode = GCode()
                with self.assertRaises(ValueError, msg="GCode Line {}: \n {}".format(linenumber, line)):
                    gcode.parse_line(line, linenumber)

        # load and ignore errors, keep lines
        gcode = GCode(ignore_invalid=True, keep_invalid=True)
        gcode.load_file("gc_invalid_commands.gcode")

        self.assertEqual(len(gcode.commands), 4)  # four commands should be loaded

        for i in range(4):
            self.assertEqual(gcode.commands[i].is_valid(), False)  # no command should be valid

        # load and ignore errors, discard lines
        gcode = GCode(ignore_invalid=True, keep_invalid=False)
        gcode.load_file("gc_invalid_commands.gcode")

        self.assertEqual(len(gcode.commands), 0)   # no commands should be loaded


if __name__ == '__main__':
    unittest.main()
