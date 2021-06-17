import os
import pickle

import switch_model

from switchwrapper import const
from switchwrapper.grid_to_switch import grid_to_switch
from switchwrapper.profiles_to_switch import _check_timepoints, profiles_to_switch


def prepare_inputs(
    grid,
    profiles,
    timepoints,
    timestamp_to_timepoints,
    switch_files_root=None,
    storage_candidate_buses=None,
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
    :param str switch_files_root: the location to save all Switch files.
    :param set storage_candidate_buses: buses at which to enable storage expansion.
    """
    # Validate the input data
    _check_timepoints(timepoints)

    # Create the 'inputs' folder, if it doesn't already exist
    switch_files_root = os.getgwd() if switch_files_root is None else switch_files_root
    # Folder for Switch inputs
    inputs_folder = os.path.join(switch_files_root, "inputs")
    os.makedirs(inputs_folder, exist_ok=True)
    # Folder for storing SwitchWrapper inputs, for use in extraction of results
    switchwrapper_inputs_folder = os.path.join(
        switch_files_root, "switchwrapper_inputs"
    )
    os.makedirs(switchwrapper_inputs_folder, exist_ok=True)

    grid_to_switch(grid, inputs_folder, storage_candidate_buses)
    profiles_to_switch(
        grid, profiles, timepoints, timestamp_to_timepoints, inputs_folder
    )
    write_version_file(inputs_folder)
    write_modules(switch_files_root)

    # Save input files required for output processing
    # Input Grid object
    with open(os.path.join(switchwrapper_inputs_folder, "grid.pkl"), "wb") as f:
        pickle.dump(grid, f)
    # Timepoints information
    timepoints.to_csv(os.path.join(switchwrapper_inputs_folder, "timepoints.csv"))
    # Timestamps to timepoints mapping information
    timestamp_to_timepoints.to_csv(
        os.path.join(switchwrapper_inputs_folder, "timestamp_to_timepoints.csv")
    )
    # Storage candidate buses
    if storage_candidate_buses is not None:
        bus_list_path = os.path.join(
            switchwrapper_inputs_folder, "storage_candidate_buses.txt"
        )
        with open(bus_list_path, "w") as f:
            for bus in sorted(storage_candidate_buses):
                f.write(f"{bus}\n")


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
