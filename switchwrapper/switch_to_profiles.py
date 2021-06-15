import pickle
import pandas as pd

from switchwrapper import const  # noqa: F401
from switchwrapper.helpers import (
    branch_indices_to_bus_tuple,
    load_mapping,
    parse_timepoints,
    recover_plant_indices,
)
from switchwrapper.switch_to_grid import construct_grids_from_switch_results


def reconstruct_input_profiles(
    grids,
    loads,
    variable_capacity_factors,
    timestamps_to_timepoints,
):
    """Given the temporally-reduced profiles that are given to Switch and the reduction
    mapping, reconstruct full-dimension profiles for the Grid that is constructed from
    Switch outputs.

    :param dict grids: grid objects after expansion. Keys are integers representing the
        investment year, values are powersimdata.input.grid.Grid objects representing
        the grid after that year's investments
    :param pandas.DataFrame loads: demand data frame. columns are:
        'LOAD_ZONE', 'TIMEPOINT', and 'zone_demand_mw' (no meaningful index).
    :param pandas.DataFrame variable_capacity_factors: hydro/solar/wind data frame.
        columns are: 'GENERATION_PROJECT', 'timepoint', and 'gen_max_capacity_factor'
        (no meaningful index).
    :param pandas.Series timestamps_to_timepoints: index is full-dimension timestamps,
        values are the timepoint that each timestamp was mapped to (int).
    :return: (*dict*) -- keys match the investment years from ``grids``, value are
        dicts, with sub-keys: {'demand', 'hydro', 'solar', 'wind'}, values are
        pandas DataFrames, indexed by timestamps matching the index in
        ``timestamps_to_timepoints``, with integer columns representing plant IDs (for
        hydro, solar, wind) or zone IDs (for demand). The data frame values are floats,
        and the units are MW.
    """
    # First, demand
    sample_grid = list(grids.values())[0]
    loads = loads.assign(zone_id=loads.LOAD_ZONE.map(sample_grid.bus.zone_id))
    loads.drop("LOAD_ZONE", axis=1, inplace=True)
    zone_loads = loads.groupby(["TIMEPOINT", "zone_id"]).sum().squeeze().unstack()
    full_time_zone_loads = zone_loads.loc[timestamps_to_timepoints.tolist()]
    full_time_zone_loads.index = timestamps_to_timepoints.index
    # Demand is the same for all years (at least for now)
    profiles = {year: {"demand": full_time_zone_loads} for year in grids.keys()}

    # Then profiles
    switch_plant_ids = variable_capacity_factors.GENERATION_PROJECT.unique()
    plant_ids = recover_plant_indices(switch_plant_ids)[0]
    id_unmapping = pd.Series(plant_ids.index, index=plant_ids)
    # Get original IDs
    original_id_values = variable_capacity_factors.assign(
        plant_id=variable_capacity_factors.GENERATION_PROJECT.map(id_unmapping)
    ).drop("GENERATION_PROJECT", axis=1)
    # Un-melt data frame
    reshaped_values = (
        original_id_values.set_index(["timepoint", "plant_id"]).squeeze().unstack()
    )
    # Expand to full time dimension
    full_time_profiles = reshaped_values.loc[timestamps_to_timepoints.tolist()]
    full_time_profiles.index = timestamps_to_timepoints.index
    # Un-normalize, selecting from and multiplying by the built capacities in each year
    for year, grid in grids.items():
        built_variable_plants = grid.plant.query("type in @const.variable_types").index
        unnormalized_profiles = full_time_profiles[built_variable_plants].multiply(
            grid.plant.Pmax.loc[built_variable_plants]
        )
        resource_types = {
            "hydro": {"hydro"},
            "solar": {"solar"},
            "wind": {"wind", "wind_offshore"},
        }
        for r in ["hydro", "solar", "wind"]:
            matching = resource_types[r]  # noqa: F841
            profiles[year][r] = unnormalized_profiles[
                grid.plant.query("type in @matching").index
            ]

    return profiles


