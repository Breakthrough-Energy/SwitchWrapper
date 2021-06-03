import re

import pandas as pd


def make_indices(plant_ids):
    """Make the indices for existing and hypothetical generators for input to Switch.

    :param iterable plant_ids: plant IDs.
    :return: (*tuple*) -- The first element is a list of indices for existing generators
        and the second element is a list of indices for hypothetical generators.
    """
    original_plant_indices = [f"g{p}" for p in plant_ids]
    hypothetical_plant_indices = [f"{o}i" for o in original_plant_indices]
    return original_plant_indices, hypothetical_plant_indices


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
