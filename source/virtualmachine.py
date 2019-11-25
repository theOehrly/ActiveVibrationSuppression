import math


class Machine:
    def __init__(self, gcode, create_layers=True):
        self.gcode = gcode  # gcode class
        self.path_segments = list()
        self.acceleration_segments = list()

        self.CREATE_LAYERS = create_layers
        self.layers = list()  # list of the indexes for self.gcode items where a new layer starts

        # constant machine settings
        self.SPEED = float(200)
        self.MIN_SPEED = float(10)
        self.ACCELERATION = float(2000)
        self.JUNCTION_DEVIATION = float(0.05)

    def create_path(self):
        self.create_path_segments()
        self.calculate_path_segments()
        self.calculate_acceleration_segments()

    def create_path_segments(self):
        # reads each GLine from self.gcode and creates a path segment for every line that contains x/y movement

        # machine state variables
        nominal_speed = 0
        x = 0
        y = 0

        # variables for dectection of layer change
        z = 0
        z_old = 0
        z_changed = False

        i = 0  # count gcode elements
        i_layer_start = 0  # index of gcode element at the start of the current layer

        for gline in self.gcode:
            # if the z height changed in one of the last commands this is interpreted as
            # a layer change only if a non-travel move (G1, G2, G3) takes place at the new height
            if z_changed:
                if gline.has_word('G') and (gline.get_word('G') in (1, 2, 3)):
                    self.layers.append(i_layer_start)
                    i_layer_start = i + 1
                    z_old = z
                    z_changed = False

            # check for changes of position or speed
            if gline.has_word('F'):
                nominal_speed = gline.get_word('F') / 60  # convert from mm/min to mm/sec
            if gline.has_word('X'):
                x = gline.get_word('X')
            if gline.has_word('Y'):
                y = gline.get_word('Y')

            # check for z-height change if layers should be created
            if gline.has_word('Z') and self.CREATE_LAYERS:
                z = gline.get_word('Z')
                if z != z_old:
                    z_changed = True
                else:
                    # z didn't change or got reset to the previous value before the next non-travel move (e.g Z Hop)
                    z_changed = False

            self.path_segments.append(PathSegment(x, y, nominal_speed, gline, self))
            i += 1

    def calculate_path_segments(self):
        for i in range(1, len(self.path_segments)):
            seg = self.path_segments[i]         # current segment
            prev_seg = self.path_segments[i-1]  # previous segment

            # length of each segement --> distance from previous to current segment
            seg.x_distance = seg.x - prev_seg.x
            seg.y_distance = seg.y - prev_seg.y
            seg.distance = math.sqrt(seg.x_distance ** 2 + seg.y_distance ** 2)

            if seg.distance != 0:
                # unit vectors
                seg.x_unit_vec = seg.x_distance / seg.distance
                seg.y_unit_vec = seg.y_distance / seg.distance

                # maximum entry speed
                # is the minimum of previous nominal speed, current nominal speed and maximum junction speed

                # maximum junction speed:
                # this is taken straight from GRBL/smoothieware; calculations are slightly modified for two axes only
                # the following explanation is copied from the smoothieware source

                # // Compute maximum allowable entry speed at junction by centripetal acceleration approximation.
                # // Let a circle be tangent to both previous and current path line segments, where the junction
                # // deviation is defined as the distance from the junction to the closest edge of the circle,
                # // colinear with the circle center.The circular segment joining the two paths represents the
                # // path of centripetal acceleration.Solve for max velocity based on max acceleration about the
                # // radius of the circle, defined indirectly by junction deviation.This may be also viewed as
                # // path width or max_jerk in the previous grbl version.This approach does not actually deviate
                # // from path, but used as a robust way to compute cornering speeds, as it takes into account the
                # // nonlinearities of both the junction angle and junction velocity.

                # calculate angle between previous and current path
                # the angle is the dot product of the two vectors
                # the calculation of the dot product is simplified through the usage of the unit vectors
                junction_cos_theta = -seg.x_unit_vec * prev_seg.x_unit_vec - seg.y_unit_vec * prev_seg.y_unit_vec

                if junction_cos_theta > 0.999999:
                    # angle is 0 degrees i.e. the path makes a full turn
                    max_junction_speed = self.MIN_SPEED ** 2

                elif junction_cos_theta < -0.999999:
                    # angle is 180 degrees i.e. the junction is a straight line
                    max_junction_speed = float('inf')

                else:
                    sin_theta_d2 = math.sqrt(0.5 * (1.0 - junction_cos_theta))
                    # Trig half angle identity. Always positive.

                    prelim = math.sqrt((self.ACCELERATION * self.JUNCTION_DEVIATION * sin_theta_d2) / (1 - sin_theta_d2))
                    max_junction_speed = max(self.MIN_SPEED, prelim)

                seg.max_entry_speed = min(seg.nominal_speed, prev_seg.nominal_speed, max_junction_speed)
                seg.entry_speed = seg.max_entry_speed

            else:
                seg.max_entry_speed = 0
                seg.entry_speed = 0

        # forward pass through segments to set next entry speed based on
        # previous entry speed and acceleration
        for i in range(len(self.path_segments)-1):
            seg = self.path_segments[i]
            next_seg = self.path_segments[i+1]

            max_exit_speed = seg.entry_speed + math.sqrt(2 * self.ACCELERATION * seg.distance)
            next_seg.entry_speed = min(next_seg.max_entry_speed, max_exit_speed)

        # reverse pass through segments to check that deceleration from entry speed to
        # exit speed is possible, else reduce entry speed
        next_seg = PathSegment(0, 0, 0, None, self)
        for i in range(len(self.path_segments)-1, 0, -1):
            seg = self.path_segments[i]

            max_entry_speed = next_seg.entry_speed + math.sqrt(2 * self.ACCELERATION * seg.distance)
            if max_entry_speed < seg.entry_speed:
                seg.max_entry_speed = max_entry_speed
                seg.entry_speed = max_entry_speed

            next_seg = seg

    def calculate_acceleration_segments(self):
        # calculate the acceleration within a segment so that the duration of the segment is minimized. Therefore
        # the speed needs to be as high as possible while staying within the boundaries of entry, exit and nominal
        # speed. Acceleration is always either the nominal acceleration or zero.
        #
        #                      plateau
        #                    +--------+  <-- nominal_speed
        #                   /          \
        # entry_speed -->  +            \
        #                  |             +  <-- exit_speed == next_entry_speed
        #                  +-------------+
        #                   --> distance
        #

        segments = self.path_segments + [PathSegment(0, 0, 0, None, self)]
        # we need an all zero path segment at the end to have the last path_seg decelerate to zero

        for i in range(len(segments)-1):
            path_seg = segments[i]
            next_path_seg = segments[i+1]

            if path_seg.distance == 0:
                continue  # not a segment with movement

            acc_seg = AccelerationSegment(path_seg)
            plt_seg = None
            dcc_seg = AccelerationSegment(path_seg)

            maximum_possible_speed = math.sqrt(self.ACCELERATION * path_seg.distance + (path_seg.entry_speed ** 2 + next_path_seg.entry_speed ** 2) / 2)

            limiting_speed = min(path_seg.nominal_speed, maximum_possible_speed)
            path_seg.max_reached_speed = limiting_speed

            # calculated the acceleration and deceleration durations first
            acc_seg.duration = (limiting_speed - path_seg.entry_speed) / self.ACCELERATION
            dcc_seg.duration = (limiting_speed - next_path_seg.entry_speed) / self.ACCELERATION

            # acceleration from entry to nominal speed
            acc_seg.acceleration = self.ACCELERATION
            acc_seg.x_acceleration, acc_seg.y_acceleration = self.vectorize(path_seg, self.ACCELERATION)
            acc_seg.distance = path_seg.entry_speed * acc_seg.duration + 0.5 * self.ACCELERATION * (acc_seg.duration ** 2)
            d_acc_ratio = ((acc_seg.distance / path_seg.distance) - 1)  # minus one because path_seg.x/y is end position after segment
            acc_seg.x = path_seg.x + d_acc_ratio * path_seg.x_distance
            acc_seg.y = path_seg.y + d_acc_ratio * path_seg.y_distance

            # deceleration from nominal to exit speed / next entry speed
            dcc_seg.acceleration = -self.ACCELERATION
            dcc_seg.x_acceleration, dcc_seg.y_acceleration = self.vectorize(path_seg, -self.ACCELERATION)
            dcc_seg.distance = next_path_seg.entry_speed * dcc_seg.duration + 0.5 * self.ACCELERATION * (dcc_seg.duration ** 2)
            dcc_seg.x = path_seg.x
            dcc_seg.y = path_seg.y

            if maximum_possible_speed > path_seg.nominal_speed:
                # plateau segment
                plt_seg = AccelerationSegment(path_seg)
                plt_seg.distance = path_seg.distance - acc_seg.distance - dcc_seg.distance
                plt_seg.duration = plt_seg.distance / path_seg.nominal_speed
                # subtract deceleration distance from path segment end position to get plateau end
                d_dcc_ratio = (dcc_seg.distance / path_seg.distance)
                plt_seg.x = path_seg.x - path_seg.x_distance * d_dcc_ratio
                plt_seg.y = path_seg.y - path_seg.y_distance * d_dcc_ratio

            self.acceleration_segments.append(acc_seg)
            self.acceleration_segments.append(plt_seg) if plt_seg else None  # only append if exists
            self.acceleration_segments.append(dcc_seg)

    @staticmethod
    def vectorize(path_seg, value):
        # takes a value and creates a directional vector using the path segments unit vectors
        # the absolute value of the vector will be equal to the given value parameter
        x_value = path_seg.x_unit_vec * value
        y_value = path_seg.y_unit_vec * value
        return x_value, y_value

    def get_path_coordinates(self, layer_number=None):
        # TODO fix crash in single layer files
        # returns two lists of x and y values respectively
        # for the specified layer or the whole gcode if not specified
        if layer_number is None:
            # return all items
            start = None  # slicing a list with [None:None] returns all elements
            end = None
        elif layer_number == len(self.layers) - 1:
            # return from last layer start till end of list
            start = self.layers[layer_number]
            end = None
        else:
            # return requested layer in the middle of the list
            start = self.layers[layer_number]
            end = self.layers[layer_number+1]

        coords_x = list()
        coords_y = list()

        for seg in self.path_segments[start:end]:
            coords_x.append(seg.x)
            coords_y.append(seg.y)

        return coords_x, coords_y


