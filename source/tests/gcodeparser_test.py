import unittest

from gcode import GCode


class GcodeParserTest(unittest.TestCase):
    def test_single_int(self):
        gcode = GCode()
        gcode.load_file("gc_single_int.gcode")

        # check if only one command
        self.assertEqual(len(gcode.commands), 1)

        # check command recognized correctly
        self.assertTrue(gcode.commands[0].has_param("G"))
        self.assertEqual(gcode.commands[0].get_param("G"), 5)

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
        self.assertEqual(len(gcode.commands), 12)

        cnt = 0
        for i in range(len(gcode.commands)):
            if gcode.commands[i].is_comment_only():
                cnt += 1

        self.assertEqual(cnt, 2)  # two lines should contain only a comment

        # check correct command recognition
        self.assertEqual(gcode.commands[1].get_param("G"), 1)
        self.assertEqual(gcode.commands[2].get_param("G"), 0)
        self.assertEqual(gcode.commands[3].get_param("G"), 10)
        self.assertEqual(gcode.commands[4].get_param("G"), 16)
        self.assertEqual(gcode.commands[5].get_param("G"), 1)
        self.assertEqual(gcode.commands[6].get_param("G"), 1)
        self.assertEqual(gcode.commands[7].get_param("G"), 1)

        self.assertEqual(gcode.commands[9].get_param("G"), 0)
        self.assertEqual(gcode.commands[10].get_param("G"), 1)
        self.assertEqual(gcode.commands[11].get_param("G"), 17)

        for i in range(1, 8):  # batch check for lines 1 to 7
            # check if parameters were found
            self.assertEqual(gcode.commands[i].has_param("X"), True)
            self.assertEqual(gcode.commands[i].has_param("Y"), True)

            # check if values were found
            self.assertEqual(gcode.commands[i].get_param("X"), 500)
            self.assertEqual(gcode.commands[i].get_param("Y"), 400)

            # check validity
            self.assertEqual(gcode.commands[i].is_valid(), True)

        for i in range(1,4):
            # check if comment was found by checking for "Test comment"
            self.assertEqual("Test comment" in gcode.commands[i].comment, True)

        ###################################
        # check the last three lines extra
        #
        # weird but valid line formatting (NIST example)
        self.assertEquals(gcode.commands[9].get_param("X"), 0.1234)
        self.assertEquals(gcode.commands[9].get_param("Y"), 7)

        # negative signs
        self.assertEqual(gcode.commands[10].get_param("X"), -5)
        self.assertEqual(gcode.commands[10].get_param("Y"), -0.17)

        # this is the no-hex-check
        self.assertEqual(gcode.commands[11].get_param("X"), 500)
        self.assertEqual(gcode.commands[11].get_param("Y"), 0)

    def test_weird_comments(self):
        gcode = GCode()
        gcode.load_file("gc_weird_comments.gcode")

        # check correct number of commands
        self.assertEqual(len(gcode.commands), 6)

        g_lines = 0
        for i in range(6):
            if gcode.commands[i].has_param("G"):
                g_lines += 1

                # check correct command recognition
                self.assertTrue(gcode.commands[i].get_param("G"), 1)

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

    def test_g01_equal_g1(self):
        gcode = GCode()
        gcode.load_file("gc_g1_equals_g01.gcode")

        self.assertEqual(len(gcode.commands), 3)  # three commands should be loaded

        for i in range(3):
            self.assertEqual(gcode.commands[i].get_param("G"), 1)


if __name__ == '__main__':
    unittest.main()
