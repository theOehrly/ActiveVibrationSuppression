import math


class Machine:
    def __init__(self, gcode):
        self.gcode = gcode
        self.path_segments = list()
        self.acceleration_segments = list()

        self.x = float(0)
        self.y = float(0)

        self.vx = float(0)
        self.vy = float(0)

        self.SPEED = float(200)
        self.MIN_SPEED = float(10)
        self.ACCELERATION = float(2000)
        self.JUNCTION_DEVIATION = float(0.05)

    def create_path(self):
        self.path_segments = list()

        self.create_path_segments()
        self.calculate_path_segments()
        self.calculate_acceleration_segments()

    def create_path_segments(self):
        nominal_speed = 0
        x = 0
        y = 0

        for gline in self.gcode:
            if gline.has_word('F'):
                nominal_speed = gline.get_word('F') / 60  # convert from mm/min to mm/sec
            if gline.has_word('X'):
                x = gline.get_word('X')
            if gline.has_word('Y'):
                y = gline.get_word('Y')

            self.path_segments.append(PathSegment(x, y, nominal_speed, gline))

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
                seg.x_unit_vector = seg.x_distance / seg.distance
                seg.y_unit_vector = seg.y_distance / seg.distance

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
        for i in range(len(self.path_segments)-1, 0, -1):
            seg = self.path_segments[i]

            max_entry_speed = seg.exit_speed + math.sqrt(2 * self.ACCELERATION * seg.distance)
            if max_entry_speed < seg.entry_speed:
                seg.max_entry_speed = max_entry_speed
                seg.entry_speed = max_entry_speed

    def calculate_acceleration_segments(self):
        # calculate the acceleration within a segment so that the duration of the segment is minimized. Therefore
        # the speed needs to be as high as possible while staying within the boundaries of entry, exit and nominal
        # speed. Acceleration is always either the nominal acceleration or zero.
        #
        #                      plateau
        #                    +--------+  <-- nominal_speed
        #                   /          \
        # entry_speed -->  +            \
        #                  |             +  <-- exit_speed
        #                  +-------------+
        #                   --> distance
        #

        for path_seg in self.path_segments:
            if path_seg.distance == 0:
                continue  # not a segment with movement

            acc_seg = AccelerationSegment(path_seg)
            plt_seg = None
            dcc_seg = AccelerationSegment(path_seg)

            maximum_possible_speed = math.sqrt(self.ACCELERATION * path_seg.distance + (path_seg.entry_speed ** 2 + path_seg.exit_speed ** 2) / 2)

            limiting_speed = min(path_seg.nominal_speed, maximum_possible_speed)

            # calculated the acceleration and deceleration durations first
            acc_seg.duration = (limiting_speed - path_seg.entry_speed) / self.ACCELERATION
            dcc_seg.duration = (limiting_speed - path_seg.exit_speed) / self.ACCELERATION

            # acceleration from entry to nominal speed
            acc_seg.acceleration = self.ACCELERATION
            acc_seg.x_acceleration, acc_seg.y_acceleration = self.vectorize(path_seg, self.ACCELERATION)
            acc_seg.distance = path_seg.entry_speed * acc_seg.duration + 0.5 * self.ACCELERATION * (acc_seg.duration ** 2)
            d_acc_ratio = ((acc_seg.distance / path_seg.distance) - 1)  # minus one because path_seg.x/y is end position after segment
            acc_seg.x = path_seg.x + d_acc_ratio * path_seg.x_distance
            acc_seg.y = path_seg.y + d_acc_ratio * path_seg.y_distance

            # deceleration from nominal to exit speed
            dcc_seg.acceleration = -self.ACCELERATION
            dcc_seg.x_acceleration, dcc_seg.y_acceleration = self.vectorize(path_seg, -self.ACCELERATION)
            dcc_seg.distance = path_seg.exit_speed * dcc_seg.duration + 0.5 * self.ACCELERATION * (dcc_seg.duration ** 2)
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
        x_value = path_seg.x_unit_vec * value
        y_value = path_seg.y_unit_vec * value
        return x_value, y_value


class PathSegment:
    def __init__(self, x, y, nominal_speed, gline):
        self.gline = gline

        self.x = x  # position after movement [mm]
        self.y = y

        self.nominal_speed = nominal_speed  # target/maximum speed for this segment [mm/s]

        self.entry_speed = 0            # actual speed at beginning of segment [mm/s]
        self.max_entry_speed = 0        # maximum speed at beginning of segment [mm/s]
        self.exit_speed = 0             # speed when exiting the segment [mm/s]

        self.distance = 0                   # length of this segment [mm]
        self.x_distance = 0                 # x component of length  [mm]
        self.y_distance = 0                 # y component of length  [mm]

        self.x_unit_vec = 0
        self.y_unit_vec = 0


class AccelerationSegment:
    def __init__(self, pathsegment):
        self.pathsegment = pathsegment

        self.x = 0  # position after movement [mm]
        self.y = 0

        self.acceleration = 0               # acceleration in this segment [mm/s^2]
        self.x_acceleration = 0
        self.y_acceleration = 0

        self.distance = 0                   # length of this segment [mm]
        self.duration = 0                  # duration of the segment [s]

    def get_accelerations(self):
        return self.acceleration, self.x_acceleration, self.y_acceleration


class AccelerationFromTime:
    def __init__(self, machine):
        self.seg_iter = iter(machine.acceleration_segments)
        self.current_seg = next(self.seg_iter)

        self.current_seg_end_time = self.current_seg.duration
        self.time = 0

    def __getitem__(self, t):
        if t < self.time:
            raise ValueError("Current time index is smaller than previous time index. This class is unidirectional!")

        elif self.current_seg_end_time < t:
            # advance segments as far as necessary
            while self.current_seg_end_time < t:
                self.current_seg = next(self.seg_iter)
                self.current_seg_end_time += self.current_seg.duration

        self.time += t

        return self.current_seg.get_accelerations()
