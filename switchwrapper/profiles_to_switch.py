import os

import pandas as pd

from switchwrapper.helpers import make_indices


def profiles_to_switch(
    grid,
    profiles,
    timepoints,
    timestamp_to_timepoints,
    output_folder,
):
    """Using the provided mapping of hourly timestamps to timepoints, plus hourly
    profiles, create and save CSVs which produce temporal data needed for Switch.
    Inputs are indexed by 'timestamps', while outputs are 'timeseries', each of which
    can contain multiple 'timepoints'.

    :param powersimdata.input.grid.Grid grid: grid instance.
    :param dict profiles: keys are {"demand", "hydro", "solar", "wind"}, values are the
        corresponding pandas data frames, indexed by hourly timestamp, with columns
        representing plant IDs (for hydro, solar, and wind) or zone IDs (for demand).
    :param pandas.DataFrame timepoints: data frame, indexed by timepoint_id, with
        columns: 'timestamp', 'timeseries', 'ts_period', and 'ts_duration_of_tp'.
        Each unique value in the 'timeseries' column must map to exactly one entry in
        each of 'ts_period' and 'ts_duration_of_tp', as if these columns came from
        another table in a relational database.
    :param pandas.Series timestamp_to_timepoints: timepoints (values) of each timestamp
        (index).
    :param str output_folder: the location to save outputs, created as necessary.
    """
    loads_filepath = os.path.join(output_folder, "loads.csv")
    loads = build_loads(grid.bus, profiles["demand"], timestamp_to_timepoints)
    loads.to_csv(loads_filepath)

    timepoints_filepath = os.path.join(output_folder, "timepoints.csv")
    timepoints[["timestamp", "timeseries"]].to_csv(timepoints_filepath)

    timeseries_filepath = os.path.join(output_folder, "timeseries.csv")
    timeseries = build_timeseries(timepoints, timestamp_to_timepoints)
    timeseries.to_csv(timeseries_filepath, index=False)

    variable_capacity_factors_filepath = os.path.join(
        output_folder, "variable_capacity_factors.csv"
    )
    variable_profiles = {p: profiles[p] for p in {"hydro", "solar", "wind"}}
    variable_capacity_factors = build_variable_capacity_factors(
        variable_profiles, grid.plant, timestamp_to_timepoints
    )
    variable_capacity_factors.to_csv(variable_capacity_factors_filepath, index=False)


def _check_timepoints(timepoints):
    """Validate that a one-to-many relationship exists between the entries of the
    'timeseries' column and the entries of the 'ts_period' and 'ts_duration_of_tp'
    columns.

    :param pandas.DataFrame timepoints: data frame, indexed by timepoint_id, with
        columns: 'timestamp', 'timeseries', 'ts_period', and 'ts_duration_of_tp'.
    :raises ValueError: if each unique value in the 'timeseries' column does not map to
        exactly one entry in each of 'ts_period' and 'ts_duration_of_tp', as if these
        columns came from another table in a relational database.
    """
    timeseries_group_columns = ["timeseries", "ts_period", "ts_duration_of_tp"]
    num_timeseries = len(timepoints["timeseries"].unique())
    num_timeseries_groups = len(timepoints.groupby(timeseries_group_columns))
    if num_timeseries != num_timeseries_groups:
        raise ValueError(
            "Each timeseries entry must have exactly one corresponding entry within the"
            " ts_period and ts_duration_of_tp columns."
        )


