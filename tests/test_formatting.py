#!/usr/bin/env python3
"""
Formato de celdas de la tabla.
"""

import math

import numpy as np
import pandas as pd
import pytest

from app.models.formatting import format_cell


class TestFormatCell:
    def test_none_and_nan_become_empty(self) -> None:
        assert format_cell(None) == ''
        assert format_cell(float('nan')) == ''
        assert format_cell(pd.NA) == ''
        assert format_cell(pd.NaT) == ''

    def test_infinite_values_become_empty(self) -> None:
        assert format_cell(math.inf) == ''
        assert format_cell(-math.inf) == ''

    def test_integral_float_has_no_decimals(self) -> None:
        assert format_cell(10.0) == '10'
        assert format_cell(-3.0) == '-3'

    def test_float_uses_comma_by_default(self) -> None:
        assert format_cell(3.5) == '3,5'
        assert format_cell(0.25, decimal_separator='.') == '0.25'

    def test_other_types_use_str(self) -> None:
        assert format_cell('Madrid') == 'Madrid'
        assert format_cell(7) == '7'
        assert format_cell(True) == 'True'
        assert format_cell(pd.Timestamp('2024-05-01')) == '2024-05-01 00:00:00'

    def test_numpy_scalars(self) -> None:
        assert format_cell(np.int64(12)) == '12'
        assert format_cell(np.float64(2.5)) == '2,5'

    def test_non_scalar_value_does_not_crash(self) -> None:
        assert format_cell([1, 2, 3]) == '[1, 2, 3]'
