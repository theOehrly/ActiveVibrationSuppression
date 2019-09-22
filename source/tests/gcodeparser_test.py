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


if __name__ == '__main__':
    unittest.main()
