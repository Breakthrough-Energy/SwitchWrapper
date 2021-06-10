import copy

import pandas as pd
from powersimdata.tests.mock_grid import MockGrid

from switchwrapper.switch_to_grid import add_tx_upgrades_to_grid

# Two sets of parallel lines: {{11, 15}, {12, 16}}
mock_branch_data = {
    "branch_id": [11, 12, 13, 14, 15, 16],
    "rateA": [100.0, 200, 0, 50, 0, 100],
    "x": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
    "from_bus_id": [1, 2, 3, 4, 2, 2],
    "to_bus_id": [2, 3, 4, 5, 1, 3],
}


def test_add_tx_upgrades_to_grid_one_branch():
    # Data setup
    mock_build_tx = pd.DataFrame({"year": [2030], "tx_id": ["14ac"], "capacity": [75]})
    changed = {14}
    mock_grid = MockGrid(grid_attrs={"branch": mock_branch_data})
    original_grid = copy.deepcopy(mock_grid)
    original_branch = original_grid.branch

    add_tx_upgrades_to_grid(mock_grid, mock_build_tx, 2030)
    mock_branch = mock_grid.branch
    assert original_branch.query("index not in @changed").equals(
        mock_branch.query("index not in @changed")
    )
    assert original_branch[["from_bus_id", "to_bus_id"]].equals(
        mock_branch[["from_bus_id", "to_bus_id"]]
    )
    assert (
        mock_branch.loc[changed, "rateA"] == original_branch.loc[changed, "rateA"] * 2.5
    ).all()
    assert (
        mock_branch.loc[changed, "x"] == original_branch.loc[changed, "x"] / 2.5
    ).all()


def test_add_tx_upgrades_to_one_branch_inf_capacity():
    # Data setup
    mock_build_tx = pd.DataFrame({"year": [2030], "tx_id": ["13ac"], "capacity": [125]})
    mock_grid = MockGrid(grid_attrs={"branch": mock_branch_data})
    original_grid = copy.deepcopy(mock_grid)
    original_branch = original_grid.branch

    add_tx_upgrades_to_grid(mock_grid, mock_build_tx, 2030)
    mock_branch = mock_grid.branch
    assert original_branch.equals(mock_branch)


def test_add_tx_upgrades_to_two_parallel_branches_one_upgrade():
    # Data setup
    mock_build_tx = pd.DataFrame({"year": [2030], "tx_id": ["12ac"], "capacity": [60]})
    changed = {12, 16}
    mock_grid = MockGrid(grid_attrs={"branch": mock_branch_data})
    original_grid = copy.deepcopy(mock_grid)
    original_branch = original_grid.branch

    add_tx_upgrades_to_grid(mock_grid, mock_build_tx, 2030)
    mock_branch = mock_grid.branch
    assert original_branch.query("index not in @changed").equals(
        mock_branch.query("index not in @changed")
    )
    assert original_branch[["from_bus_id", "to_bus_id"]].equals(
        mock_branch[["from_bus_id", "to_bus_id"]]
    )
    assert (
        mock_branch.loc[changed, "rateA"] == original_branch.loc[changed, "rateA"] * 1.2
    ).all()
    assert (
        mock_branch.loc[changed, "x"] == original_branch.loc[changed, "x"] / 1.2
    ).all()


def test_add_tx_upgrades_to_two_parallel_branches_two_upgrades():
    # Data setup
    mock_build_tx = pd.DataFrame(
        {"year": [2030, 2030], "tx_id": ["12ac", "16ac"], "capacity": [10, 20]}
    )
    changed = {12, 16}
    mock_grid = MockGrid(grid_attrs={"branch": mock_branch_data})
    original_grid = copy.deepcopy(mock_grid)
    original_branch = original_grid.branch

    add_tx_upgrades_to_grid(mock_grid, mock_build_tx, 2030)
    mock_branch = mock_grid.branch
    assert original_branch.query("index not in @changed").equals(
        mock_branch.query("index not in @changed")
    )
    assert original_branch[["from_bus_id", "to_bus_id"]].equals(
        mock_branch[["from_bus_id", "to_bus_id"]]
    )
    assert (
        mock_branch.loc[changed, "rateA"] == original_branch.loc[changed, "rateA"] * 1.1
    ).all()
    assert (
        mock_branch.loc[changed, "x"] == original_branch.loc[changed, "x"] / 1.1
    ).all()


def test_add_tx_upgrades_to_grid_two_parallel_branches_one_inf_capacity_two_years():
    # Data setup
    mock_build_tx = pd.DataFrame(
        {"year": [2030, 2040], "tx_id": ["11ac", "11ac"], "capacity": [100, 200]}
    )
    changed = {11}
    mock_grid = MockGrid(grid_attrs={"branch": mock_branch_data})
    original_grid = copy.deepcopy(mock_grid)
    original_branch = original_grid.branch

    # Testing 2030-only upgrades
    add_tx_upgrades_to_grid(mock_grid, mock_build_tx, 2030)
    mock_branch = mock_grid.branch
    assert original_branch.query("index not in @changed").equals(
        mock_branch.query("index not in @changed")
    )
    assert original_branch[["from_bus_id", "to_bus_id"]].equals(
        mock_branch[["from_bus_id", "to_bus_id"]]
    )
    assert (
        mock_branch.loc[changed, "rateA"] == original_branch.loc[changed, "rateA"] * 2
    ).all()
    assert (
        mock_branch.loc[changed, "x"] == original_branch.loc[changed, "x"] / 2
    ).all()

    # Testing 2040-only upgrades
    mock_grid = copy.deepcopy(original_grid)
    add_tx_upgrades_to_grid(mock_grid, mock_build_tx, 2040)
    mock_branch = mock_grid.branch
    assert original_branch.query("index not in @changed").equals(
        mock_branch.query("index not in @changed")
    )
    assert original_branch[["from_bus_id", "to_bus_id"]].equals(
        mock_branch[["from_bus_id", "to_bus_id"]]
    )
    assert (
        mock_branch.loc[changed, "rateA"] == original_branch.loc[changed, "rateA"] * 3
    ).all()
    assert (
        mock_branch.loc[changed, "x"] == original_grid.branch.loc[changed, "x"] / 3
    ).all()
