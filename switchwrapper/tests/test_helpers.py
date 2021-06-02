import pandas as pd
from powersimdata.tests.mock_grid import MockGrid

from switchwrapper.helpers import map_branch_indices_to_bus_tuple, recover_plant_indices

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
        ["g1", "g2"],
    ]
    expected_return = [
        pd.Series({1: "g1", 2: "g2", 3: "g1i", 4: "g2i"}),
        pd.Series({1: "g1", 2: "g2", 3: "g1i"}),
        pd.Series({1: "g1", 2: "g2"}),
    ]
    for a, e in zip(args, expected_return):
        assert e.equals(recover_plant_indices(a))


def test_map_branch_indices_to_bus_tuple():
    grid = MockGrid(grid_attrs={"branch": mock_branch, "dcline": mock_dcline})
    acline, dcline = map_branch_indices_to_bus_tuple(grid)
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