class ExtractTimeseries:
    def __init__(self, results_file, mapping_file, timepoints_file, grid):
        """Extract timeseries results from Switch results.

        :param str results_file: file path of Switch results pickle file.
        :param str mapping_file: file path of mapping.csv.
        :param str timepoints_file: file path of timepoints.csv.
        :param powersimdata.input.grid.Grid grid: grid instance.
        """
        self.mapping = load_mapping(mapping_file)
        self._timestamp_to_investment_year(timepoints_file)
        self._get_parsed_data(results_file)
        self.plant_id_mapping, _ = recover_plant_indices(
            self.parsed_data["DispatchGen"].columns.map(lambda x: x[1])
        )
        self._calculate_net_pf()
        (
            self.ac_branch_id_mapping,
            self.dc_branch_id_mapping,
        ) = branch_indices_to_bus_tuple(grid)
        self.grids = construct_grids_from_switch_results(grid, self.results)

    def _timestamp_to_investment_year(self, timepoints_file):
        """Get investment year for each timestamp via timepoints.

        :param str timepoints_file: file path of timepoints.csv.
        """
        timepoints = pd.read_csv(timepoints_file)
        timepoints.set_index("timepoint_id", inplace=True)
        self.timestamp_to_investment_year = pd.Series(
            self.mapping["timepoint"].map(timepoints["ts_period"]),
            index=self.mapping.index,
        )

    def _get_parsed_data(self, results_file):
        """Parse Switch results to get raw timeseries of pg and pf.

        :param str results_file: file path of Switch results pickle file.
        """
        with open(results_file, "rb") as f:
            self.results = pickle.load(f)
        data = self.results.solution._list[0].Variable
        variables_to_parse = ["DispatchGen", "DispatchTx"]
        self.parsed_data = parse_timepoints(data, variables_to_parse, self.mapping)

    def get_pg(self):
        """Get timeseries power generation for each plant.

        :return: (*dict*) -- keys are investment years, values are data frames
            indexed by timestamps with plant_id as columns.
        """
        all_pg = self.parsed_data["DispatchGen"].copy()
        all_pg.columns = self.plant_id_mapping.index
        pg = dict()
        for year, grid in self.grids.items():
            pg[year] = all_pg.loc[
                self.timestamp_to_investment_year == year, grid.plant.index
            ]
            pg[year].index = pd.Index(pg[year].index.map(pd.Timestamp), name="UTC")
        return pg

    def _calculate_net_pf(self):
        """Calculate net power flow between every bus tuple."""
        original_tx = self.parsed_data["DispatchTx"].copy()
        original_tx.columns = self.parsed_data["DispatchTx"].columns.map(
            lambda x: tuple(map(int, x[1].split(",")))
        )
        mirror_tx = original_tx.copy()
        mirror_tx.columns = mirror_tx.columns.map(lambda x: (x[1], x[0]))
        self.net_tx = original_tx - mirror_tx

    def get_pf(self):
        """Get timeseries power flow for each ac branch, power flow split between
        parallel branches by reactance.

        :return: (*dict*) -- keys are investment years, values are data frames
            indexed by timestamps with branch_id as columns.
        """
        pf = dict()
        for year, grid in self.grids.items():
            pf[year] = self.net_tx[grid.branch.index.map(self.ac_branch_id_mapping)]
            pf[year].columns = grid.branch.index
            branch = grid.branch.assign(b=grid.branch.x.apply(lambda x: 1 / x))
            bus_tuple_b = branch.groupby(["from_bus_id", "to_bus_id"]).sum()["b"]
            branch["total_b"] = bus_tuple_b.loc[
                branch.index.map(self.ac_branch_id_mapping)
            ].values
            pf[year] *= branch["b"] / branch["total_b"]
            pf[year].index = pd.Index(pf[year].index.map(pd.Timestamp), name="UTC")
        return pf

    def get_dcline_pf(self):
        """Get timeseries power flow for each dcline, power flow split between
        parallel lines by capacity.

        :return: (*dict*) -- keys are investment years, values are data frames indexed
            by timestamps with dcline_id as columns.
        """
        dcline_pf = dict()
        for year, grid in self.grids.items():
            dcline_pf[year] = self.net_tx[
                grid.dcline.index.map(self.dc_branch_id_mapping)
            ]
            dcline_pf[year].columns = grid.dcline.index
            bus_tuple_pmax = grid.dcline.groupby(["from_bus_id", "to_bus_id"]).sum()[
                "Pmax"
            ]
            dcline = grid.dcline.assign(
                total_pmax=bus_tuple_pmax.loc[
                    grid.dcline.index.map(self.dc_branch_id_mapping)
                ].values
            )
            dcline_pf[year] *= dcline["Pmax"] / dcline["total_pmax"]
            dcline_pf[year].index = pd.Index(
                dcline_pf[year].index.map(pd.Timestamp), name="UTC"
            )
        return dcline_pf
