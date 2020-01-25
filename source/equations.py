from virtualmachine import AccelerationFromTime, SpeedFromTime


class ZAxisTorsion:
    def __init__(self, machine):
        self.machine = machine

        # self.v_t = SpeedFromTime(machine)
        self.dydt2 = AccelerationFromTime(machine)

        self.y = 0   # [mm] y distance from reference zero position  TODO should not be constant
        self.z = 0   # [mm] z height above reference zero height  TODO should not be constant

        # calculation parameters
        self.pG = 70000      # [MPa] shear modulus
        self.pI_t = 15000    # [mm^4] polar moment of inertia
        self.pd_t = 210000   # [(N*mm)/s] damping coefficient

        self.pL_zmin = 10  # [mm] minimum height of the z axis
        self.pL_ymin = 25  # [mm] minimum distance between the axis of rotation (z-axis) and the center of gravity of the print head
        self.pL_xoff = 25  # [mm] distance between y-axis and center of gravity of the print head

        self.pJ_ybeam = 333       # [kg*mm^2] first moment of area of the y-beam around the z-axis (i.e. the y-axis' single point of fixation
        self.pJ_head = 250        # [kg*mm^2] first moment of area of the print head around its center of gravity
        self.pm_head = 0.25       # [kg] mass of the print head

    def _kt_z(self):
        # torsional spring constant in relation to the current height z
        return (self.pG * self.pI_t) / (self.pL_zmin + self.z)

    def _Ly_y(self):
        # distance from the center of rotation (z-axis) to the center of mass of the print head in relation to the print heads current position y
        return self.pL_ymin + self.y

    def _J_y(self):
        # first moment of inertia of the y-arm plus print head in relation to the print heads current distance Ly from the center of rotation
        return self.pJ_ybeam + self.pJ_head + self.pm_head * self._Ly_y()**2

    def _Mz_t(self, t):
        # torsional moment around the z axis in relation to the time t
        return self.pL_xoff * self.pm_head * self.dydt2[t]

    def explicit_equation(self, j, iht, t):
        # the inhomogenous term is included in this equation as self._Mz_t
        return (-self._kt_z() * j[0] - self.pd_t * j[1] + self._Mz_t(t)) / self._J_y()
