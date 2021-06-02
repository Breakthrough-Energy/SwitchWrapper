import pandas as pd

from switchwrapper.helpers import recover_plant_indices


def test_recover_plant_indices():
    args = [
        ["g1", "g2", "g1i", "g2i"],
        ["g1", "g2", "g1i"],
        ["g1", "g2"],
    ]
    expected_return = [
        pd.Series({1: "g1", 2: "g2", 3: "g1i", 4: "g2i"}),
        pd.Series({1: "g1", 2: "g2", 3: "g1i"}),
        pd.Series({1: "g1", 2: "g2"}),
    ]
    for a, e in zip(args, expected_return):
        assert e.equals(recover_plant_indices(a))
