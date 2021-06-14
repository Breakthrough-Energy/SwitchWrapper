import pandas as pd

from switchwrapper import const  # noqa: F401
from switchwrapper.helpers import recover_plant_indices


def reconstruct_input_profiles(
    grid,
    loads,
    variable_capacity_factors,
    timestamps_to_timepoints,
):
    """Given the temporally-reduced profiles that are given to Switch and the reduction
    mapping, reconstruct full-dimension profiles for the Grid that is constructed from
    Switch outputs.

    :param powersimdata.input.grid.Grid grid: grid object after expansion.
    :param pandas.DataFrame loads: demand data frame. columns are:
        'LOAD_ZONE', 'TIMEPOINT', and 'zone_demand_mw' (no meaningful index).
    :param pandas.DataFrame variable_capacity_factors: hydro/solar/wind data frame.
        columns are: 'GENERATION_PROJECT', 'timepoint', and 'gen_max_capacity_factor'
        (no meaningful index).
    :param pandas.Series timestamps_to_timepoints: index is full-dimension timestamps,
        values are the timepoint that each timestamp was mapped to (int).
    :return: (*dict*) -- keys are: {'demand', 'hydro', 'solar', 'wind'}, values are
        pandas DataFrames, indexed as in ``timestamps_to_timepoints``, with integer
        columns representing plant IDs (for hydro, solar, wind) or zone IDs
        (for demand). The data frame values are floats, and the units are MW.
    """
    profiles = {}  # Container for all resulting profiles

    # First, demand
    loads = loads.assign(zone_id=loads.LOAD_ZONE.map(grid.bus.zone_id))
    loads.drop("LOAD_ZONE", axis=1, inplace=True)
    zone_loads = loads.groupby(["TIMEPOINT", "zone_id"]).sum().squeeze().unstack()
    full_time_zone_loads = zone_loads.loc[timestamps_to_timepoints.tolist()]
    full_time_zone_loads.index = timestamps_to_timepoints.index
    profiles["demand"] = full_time_zone_loads

    # Then profiles
    switch_plant_ids = variable_capacity_factors.GENERATION_PROJECT.unique()
    plant_ids = recover_plant_indices(switch_plant_ids)[0]
    id_unmapping = pd.Series(plant_ids.index, index=plant_ids)
    # Get original IDs
    original_id_values = variable_capacity_factors.assign(
        plant_id=variable_capacity_factors.GENERATION_PROJECT.map(id_unmapping)
    ).drop("GENERATION_PROJECT", axis=1)
    # Un-melt data frame
    reshaped_values = (
        original_id_values.set_index(["timepoint", "plant_id"]).squeeze().unstack()
    )
    # Expand to full time dimension
    full_time_profiles = reshaped_values.loc[timestamps_to_timepoints.tolist()]
    full_time_profiles.index = timestamps_to_timepoints.index
    # Un-normalize
    built_variable_plants = grid.plant.query("type in @const.variable_types").index
    unnormalized_profiles = full_time_profiles[built_variable_plants].multiply(
        grid.plant.Pmax.loc[built_variable_plants]
    )
    resource_types = {
        "hydro": {"hydro"},
        "solar": {"solar"},
        "wind": {"wind", "wind_offshore"},
    }
    for r in ["hydro", "solar", "wind"]:
        matching = resource_types[r]  # noqa: F841
        profiles[r] = unnormalized_profiles[grid.plant.query("type in @matching").index]

    return profiles
