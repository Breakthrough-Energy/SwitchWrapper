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


def make_branch_indices(branch_ids, dc=False):
    """Make the indices of existing branch for input to Switch.

    :param iterable branch_ids: list of original branch ids.
    :param bool dc: branch_ids are for dclines or not, defaults to False.
    :return: (*list*) -- list of branch indices for input to Switch
    """
    if dc:
        return [str(i) + "dc" for i in branch_ids]
    else:
        return [str(i) + "ac" for i in branch_ids]


def recover_plant_indices(switch_plant_ids):
    """Recover the plant indices from Switch outputs.

    :param iterable switch_plant_ids: Switch plant indices.
    :return: (*pandas.Series*) -- indices are original plant ids with new plants
        added, values are Switch plant indices.
    """
    original_plant_num = sum(1 for ind in switch_plant_ids if ind[-1] != "i")
    plant_ids = dict()
    new_plant_index_start = int(switch_plant_ids[original_plant_num - 1][1:])
    cnt = 0
    for ind in switch_plant_ids:
        if ind[-1] != "i":
            plant_ids[int(ind[1:])] = ind
        else:
            cnt += 1
            plant_ids[new_plant_index_start + cnt] = ind
    return pd.Series(plant_ids)
