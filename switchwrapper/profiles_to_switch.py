import os

import pandas as pd


def profiles_to_switch(
    grid,
    profiles,
    timepoints,
    timeseries_to_duration,
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
    :param pandas.Series timeseries_to_duration: durations (values) of each timeseries
        (index).
    :param pandas.Series timestamp_to_timepoints: timepoints (values) of each timestamp
        (index).
    :param str output_folder: the location to save outputs, created as necessary.
    """
    # Create the output folder, if it doesn't already exist
    os.makedirs(output_folder, exist_ok=True)

    loads_filepath = os.path.join(output_folder, "loads.csv")
    loads = build_loads(grid.bus, profiles["demand"], timestamp_to_timepoints)
    loads.to_csv(loads_filepath, index=False)

    timeseries_filepath = os.path.join(output_folder, "timeseries.csv")
    timeseries = build_timeseries(
        timeseries_to_duration, timestamp_to_timepoints, timepoints
    )
    timeseries.to_csv(timeseries_filepath, index=False)

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
    return pd.DataFrame()


def build_timeseries(timeseries_to_duration, timestamp_to_timepoints, timepoints):
    """Add extra information to ``timeseries_to_duration``, based on the information in
    ``timestamp_to_timepoints`` and ``timepoints``.

    :param pandas.Series timeseries_to_duration: durations (values) of each timeseries
        (index).
    :param pandas.Series timestamp_to_timepoints: timepoints (values) of each timestamp
        (index).
    :param pandas.DataFrame timepoints: data frame, indexed by timepoint_id, with
        columns 'timestamp' and 'timeseries'.
    :return: (*pandas.DataFrame*) -- data frame containing all timeseries information.
    """
    return pd.DataFrame()


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