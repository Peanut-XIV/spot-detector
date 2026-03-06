from typing import Any
from dataclasses import dataclass
from pprint import pprint

from numpy.typing import NDArray
import numpy as np
import numpy.random as npr


def make_float_intervals(bits):
    maxi = 2.0**bits
    h_maxi = 2.0 ** (bits - 1)
    pos = (0, maxi - 1, f"unsigned int {str(bits)}")
    neg = (1 - maxi, 0, f"negative unsigned int {str(bits)}")
    both = (-h_maxi, h_maxi - 1, f"signed int {str(bits)}")
    return [pos, neg, both]


def generate_kwargs(arg_sequence: list[tuple[str, list[Any]]]) -> list[dict[str, Any]]:
    """
    create the cartesian product of elements of the input list of name , value-list pairs
    outputs it as a list of dict where each dict is a unique* element.
    ----
    *: as long as there are no duplicated elements inside a same value-list and
    there are no duplicated names
    """
    kwargs_set: list[dict[str, Any]] = [dict()]
    for arg_name, values in arg_sequence:
        kwargs_set = [conf | {arg_name: val} for val in values for conf in kwargs_set]
    return kwargs_set


@dataclass
class TestCase:
    type_in: np.dtype
    type_out: np.dtype
    data: NDArray
    label: str


@dataclass
class TestResult:
    failed: int = 0
    passed: int = 0
    available: int = 0
    dont_work: int = 0
    warnings: int = 0
    current_sequence: str = ""

    _red_bg: str = "\033[41m"
    _grn_bg: str = "\033[42m"
    _yel_bg: str = "\033[43m"
    _gry_bg: str = "\033[100m"
    _blk_fg: str = "\033[30m"
    _yel_fg: str = "\033[33m"
    _rst: str = "\033[0m"

    def __add__(self, other):
        return TestResult(
            failed=self.failed + other.failed,
            passed=self.passed + other.passed,
            available=self.available + other.available,
            dont_work=self.dont_work + other.dont_work,
            warnings=self.warnings + other.warnings,
            current_sequence=self.current_sequence + other.current_sequence,
        )

    def add_fail(self, warn, count=1):
        if count <= 0:
            return
        self.failed += count
        if warn:
            fg = self._yel_fg
            letter = "W"
        else:
            fg = self._blk_fg
            letter = "F"
        self.current_sequence += self._red_bg + fg + letter * count

    def add_pass(self, warn, count=1):
        if count <= 0:
            return
        self.passed += count
        if warn:
            fg = self._yel_fg
            letter = "W"
        else:
            fg = self._blk_fg
            letter = "P"
        self.current_sequence += self._grn_bg + fg + letter * count

    def add_dont_work(self, count=1):
        if count <= 0:
            return
        self.dont_work += count
        self.current_sequence += self._yel_bg + self._blk_fg + "W" * count

    @property
    def untested(self):
        return self.available - (self.failed + self.passed + self.dont_work)

    def get_sequence(self):
        return self.current_sequence + self._gry_bg + "?" * self.untested + self._rst


class Test_to_unsigned:
    def __init__(
        self,
        samp_per_case: int | None = None,
        max_fails: int = -1,
    ) -> None:
        if samp_per_case is None:
            self.test_cases = []
        else:
            self.make_test_cases(samp_per_case)
        self.max_fails = max_fails

    def make_test_cases(self, samp_per_case: int = 100):
        test_cases = []
        truth_sint = [
            (np.int8, np.uint8),
            (np.int16, np.uint16),
            (np.int32, np.uint32),
            (np.int64, np.uint64),
        ]
        for t_in, t_out in truth_sint:
            type_info = np.iinfo(t_in)
            mini = type_info.min
            maxi = type_info.max

            data = npr.randint(mini, maxi, size=samp_per_case).astype(t_in)
            data[0] = mini
            data[-1] = maxi

            label = f"integer_{str(t_in)}"

            test_cases.append(TestCase(t_in, t_out, data, label))

        truth_fp = [
            (np.float32, np.uint32),
            (np.float64, np.uint64),
        ]

        float_ranges = [
            (0, 1.0, "[0, 1)"),
            (-1.0, 0.0, "[-1, 0)"),
            (-1.0, 1.0, "[-1, 1)"),
        ]

        for b in [8, 16, 64]:
            float_ranges += make_float_intervals(b)

        for t_in, t_out in truth_fp:
            for low, high, range_name in float_ranges:
                delta = high - low
                data = (npr.random(samp_per_case) * delta - low).astype(t_in)
                label = f"{range_name} as {str(t_in)}"
                test_cases.append(TestCase(t_in, t_out, data, label))

        self.test_cases = test_cases

    def run(self, test_func, **kwargs):
        result = TestResult(
            failed=0, passed=0, dont_work=0, available=len(self.test_cases)
        )

        if len(self.test_cases) == 0:
            print("No case to test! Goodbye.")
            return result

        for tcase in self.test_cases:
            if 0 <= self.max_fails < result.failed:
                print("Too many failures, aborting...")
                return result

            if tcase.type_in != tcase.data.dtype:
                print(
                    f"Error found within *TESTER* code at case: {tcase.label}.",
                    f"Expected datatype {str(tcase.type_in)} datatype",
                    f"{str(tcase.data.dtype)} for the input. Skipping...",
                )
                result.add_dont_work()
                continue

            threw_warning = False
            out = test_func(tcase.data, **kwargs)

            if out.dtype != tcase.type_out:
                print(
                    f"Case {tcase.label} failed. Got dtype {str(out.dtype)}",
                    f"instead of {str(tcase.type_out)}.",
                )
                result.add_fail(warn=threw_warning)
            else:
                result.add_pass(warn=threw_warning)

        return result


def test_my_function(func):
    failed = False
    test = Test_to_unsigned(100)

    kwarg_spec = [
        ("domain_change", ["ReLU", "abs", "shift"]),
        ("lerp_float_first", [True, False]),
    ]

    kwarg_list = generate_kwargs(kwarg_spec)

    for kwarg in kwarg_list:
        result = test.run(func, **kwarg)
        if result.failed != 0 or result.dont_work != 0:
            failed = True
            print("using the following kwargs :")
            pprint(kwarg)
            print(result.get_sequence())
    return failed
