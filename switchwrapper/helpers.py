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
    with open(filename, 'r') as f:
        mapping = {}
        index = []
        # read headers
        
        f.readline()
        for line in f:
            utc, timepoint = line.rstrip().split(',')

            if timepoint in mapping:
                mapping[timepoint].append(utc)
            else:
                mapping[timepoint] = [utc]

            index.append(utc)  
    
    return mapping, index

def make_branch_indices(branch_ids, dc=False):
    """Make the indices of existing branch for input to Switch.
    :param iterable branch_ids: list of original branch ids.
    :param bool dc: branch_ids are for dclines or not, defaults to False.
    :return: (*list*) -- list of branch indices for input to Switch
    """
    return [f"{i}dc" if dc else f"{i}ac" for i in branch_ids]

def parse_timepoints(var_dict, variables, mapping_info):
    start = datetime.now()
    
    mapping, index = mapping_info

    var_data = {key: pd.DataFrame(index = index) for key in variables}

    for key in var_dict:
        # assumes key pattern of variableName[parameters]
        split_point = key.find('[')
        var_name = key[:split_point]
        var_params = key[split_point+1:-1].split(',')

        if var_name in variables:
            timepoint = var_params.pop(int(variables[var_name]))

            data = var_data[var_name]
            v = ','.join(var_params)
            
            if v not in data.columns:
                data[v] = None
            data.loc[mapping[timepoint], v] = var_dict[key]['Value']

    print(datetime.now() - start)
    return var_data



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