class PathSegment:
    def __init__(self, x, y, nominal_speed, gline, machine):
        self.gline = gline
        self.machine = machine

        self.x = x  # position after movement [mm]
        self.y = y

        self.nominal_speed = nominal_speed  # target/maximum speed for this segment [mm/s]

        self.entry_speed = 0            # actual speed at beginning of segment [mm/s]
        self.max_entry_speed = 0        # maximum speed at beginning of segment [mm/s]
        self.max_reached_speed = 0      # maximum speed that is actually reached in this segment [mm/s]

        self.distance = 0                   # length of this segment [mm]
        self.x_distance = 0                 # x component of length  [mm]
        self.y_distance = 0                 # y component of length  [mm]

        self.x_unit_vec = 0
        self.y_unit_vec = 0


class AccelerationSegment:
    def __init__(self, pathsegment):
        self.path_seg = pathsegment

        self.x = 0  # position after movement [mm]
        self.y = 0

        self.acceleration = 0               # acceleration in this segment [mm/s^2]
        self.x_acceleration = 0
        self.y_acceleration = 0

        self.distance = 0                   # length of this segment [mm]
        self.duration = 0                  # duration of the segment [s]

    def get_accelerations(self):
        return self.acceleration, self.x_acceleration, self.y_acceleration


class ValueFromTime:
    # this class allows list-like access to the machine data using time as an index
    # the index can be a floating point number
    # ! Functionality is limited to accending values for the index/time !
    #       e.g. after accesing data at index 10 it is only possible to acces data at an index >= 10
    # ! This is just a base class and will return nothing. The _retrun_value function is overridden in child classes !

    def __init__(self, machine):
        self.seg_iter = iter(machine.acceleration_segments)
        self.current_seg = next(self.seg_iter)

        self.current_seg_start_time = 0
        self.current_seg_end_time = self.current_seg.duration
        self.current_time = 0

    def __getitem__(self, time):
        if time < self.current_time:
            raise ValueError("Current time index is smaller than previous time index. This class is unidirectional!")

        elif self.current_seg_end_time < time:
            # advance segments as far as necessary
            while self.current_seg_end_time < time:
                try:
                    self.current_seg = next(self.seg_iter)
                except StopIteration:
                    raise IndexError

                self.current_seg_start_time = self.current_seg_end_time
                self.current_seg_end_time += self.current_seg.duration

        self.current_time = time

        return self._return_value(time)

    def _return_value(self, time):
        pass


class AccelerationFromTime(ValueFromTime):
    # returns acceleration at given time
    def _return_value(self, time):
        self.current_seg.get_accelerations()


class SpeedFromTime(ValueFromTime):
    # returns speed at given time
    def _return_value(self, time):
        # plateau segment
        if not self.current_seg.acceleration:
            return self.current_seg.path_seg.max_reached_speed

        # acceleration or deceleration segment
        t_acc = time - self.current_seg_start_time  # elapsed time since beginning of this acceleration segment

        # depending on if this is a acceleration/deceleration segment the value at segment entry is either
        #   - entry speed for acceleration segments
        if self.current_seg.acceleration > 0:
            v_in = self.current_seg.path_seg.entry_speed
        #   - maximum reached speed for deceleration segments
        else:
            v_in = self.current_seg.path_seg.max_reached_speed

        # v = v0 + a*t ; acceleration is a negative value for a deceleration segment
        return v_in + self.current_seg.acceleration * t_acc
