from switchwrapper.grid_to_switch import grid_to_switch
from switchwrapper.profiles_to_switch import profiles_to_switch


def prepare_inputs(
    grid,
    profiles,
    timepoints,
    timestamp_to_timepoints,
    output_folder="inputs",
):
    """Prepare all grid and profile data into a format expected by Switch.

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
    grid_to_switch(grid, output_folder)
    profiles_to_switch(
        grid, profiles, timepoints, timestamp_to_timepoints, output_folder
    )
