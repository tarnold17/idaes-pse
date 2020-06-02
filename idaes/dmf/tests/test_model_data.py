##############################################################################
# Institute for the Design of Advanced Energy Systems Process Systems
# Engineering Framework (IDAES PSE Framework) Copyright (c) 2018-2020, by the
# software owners: The Regents of the University of California, through
# Lawrence Berkeley National Laboratory,  National Technology & Engineering
# Solutions of Sandia, LLC, Carnegie Mellon University, West Virginia
# University Research Corporation, et al. All rights reserved.
#
# Please see the files COPYRIGHT.txt and LICENSE.txt for full copyright and
# license information, respectively. Both files are also available online
# at the URL "https://github.com/IDAES/idaes-pse".
##############################################################################
"""
This module contains data utility function tests.
"""
import os
import warnings
import pytest
import numpy as np
import pyomo.environ as pyo

from pyomo.common.fileutils import this_file_dir

import idaes.dmf.model_data as da

_data_dir = os.path.join(this_file_dir(), "data_files")


def test_map_data():
    data1 = os.path.join(_data_dir, "data1.csv")
    data1_meta = os.path.join(_data_dir, "data1_meta.csv")
    m = pyo.ConcreteModel("Data Test Model")
    m.time = pyo.Set(initialize=[1, 2, 3])
    m.pressure = pyo.Var(m.time, doc="pressure (Pa)", initialize=101325)
    m.temperature = pyo.Var(m.time, doc="temperature (K)", initialize=300)
    m.volume = pyo.Var(m.time, doc="volume (m^3)", initialize=10)

    def retag(tag):
        return tag.replace(".junk", "")

    df, df_meta = da.read_data(
        data1, data1_meta, model=m, rename_mapper=retag, unit_system="mks"
    )

    # Check for expected columns in data and meta data
    assert "T" in df
    assert "P" in df
    assert "V" in df
    assert "T" in df_meta
    assert "P" in df_meta
    assert "V" in df_meta

    # Check that the unit strings updated after conversion
    assert df_meta["T"]["units"] == "kelvin"
    # this next unit is Pa
    assert df_meta["P"]["units"] == "kilogram / meter / second ** 2"
    assert df_meta["V"]["units"] == "meter ** 3"

    # Check that the unit conversions are okay
    assert df["T"]["1901-3-3 12:00"] == pytest.approx(300, rel=1e-4)
    assert df["P"]["1901-3-3 12:00"] == pytest.approx(200000, rel=1e-4)
    assert df["V"]["1901-3-3 12:00"] == pytest.approx(5.187286689, rel=1e-4)

    # Check the mapping of the tags to the model (the 1 key is the time indexed
    # from the model, because the reference is for a time-indexed variable)
    assert pyo.value(df_meta["T"]["reference"][1]) == pytest.approx(300, rel=1e-4)
    assert pyo.value(df_meta["P"]["reference"][1]) == pytest.approx(101325, rel=1e-4)
    assert pyo.value(df_meta["V"]["reference"][1]) == pytest.approx(10, rel=1e-4)


def test_map_data_use_ambient_pressure():
    data1 = os.path.join(_data_dir, "data1.csv")
    data1_meta = os.path.join(_data_dir, "data1_meta.csv")
    m = pyo.ConcreteModel("Data Test Model")
    m.time = pyo.Set(initialize=[1, 2, 3])
    m.pressure = pyo.Var(m.time, doc="pressure (Pa)", initialize=101325)
    m.temperature = pyo.Var(m.time, doc="temperature (K)", initialize=300)
    m.volume = pyo.Var(m.time, doc="volume (m^3)", initialize=10)

    def retag(tag):
        return tag.replace(".junk", "")

    df, df_meta = da.read_data(
        data1,
        data1_meta,
        model=m,
        rename_mapper=retag,
        unit_system="mks",
        ambient_pressure="Pamb",
        ambient_pressure_unit="psi",
    )

    # Check that the unit conversions are okay
    assert df["P"]["1901-3-3 12:00"] == pytest.approx(195886, rel=1e-4)


def test_unit_coversion():
    # spot test some unit conversions and features
    # da.unit_convert(x, frm, to=None, system=None, unit_string_map={},
    #                 ignore_units=[], gauge_pressures={}, atm=1.0):

    p_atm = np.array([1, 2, 3])
    p_psi, unit = da.unit_convert(p_atm, "atm", "psi")

    assert p_psi[0] == pytest.approx(14.7, rel=1e-2)
    assert p_psi[1] == pytest.approx(14.7 * 2, rel=1e-2)
    assert p_psi[2] == pytest.approx(14.7 * 3, rel=1e-2)
    assert unit == "pound_force_per_square_inch"

    # ppb is on the list of units to ignore, and not attempt to convert
    p, unit = da.unit_convert(p_atm, "ppb", "psi")
    assert (p[0], pytest.approx(1, rel=1e-2))
    assert unit == "ppb"

    # psig is on the list of gauge pressures.
    p, unit = da.unit_convert(p_psi, "psig", "atm")

    assert p[0] == pytest.approx(2, rel=1e-1)
    assert p[1] == pytest.approx(3, rel=1e-1)
    assert p[2] == pytest.approx(4, rel=1e-1)

    # check the general system of units conversion
    p_pa, unit = da.unit_convert(p_psi, "psi", system="mks")

    assert p_pa[0] == pytest.approx(101325, rel=1e-1)
    assert unit == "kilogram / meter / second ** 2"  # AKA Pa

    # Test for unit conversion of gauge pressue with different atmosperic
    # pressure values
    p, unit = da.unit_convert(
        p_psi, "psig", "atm", ambient_pressure=np.array([1, 1.1, 1.2])
    )

    assert p[0] == pytest.approx(2, rel=1e-1)
    assert p[1] == pytest.approx(3.1, rel=1e-1)
    assert p[2] == pytest.approx(4.2, rel=1e-1)

    # Again but make sure it works with a scalar to
    p, unit = da.unit_convert(p_psi, "psig", "atm", ambient_pressure=1.2)

    assert p[0] == pytest.approx(2.2, rel=1e-1)
    assert p[1] == pytest.approx(3.2, rel=1e-1)
    assert p[2] == pytest.approx(4.2, rel=1e-1)

    # test custom unit string mapping
    p, unit = da.unit_convert(
        p_psi, "MYPRESSURE", "atm", unit_string_map={"MYPRESSURE": "psi"}
    )

    assert p[0] == pytest.approx(1, rel=1e-1)
    assert p[1] == pytest.approx(2, rel=1e-1)
    assert p[2] == pytest.approx(3, rel=1e-1)

    # Test that a unit that doesn't exist remains unchanged
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        p, unit = da.unit_convert(p_psi, "MYPRESSURE", "atm")
        assert len(w) == 1
        assert issubclass(w[-1].category, UserWarning)
        assert (
            str(w[-1].message) == "In unit conversion, from unit 'MYPRESSURE'"
            " is not defined. No conversion."
        )

    assert p_psi[0] == pytest.approx(14.7, rel=1e-1)
    assert unit == "MYPRESSURE"
