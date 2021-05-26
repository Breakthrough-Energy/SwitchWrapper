import os

import switch_model

from switchwrapper import const
from switchwrapper.grid_to_switch import grid_to_switch
from switchwrapper.profiles_to_switch import _check_timepoints, profiles_to_switch


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
    # Validate the input data
    _check_timepoints(timepoints)

    # Create the output folder, if it doesn't already exist
    os.makedirs(output_folder, exist_ok=True)

    grid_to_switch(grid, output_folder)
    profiles_to_switch(
        grid, profiles, timepoints, timestamp_to_timepoints, output_folder
    )
    write_version_file(output_folder)
    write_modules(os.path.join(output_folder, ".."))


def write_modules(folder):
    """Create a file containing a list of modules to be imported by Switch.

    :param str folder: the location to save the file.
    """
    with open(os.path.join(folder, "modules.txt"), "w") as f:
        for module in const.switch_modules:
            f.write(f"{module}\n")


def write_version_file(folder):
    """Create a switch_inputs_version.txt file in the inputs folder.

    :param str folder: the location to save the file.
    """
    switch_version = switch_model.__version__
    with open(os.path.join(folder, "switch_inputs_version.txt"), "w") as f:
        f.write(switch_version)
