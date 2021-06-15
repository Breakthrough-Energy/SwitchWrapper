import re

import pandas as pd


def match_variables(variables, pattern, columns):
    """Search through dictionary of variables, extracting data frame of values.

    :param dict variables: dictionary, keys are strings, values are dictionaries
        with key "Value" and float value.
    :param str pattern: regex pattern to use to search for matching variables.
    :param iterable columns: names to extract from match to data frame columns.
    :return: (*pandas.DataFrame*) -- data frame of matching variables.
    """
    prog = re.compile(pattern)
    df = pd.DataFrame(
        [
            {
                **{name: m.group(name) for name in columns},
                "capacity": variables[m.group(0)]["Value"],
            }
            for m in [
                prog.match(v) for v in variables.keys() if prog.match(v) is not None
            ]
        ]
    )
    return df


def make_plant_indices(plant_ids, storage_candidates=None):
    """Make the indices for existing and hypothetical generators for input to Switch.

    :param iterable plant_ids: plant IDs.
    :param set storage_candidates: buses at which to enable storage expansion.
    :return: (*dict*) -- keys are {'existing', 'expansion', 'storage'}, values are
        lists of indices (str) for each sub-type.
    """
    indices = {"existing": [f"g{p}" for p in plant_ids]}
    indices["expansion"] = [f"{e}i" for e in indices["existing"]]
    if storage_candidates is None:
        indices["storage"] = []
    else:
        indices["storage"] = [f"s{b}i" for b in sorted(storage_candidates)]
    return indices


def load_timestamps_to_timepoints(filename):
    """Read timestamps_to_timepoints csv file from the given file path using pandas.

    :param str filename: path to the timestamps_to_timepoints csv.
    :return: (*pandas.DataFrame*) -- a dataframe with of timepoints to a list containing
        all the component timestamps.
    """
    timestamps_to_timepoints = pd.read_csv(filename, index_col=0)

    return timestamps_to_timepoints


def make_branch_indices(branch_ids, dc=False):
    """Make the indices of existing branch for input to Switch.

    :param iterable branch_ids: list of original branch ids.
    :param bool dc: branch_ids are for dclines or not, defaults to False.
    :return: (*list*) -- list of branch indices for input to Switch
    """
    return [f"{i}dc" if dc else f"{i}ac" for i in branch_ids]


def parse_timepoints(var_dict, variables, timestamps_to_timepoints):
    """Takes the solution variable dictionary contained in the output pickle
    file of `switch` and un-maps the temporal reduction timepoints back into
    a timestamp-indexed dataframe.

    :param dict var_dict: a flat dictionary where the keys are a string
        containing both variable names and variable parameters and the values
        are a dictionary where Value is the datapoint for that combination of
        variable name and parameters.
    :param list variables: a list of timeseries variable strings to parse out
    :param pandas.DataFrame timestamps_to_timepoints: data frame indexed by
        timestamps with a column of timepoints for each timestamp.
    :return (*dict*): a dictionary where the keys are the variable name strings
        and the values are pandas dataframes. The index of these dataframes
        are the timestamps contained in the timestamps_to_timepoints data frame.
        The columns of these dataframes are a comma-separated string of the
        parameters embedded in the key of the original input dictionary with
        the timepoint removed and preserved order otherwise. If no variables
        are found in the input dictionary, the value will be None.

    """
    # Initialize final dictionary to return
    parsed_data = {}

    for key in variables:
        # Parse out a dataframe for each variable
        df = match_variables(
            var_dict,
            key + r"\[(?P<params>.*),(?P<timepoint>.*?)\]",
            ["params", "timepoint"],
        )

        # If no such variable was found, set dataframe to None
        if df.empty:
            parsed_data[key] = None
            continue

        # Unstack such that the timepoints are the indices
        df = df.set_index(["timepoint", "params"]).unstack()
        # Cast timepoints as ints to match timestamps_to_timepoints
        df.index = df.index.astype(int)
        # Expand rows to all timestamps
        df = df.loc[timestamps_to_timepoints["timepoint"]].set_index(
            timestamps_to_timepoints.index
        )

        parsed_data[key] = df

    return parsed_data


def recover_plant_indices(switch_plant_ids):
    """Recover the plant indices from Switch outputs.

    :param iterable switch_plant_ids: Switch plant indices.
    :return: (*tuple*) -- a pair of pandas.Series objects for plant and storage
        respectively. The plant series is indexed by original plant IDs (with new plants
        added), values are Switch plant indices. The storage series is indexed by
        the new plant IDs for storage, values are Switch plant indices.
    """
    plant_ids, storage_ids = dict(), dict()
    for ind in switch_plant_ids[::-1]:
        if ind[-1] != "i":
            last_original_plant_id = int(ind[1:])
            break
    cnt = 0
    for ind in switch_plant_ids:
        if ind[-1] != "i":
            plant_ids[int(ind[1:])] = ind
        else:
            cnt += 1
            if ind[0] == "s":
                storage_ids[last_original_plant_id + cnt] = ind
            else:
                plant_ids[last_original_plant_id + cnt] = ind
    return pd.Series(plant_ids), pd.Series(storage_ids, dtype=str)


def recover_branch_indices(switch_branch_ids):
    """Recover the branch indices from Switch outputs.

    :param iterable switch_branch_ids: Switch branch indices.
    :return: (*tuple*) -- a pair of pandas.Series objects for acline and dcline
        respectively, which are indexed by original branch ids and values are
        corresponding Switch branch indices.
    """
    ac_branch_ids = dict()
    dc_branch_ids = dict()
    for ind in switch_branch_ids:
        if ind[-2:] == "ac":
            ac_branch_ids[int(ind[:-2])] = ind
        else:
            dc_branch_ids[int(ind[:-2])] = ind
    return pd.Series(ac_branch_ids), pd.Series(dc_branch_ids, dtype=str)


def branch_indices_to_bus_tuple(grid):
    """Map the branch indices to from/to bus tuples based on a grid instance.

    :param powersimdata.input.grid.Grid grid: grid instance.
    :return: (*tuple*) -- a pair of pandas.Series objects for acline and dcline
        respectively, which are indexed by original branch ids and values are
        corresponding tuples (from_bus_id, to_bus_id).
    """
    acline = pd.Series(
        list(zip(grid.branch["from_bus_id"], grid.branch["to_bus_id"])),
        index=grid.branch.index,
        dtype="float64",
    )
    dcline = pd.Series(
        list(zip(grid.dcline["from_bus_id"], grid.dcline["to_bus_id"])),
        index=grid.dcline.index,
        dtype="float64",
    )
    return acline, dcline
