import os

import pandas as pd


def profiles_to_switch(
    grid,
    profiles,
    timepoints,
    timeseries,
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
        columns 'timestamp' and 'timeseries'.
    :param pandas.DataFrame timeseries: data frame, indexed by timeseries, with columns
        'ts_period' and 'ts_duration_of_tp'.
    :param pandas.Series timestamp_to_timepoints: timepoints (values) of each timestamp
        (index).
    :param str output_folder: the location to save outputs, created as necessary.
    """
    # Create the output folder, if it doesn't already exist
    os.makedirs(output_folder, exist_ok=True)

    loads_filepath = os.path.join(output_folder, "loads.csv")
    loads = build_loads(grid.bus, profiles["demand"], timestamp_to_timepoints)
    loads.to_csv(loads_filepath)

    timeseries_filepath = os.path.join(output_folder, "timeseries.csv")
    timeseries_df = build_timeseries(timeseries, timestamp_to_timepoints, timepoints)
    timeseries_df.to_csv(timeseries_filepath, index=False)

    variable_capacity_factors_filepath = os.path.join(
        output_folder, "variable_capacity_factors.csv"
    )
    variable_capacity_factors = build_variable_capacity_factors(
        profiles, grid.plant, timestamp_to_timepoints
    )
    variable_capacity_factors.to_csv(variable_capacity_factors_filepath, index=False)


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

    return timepoint_demand


def build_timeseries(timeseries, timestamp_to_timepoints, timepoints):
    """Add extra information to ``timeseries``, based on the information in
    ``timestamp_to_timepoints`` and ``timepoints``.

    :param pandas.DataFrame timeseries: data frame, indexed by timeseries, with columns
        'ts_period' and 'ts_duration_of_tp'.
    :param pandas.Series timestamp_to_timepoints: timepoints (values) of each timestamp
        (index).
    :param pandas.DataFrame timepoints: data frame, indexed by timepoint_id, with
        columns 'timestamp' and 'timeseries'.
    :return: (*pandas.DataFrame*) -- data frame containing all timeseries information.
    """
    timeseries["ts_num_tps"] = timepoints.value_counts("timeseries")
    # Count the number of hours mapped to each timeseries (via the timepoints)
    hours = timestamp_to_timepoints.value_counts().groupby(timepoints.timeseries).sum()
    timeseries["ts_scale_to_period"] = hours / (
        timeseries["ts_duration_of_tp"] * timeseries["ts_num_tps"]
    )
    timeseries.index.name == "TIMESERIES"
    timeseries.reset_index(inplace=True)
    return timeseries


def build_variable_capacity_factors(profiles, plant, timestamp_to_timepoints):
    """Map timestamps to timepoints for variable generation data frames.

    :param dict profiles: keys include {"hydro", "solar", "wind"}, values are the
        corresponding pandas data frames, indexed by hourly timestamp, with columns
        representing plant IDs.
    :param pandas.DataFrame plant: plant data from a Grid object.
    :param pandas.Series timestamp_to_timepoints: timepoints (values) of each timestamp
        (index).
    :return: (*pandas.DataFrame*) -- data frame generation at each plant/timepoint.
    """
    return pd.DataFrame()
