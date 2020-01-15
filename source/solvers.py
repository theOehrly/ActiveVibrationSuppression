import numpy as np


class EulerDifferentialEquationSolver:
    """"Solver for inhomogenous differential equations of any order with nonconstant coefficients using the Euler Method.

    Can solve equations of the following form: an(t)*y{n} + ... + a2(t)*y'' +  a1(t)*y' + a0(t)*y = f(t)"""

    def __init__(self, order):
        self._order = order  # order of the differential equation

        self._iht_func = lambda *args: 0   # function for the inhomogenous term, by default just use zero always
        self._explicit_func = None   # a function calculating the differential equation in it's explicit form, i.e. returning the highest derivative

        self._Z = np.empty(0)    # Solution matrix [[*base function*: y0, y1, ...], [*first derivative*: ydt1_0, ydt1_1, ....], ....]
        self._param_t = [0, ]   # List of all values of the parameter t for which the equations are calculated

        self._t = 0  # t parameter as in y'=f(y(t), t)
        self._i = 0  # iteration index

    def set_explicit_function(self, func):
        """Set a function for calculating the value of the explicit differential equation.

        Explicit differential equation should have the following form:      y''...' = f(y, y', y'', ..., t)

        This function may include an inhomogenous term. The inhomogenous term can also be defined through a second function though,
        if a more involved method for determining it is necessary.

        The function you set may return only one value which is the value of the highest derivative for this calculation step.

        The function will be passed the following arguments when called (in order):
            - list containing current values of the base function and all derivatives: [y, y', y'', ...]
            - the value of the inhomogenous term for this calculation step (or zero if it is not set seperately)
            - the parameter t

        :param func: A function returning the value of the highest derivative
        :type func: function
        """
        self._explicit_func = func

    def set_inhomogenous_term(self, func):
        """Set a function for calculating the inhomogenous term. This is OPTIONAL

        This does not need to be set if either:
            a) inhomogenous term is included in explicit function
            b) there is no inhomogenous term

        The function may only return one value which is the value of the inhomegenous term for this calculation step.

        The function will be passed the following argument: parameter t for current calculation step

        :param func: A function returning the value of the inhomogenous term
        :type func: function
        """
        self._iht_func = func

    def set_start_values(self, values):
        """Set the starting values for the solver.

        The number of values needs to correspond to the order of the equation plus one.
        (One value for each derivative plus one for the base function.)
        The order of the values needs to be as follows: (y0, y0', y0'', ...)

        :param values: Starting values
        :type values: list or tuple
        """
        n = len(values)
        assert n == self._order + 1, "Invalid number of start values"

        # create array from starting values and shape it; force dtype float64 so array is always float even if starting values are given as int
        self._Z = np.array(values, dtype=np.float64).reshape((n, 1))

    def reset(self):
        """Resets the index, parameter t and solutions so that the solver can be rerun with different starting values, step distance, ...."""

        self._t = 0
        self._i = 0

        self._Z = np.empty(0)
        self._param_t = [0, ]

    def solve(self, t_end, step_dist):
        """Solves the equation for the given parameters and within the given range using the specified step distance.

        :param t_end: Value for which the solver should stop
        :type t_end: int or float
        :param step_dist: Distance for each calculation step
        :type step_dist: int or float
        """

        # TODO check direction against t to prevent infinite loops

        while True:
            self._Z = np.pad(self._Z, ((0, 0), (0, 1)), 'constant')  # increase teh length of each axis by one

            # calculate the new values for the base function up to the second highest derivative based on the
            # last value of the respective higher derivative
            for dtn in range(0, self._order):
                self._Z[dtn, self._i+1] = self._Z[dtn, self._i] + step_dist * self._Z[dtn+1, self._i]

            # calculate the value for the highest derivative using the explicit differential equation
            iht = self._iht_func(self._t)
            self._Z[self._order, self._i+1] = self._explicit_func(self._Z[:, self._i+1:self._i+2], iht, self._t)

            self._param_t.append(self._t)

            if self._t >= t_end:
                break

            self._i += 1
            self._t += step_dist

    def get_solution(self, dtn=0):
        """Returns the list of all parameters t and the values of the solved equation.

        By default this returns the values for the base function.

        :param dtn: optional - specifies which values should be returned: 0=y, 1=y', 2=y'', ...
        :type dtn: int
        :returns: (list of parameter t, list of function values)
        """
        return self._param_t, self._Z[dtn, :]
