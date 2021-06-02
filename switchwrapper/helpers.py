import re

import pandas as pd

from switchwrapper import const

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


def make_plant_indices(plant_ids):
    """Make the indices for existing and hypothetical generators for input to Switch.

    :param iterable plant_ids: plant IDs.
    :return: (*tuple*) -- The first element is a list of indices for existing generators
        and the second element is a list of indices for hypothetical generators.
    """
    original_plant_indices = [f"g{p}" for p in plant_ids]
    hypothetical_plant_indices = [f"{o}i" for o in original_plant_indices]
    return original_plant_indices, hypothetical_plant_indices


def load_mapping(filename):
    """Takes a file path to a timepoint mapping csv and converts
        the given mapping into a format expected by the conversion function

    :param str filename: path to the mapping csv
    :return: (*dict*) -- a dictionary of timepoints to a list containing
        all the component time stamps
    """
    mapping_data = pd.read_csv(filename, index_col=0).groupby("timepoint")
    mapping = {str(k): v.tolist() for k, v in mapping_data.groups.items()}

    return mapping

def make_branch_indices(branch_ids, dc=False):
    """Make the indices of existing branch for input to Switch.
    :param iterable branch_ids: list of original branch ids.
    :param bool dc: branch_ids are for dclines or not, defaults to False.
    :return: (*list*) -- list of branch indices for input to Switch
    """
    return [f"{i}dc" if dc else f"{i}ac" for i in branch_ids]

def parse_timepoints(var_dict, variables, mapping_info):
    """ Takes the solution variable dictionary contained in the output pickle
    file of `switch` and un-maps the temporal reduction timepoints back into
    a timestamp-indexed dataframe.

    :param dict var_dict: a flat dictionary where the keys are a combination
        of variable names and variable parameters and the values are a
        dictionary where Value is the datapoint for that combination of variable
        name and parameters.
    :param list variables: a list of timeseries variable strings to parse out
    :param dict mapping: a dictionary of timepoints to a list containing
        all the component time stamps
    :return (*dict*): a dictionary where the keys are the variable name strings
        and the values are pandas dataframes. The index of these dataframes
        are the timestamps contained in the mapping dictionary values.
        The columns of these dataframes are a comma-separated string of the
        parameters embedded in the key of the original input dictionary with
        the timepoint removed and preserved order otherwise.
    """

    # Initialize dictionary of variables: set(column names)
    var_columns = {key: set([]) for key in variables}

    # Parse out column names, removing the timepoint
    for key in var_dict:
        # Split pickle dictionary key into variable name and parameters
        match = re.match(r"(.*?)\[(.*?)\]", key)
        var_name = match.group(1)

        # Remove timepoint, and add the rest to the column name dictionary
        if var_name in variables:
            var_params = match.group(2).split(",")
            var_params.pop(const.output_timeseries_format[var_name])
            var_columns[var_name].add(",".join(var_params))

    # Initialize final dictionary to return
    parsed_data = {}
    for key in var_columns:
        # Initialize dictionary to turn into pandas dataframe
        data_dict = {a: {} for a in var_columns[key]}
        # Remap data for only this variable
        for val in var_columns[key]:
            for timepoint in mapping:
                orig_key = key + "[" + val + "," + timepoint + "]"
                data_dict[val][timepoint] = var_dict[orig_key]["Value"]

        # Cast as pandas dataframe
        data_dict = pd.DataFrame.from_dict(data_dict)
        # Create column to explode on
        data_dict.reset_index(inplace=True)
        # Transform timepoint into list of timestamps
        data_dict["index"] = data_dict["index"].map(mapping)
        # Explode timestamp lists
        data_dict = data_dict.explode("index")
        # Update index, as sorted datetime
        data_dict.set_index("index", inplace=True)
        data_dict.index = pd.to_datetime(data_dict.index)
        data_dict.sort_index(inplace=True)

        parsed_data[key] = data_dict

    return parsed_data


def recover_plant_indices(switch_plant_ids):
    """Recover the plant indices from Switch outputs.

    :param iterable switch_plant_ids: Switch plant indices.
    :return: (*pandas.Series*) -- indices are original plant ids with new plants
        added, values are Switch plant indices.
    """
    plant_ids = dict()
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
            plant_ids[last_original_plant_id + cnt] = ind
    return pd.Series(plant_ids)


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
    )
    dcline = pd.Series(
        list(zip(grid.dcline["from_bus_id"], grid.dcline["to_bus_id"])),
        index=grid.dcline.index,
    )
    return acline, dcline
