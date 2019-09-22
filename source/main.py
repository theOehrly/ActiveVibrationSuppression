from gcode import GCode

gcode = GCode(ignore_invalid=False, keep_invalid=False, keep_raw=True)

gcode.load_file("test.gcode")

pass
