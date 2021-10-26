import pandas as pd
from powersimdata.tests.mock_grid import MockGrid

from switchwrapper.helpers import (
    branch_indices_to_bus_tuple,
    recover_branch_indices,
    recover_plant_indices,
)

mock_branch = {
    "branch_id": [101, 102, 103],
    "from_bus_id": [1, 2, 3],
    "to_bus_id": [2, 3, 1],
}

mock_dcline = {
    "dcline_id": [0],
    "from_bus_id": [1],
    "to_bus_id": [2],
}


def test_recover_plant_indices():
    args = [
        ["g1", "g2", "g1i", "g2i"],
        ["g1", "g2", "g1i"],
        ["g1", "g2", "g1i", "s2i"],
        ["g1", "g2"],
        ["g1", "g2", "s1i"],
    ]
    expected_return = [
        (pd.Series({1: "g1", 2: "g2", 3: "g1i", 4: "g2i"}), pd.Series(dtype=str)),
        (pd.Series({1: "g1", 2: "g2", 3: "g1i"}), pd.Series(dtype=str)),
        (pd.Series({1: "g1", 2: "g2", 3: "g1i"}), pd.Series({4: "s2i"})),
        (pd.Series({1: "g1", 2: "g2"}), pd.Series(dtype=str)),
        (pd.Series({1: "g1", 2: "g2"}), pd.Series({3: "s1i"})),
    ]
    for a, e in zip(args, expected_return):
        assert all([s.equals(e[i]) for i, s in enumerate(recover_plant_indices(a))])


def test_recover_branch_indices():
    args = [["1ac", "2ac", "0dc"], ["1ac", "2ac"]]
    expected_return = [
        (pd.Series({1: "1ac", 2: "2ac"}), pd.Series({0: "0dc"})),
        (pd.Series({1: "1ac", 2: "2ac"}), pd.Series(dtype=str)),
    ]
    for a, e in zip(args, expected_return):
        assert all([s.equals(e[i]) for i, s in enumerate(recover_branch_indices(a))])


def test_branch_indices_to_bus_tuple():
    grid = MockGrid(grid_attrs={"branch": mock_branch, "dcline": mock_dcline})
    acline, dcline = branch_indices_to_bus_tuple(grid)
    expected_acline = pd.Series(
        {
            101: (1, 2),
            102: (2, 3),
            103: (3, 1),
        }
    )
    expected_dcline = pd.Series({0: (1, 2)})
    assert expected_acline.equals(acline)
    assert expected_dcline.equals(dcline)