def build_loads(bus, demand, timestamp_to_timepoints):
    """Map timestamps to timepoints for demand data frame.

    :param pandas.DataFrame bus: bus data from a Grid object.
    :param pandas.DataFrame demand: demand by timestamp (index) and zone IDs (columns).
    :param pandas.Series timestamp_to_timepoints: timepoints (values) of each timestamp
        (index).
    :return: (*pandas.DataFrame*) -- data frame of demand at each bus/timepoint.
    """
    # Distribute per-zone to demand to buses
    bus_mod = bus.copy()
    bus_mod["zone_Pd"] = bus_mod.groupby("zone_id")["Pd"].transform("sum")
    bus_mod["zone_share"] = bus_mod["Pd"] / bus_mod["zone_Pd"]
    zone_bus_shares = bus_mod.pivot(columns="zone_id", values="zone_share").fillna(0)
    bus_demand = demand.dot(zone_bus_shares.T)

    # Calculate mean bus demand for each timepoint
    bus_demand["TIMEPOINT"] = timestamp_to_timepoints.to_numpy()
    timepoint_demand = bus_demand.groupby("TIMEPOINT").mean()

    # Convert from table of values to one row for each value
    timepoint_demand = timepoint_demand.melt(
        var_name="LOAD_ZONE", value_name="zone_demand_mw", ignore_index=False
    )

    # Set the index properly for Switch's expectations for the CSV
    timepoint_demand.reset_index(inplace=True)
    timepoint_demand.set_index("LOAD_ZONE", inplace=True)

    return timepoint_demand


def build_timeseries(timepoints, timestamp_to_timepoints):
    """Add extra information to ``timeseries``, based on the information in
    ``timestamp_to_timepoints`` and ``timepoints``.

    :param pandas.DataFrame timepoints: data frame, indexed by timepoint_id, with
        columns: 'timestamp', 'timeseries', 'ts_period', and 'ts_duration_of_tp'.
    :param pandas.Series timestamp_to_timepoints: timepoints (values) of each timestamp
        (index).
    :return: (*pandas.DataFrame*) -- data frame containing all timeseries information.
    """
    timeseries = timepoints.groupby("timeseries").first().drop(columns="timestamp")
    timeseries["ts_num_tps"] = timepoints.value_counts("timeseries")
    # Count the number of hours mapped to each timeseries (via the timepoints)
    hours = timestamp_to_timepoints.value_counts().groupby(timepoints.timeseries).sum()
    timeseries["ts_scale_to_period"] = hours / (
        timeseries["ts_duration_of_tp"] * timeseries["ts_num_tps"]
    )
    timeseries.index.name = "TIMESERIES"
    timeseries.reset_index(inplace=True)
    return timeseries


def build_variable_capacity_factors(gen_profiles, plant, timestamp_to_timepoints):
    """Map timestamps to timepoints for variable generation data frames.

    :param dict gen_profiles: keys include {"hydro", "solar", "wind"}, values are the
        corresponding pandas data frames, indexed by hourly timestamp, with columns
        representing plant IDs.
    :param pandas.DataFrame plant: plant data from a Grid object.
    :param pandas.Series timestamp_to_timepoints: timepoints (values) of each timestamp
        (index).
    :return: (*pandas.DataFrame*) -- data frame generation at each plant/timepoint.
    """
    # Constants
    column_names = ["GENERATION_PROJECT", "timepoint", "gen_max_capacity_factor"]

    # Get normalized profiles for all variable plants
    all_profiles = pd.concat(gen_profiles.values(), axis=1)
    capacities = plant.loc[all_profiles.columns.tolist(), "Pmax"]
    normalized_profiles = (all_profiles / capacities).fillna(0)

    # Aggregate timestamps to timepoints
    normalized_profiles["timepoint"] = timestamp_to_timepoints.to_numpy()
    variable_capacity_factors = normalized_profiles.groupby("timepoint").mean()

    # Convert from table of values to one row for each value
    variable_capacity_factors = variable_capacity_factors.melt(
        var_name="GENERATION_PROJECT",
        value_name="gen_max_capacity_factor",
        ignore_index=False,
    )

    # Re-order index & columns
    variable_capacity_factors.reset_index(inplace=True)
    variable_capacity_factors = variable_capacity_factors[column_names]

    # Copy profiles to apply to current and hypothetical plants
    original_plant_indices, hypothetical_plant_indices = make_indices(
        variable_capacity_factors["GENERATION_PROJECT"]
    )
    all_plant_indices = original_plant_indices + hypothetical_plant_indices
    variable_capacity_factors = pd.concat([variable_capacity_factors] * 2)
    variable_capacity_factors["GENERATION_PROJECT"] = all_plant_indices

    return variable_capacity_factors
