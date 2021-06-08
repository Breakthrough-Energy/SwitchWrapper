import copy

import pandas as pd

from switchwrapper.helpers import (
    match_variables,
    recover_branch_indices,
    recover_plant_indices,
)


def construct_grids_from_switch_results(grid, results):
    """Using the original Grid and Switch expansion results, construct expanded Grid(s).

    :param powersimdata.input.grid.Grid grid: Grid instance.
    :param pyomo.opt.results.results_.SolverResults results: results from Switch.
    :return: (*dict*) -- keys are integers representing the expansion year, values are
        Grid objects.
    """
    # Extract the upgrade information from the Switch results
    build_gen, build_tx = extract_build_decisions(results)
    # Add this information to the existing grid to create new grids
    all_grids = create_upgraded_grids(grid, build_gen, build_tx)

    return all_grids


def create_upgraded_grids(grid, build_gen, build_tx):
    """Add upgrades to existing Grid.

    :param powersimdata.input.grid.Grid grid: Grid instance.
    :param pandas.DataFrame build_gen: generation expansion decisions.
    :param pandas.DataFrame build_tx: transmission expansion decisions.
    :return: (*dict*) -- keys are integers representing the expansion year, values are
        Grid objects.
    """
    # Build a Grid for each investment year
    all_grids = {}
    for year in build_tx.year.unique():
        # Start with a copy of the original grid (except data_loc, no longer applies)
        output_grid = copy.deepcopy(grid)
        output_grid.data_loc = None
        # Then make additions based on each year's upgrade results
        add_tx_upgrades_to_grid(output_grid, build_tx, year)
        add_gen_upgrades_to_grid(output_grid, build_gen, year)
        # Finally, save
        all_grids[year] = output_grid

    return all_grids


def add_tx_upgrades_to_grid(grid, build_tx, year):
    """Add transmission upgrades to existing Grid. Note: modifies the grid inplace.

    :param powersimdata.input.grid.Grid grid: Grid instance.
    :param pandas.DataFrame build_tx: transmission expansion decisions.
    :param int year: upgrades year to apply upgrades from.
    """
    ac_branch_ids, dc_branch_ids = recover_branch_indices(build_tx["tx_id"])
    ac_id_unmapping = pd.Series(ac_branch_ids.index, index=ac_branch_ids)
    # Filter to upgrades in each year, and separate transmission by AC or DC
    ac_upgrades = build_tx.query(
        "year == @year and tx_id in @ac_branch_ids and capacity > 0"
    )
    dc_upgrades = build_tx.query(
        "year == @year and tx_id in @dc_branch_ids and capacity > 0"
    )
    # Apply AC upgrades (no new branches, scale up rateA and scale down impedance)
    original_index_upgrades = pd.Series(
        ac_upgrades.capacity.to_numpy(),
        index=ac_upgrades.tx_id.map(ac_id_unmapping),
    )
    ac_upgrade_ratios = original_index_upgrades / grid.branch.rateA
    ac_upgrade_ratios.fillna(1, inplace=True)
    grid.branch.rateA.update(grid.branch.rateA * ac_upgrade_ratios)
    impedance_updates = grid.branch.x / ac_upgrade_ratios
    grid.branch.x.update(impedance_updates)
    # Apply DC upgrades (no new lines, add to Pmax and subtract from Pmin)
    dc_upgrades = dc_upgrades.reindex(grid.dcline.index).fillna(0)
    grid.dcline.Pmax += dc_upgrades.capacity
    grid.dcline.Pmin -= dc_upgrades.capacity


def add_gen_upgrades_to_grid(grid, build_gen, year):
    """Add generation upgrades to existing Grid. Note: modifies the grid inplace.

    :param powersimdata.input.grid.Grid grid: Grid instance.
    :param pandas.DataFrame build_gen: generation expansion decisions.
    :param int year: upgrades year to apply upgrades from.
    """
    # Extract indices
    plant_ids, _ = recover_plant_indices(build_gen["gen_id"])
    num_original_plants = len(grid.plant)
    new_plant_ids = plant_ids.iloc[num_original_plants:]
    new_plant_id_unmapping = pd.Series(new_plant_ids.index, index=new_plant_ids)
    # Copy data frames from plant inputs
    new_plants = grid.plant.copy().reset_index()
    new_gencost = grid.gencost["before"].copy().reset_index()
    # Update new generator data frames based on upgrade decisions
    new_capacity = build_gen.query("year == @year").capacity.reset_index(drop=True)
    pmin_ratio = (grid.plant.Pmin / grid.plant.Pmax).reset_index(drop=True)
    capacity_ratio = new_capacity / grid.plant.Pmax.reset_index(drop=True)
    # Replace all inf or NA values with 0
    with pd.option_context("mode.use_inf_as_na", True):
        pmin_ratio.fillna(0, inplace=True)
        capacity_ratio.fillna(0, inplace=True)
        c2_replacements = (new_gencost["c2"] / capacity_ratio).fillna(new_gencost["c2"])
    new_plants["Pmin"] = new_capacity * pmin_ratio
    new_plants["Pmax"] = new_capacity
    new_plants["plant_id"] = new_plant_id_unmapping.tolist()
    # Then calculate the new gencost
    new_gencost["c0"] *= capacity_ratio
    new_gencost["c2"].update(c2_replacements)
    new_gencost["plant_id"] = new_plant_id_unmapping.tolist()
    # Drop all plants which are not upgraded
    new_plants = new_plants.query("Pmax > 0")
    new_plants.set_index("plant_id", inplace=True)
    grid.plant = grid.plant.append(new_plants)
    # Append only these new plants to gencost
    new_gencost.set_index("plant_id", inplace=True)
    grid.gencost["before"] = grid.gencost["before"].append(
        new_gencost.loc[new_plants.index]
    )
    grid.gencost["after"] = grid.gencost["before"]


def extract_build_decisions(results):
    """Parse the results of the decision variables within Switch results.

    :param pyomo.opt.results.results_.SolverResults results: results from Switch.
    :return: (*tuple*) --
        pandas.DataFrame representing the generator build decisions. Columns are:
            'year', 'gen_id' (Switch indexing), and 'capacity'. There is no meaningful
            index.
        pandas.DataFrame representing the transmission build decisions. Columns are:
            'year', 'tx_id' (Switch indexing), and 'capacity'. There is no meaningful
            index.
    """
    gen_pattern = r"BuildGen\[(?P<gen_id>[a-z0-9]+),(?P<year>[0-9]+)\]"
    tx_pattern = r"BuildTx\[(?P<tx_id>[a-z0-9]+),(?P<year>[0-9]+)\]"

    variables = results.solution._list[0]["Variable"]
    build_gen = match_variables(variables, gen_pattern, ["year", "gen_id"])
    build_gen = build_gen.astype({"year": int})
    build_tx = match_variables(variables, tx_pattern, ["year", "tx_id"])
    build_tx = build_tx.astype({"year": int})

    return build_gen, build_tx
