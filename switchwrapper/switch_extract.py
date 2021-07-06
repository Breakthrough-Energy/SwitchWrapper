import os
import pickle
from collections import defaultdict

import pandas as pd
from powersimdata.tests.mock_scenario import MockScenario

from switchwrapper import const  # noqa: F401
from switchwrapper.helpers import (
    branch_indices_to_bus_tuple,
    load_timestamps_to_timepoints,
    parse_timepoints,
    recover_plant_indices,
)
from switchwrapper.switch_to_grid import construct_grids_from_switch_results


class SwitchExtract:
    def __init__(
        self,
        results_file,
        timestamps_to_timepoints_file,
        timepoints_file,
        loads_file,
        variable_capacity_factors_file,
        grid,
    ):
        """Extract time series results from Switch results.

        :param str results_file: file path of Switch results pickle file.
        :param str timestamps_to_timepoints_file: file path of mapping.csv.
        :param str timepoints_file: file path of timepoints.csv.
        :param str loads_file: file path of loads.csv, the columns of the loaded demand
            data frame are: 'LOAD_ZONE', 'TIMEPOINT', and 'zone_demand_mw' (no
            meaningful index).
        :param str variable_capacity_factors_file: file path of
            variable_capacity_factors.csv, the columns of the loaded hydro/wind/solar
            data frame are: 'GENERATION_PROJECT', 'timepoint',
            and 'gen_max_capacity_factor' (no meaningful index).
        :param powersimdata.input.grid.Grid grid: grid instance, the input Grid that
            Switch expanded upon.
        """
        self.timestamps_to_timepoints = load_timestamps_to_timepoints(
            timestamps_to_timepoints_file
        )
        self._add_timepoint_weight()
        self._add_investment_year(timepoints_file)
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

        self.loads = pd.read_csv(loads_file)
        self.variable_capacity_factors = pd.read_csv(variable_capacity_factors_file)
        self._reconstruct_input_profiles()

    def _add_timepoint_weight(self):
        """Add weights to timestamps_to_timepoints data frame based on timepoints."""
        self.timestamps_to_timepoints["weight"] = self.timestamps_to_timepoints[
            "timepoint"
        ].map(
            self.timestamps_to_timepoints.reset_index()
            .groupby("timepoint")
            .count()
            .squeeze()
        )

    def _add_investment_year(self, timepoints_file):
        """Get investment year for each timestamp via timepoints.

        :param str timepoints_file: file path of timepoints.csv.
        """
        timepoints = pd.read_csv(timepoints_file)
        timepoints.set_index("timepoint_id", inplace=True)
        self.timestamps_to_timepoints[
            "investment_year"
        ] = self.timestamps_to_timepoints["timepoint"].map(timepoints["ts_period"])

    def _get_parsed_data(self, results_file):
        """Parse Switch results to get raw time series of pg and pf.

        :param str results_file: file path of Switch results pickle file.
        """
        with open(results_file, "rb") as f:
            self.results = pickle.load(f)
        data = ["Variable", "Constraint"]
        variables_to_parse = [["DispatchGen", "DispatchTx"], ["Zone_Energy_Balance"]]
        value_names = ["dispatch", "dual"]
        self.parsed_data = dict()
        for d, var, vn in zip(data, variables_to_parse, value_names):
            self.parsed_data.update(
                parse_timepoints(
                    self.results.solution._list[0][d],
                    var,
                    self.timestamps_to_timepoints,
                    value_name=vn,
                )
            )

    def get_pg(self):
        """Get time series power generation for each plant.

        :return: (*dict*) -- keys are investment years, values are data frames
            indexed by timestamps with plant_id as columns.
        """
        all_pg = self.parsed_data["DispatchGen"].copy()
        # Filter the MultiIndex columns to just the plant IDs (drop storage)
        all_pg = all_pg[[("dispatch", s) for s in self.plant_id_mapping]]
        # Rename to PowerSimData plant indexing
        all_pg.columns = self.plant_id_mapping.index
        pg = dict()
        for year, grid in self.grids.items():
            pg[year] = all_pg.loc[
                self.timestamps_to_timepoints["investment_year"] == year,
                grid.plant.index,
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
        """Get time series power flow for each ac branch, power flow split between
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
        """Get time series power flow for each dcline, power flow split between
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

    def get_lmp(self):
        """Get time series lmp for each bus in every investment year.

        :return: (*dict*) -- keys are investment years, values are data frames indexed
            by timestamps with bua_id as columns.
        """
        all_lmp = self.parsed_data["Zone_Energy_Balance"].copy()
        all_lmp.columns = all_lmp.columns.map(lambda x: int(x[1]))
        lmp = dict()
        for year, grid in self.grids.items():
            lmp[year] = all_lmp.loc[
                self.timestamps_to_timepoints["investment_year"] == year, grid.bus.index
            ].divide(self.timestamps_to_timepoints["weight"], axis="index")
            lmp[year].index = pd.Index(lmp[year].index.map(pd.Timestamp), name="UTC")
        return lmp

    def _reconstruct_input_profiles(self):
        """Given the temporally-reduced profiles that are given to Switch and the
        reduction mapping, reconstruct full-dimension profiles for the Grid that is
        constructed from Switch outputs."""
        # First, demand
        sample_grid = list(self.grids.values())[0]
        loads = self.loads.assign(
            zone_id=self.loads.LOAD_ZONE.map(sample_grid.bus.zone_id)
        )
        loads.drop("LOAD_ZONE", axis=1, inplace=True)
        zone_loads = loads.groupby(["TIMEPOINT", "zone_id"]).sum().squeeze().unstack()
        full_time_zone_loads = zone_loads.loc[
            self.timestamps_to_timepoints["timepoint"]
        ]
        full_time_zone_loads.index = self.timestamps_to_timepoints.index
        # Demand is the same for all years (at least for now)
        self.input_profiles = defaultdict(dict)
        for year in self.grids:
            self.input_profiles["demand"][year] = full_time_zone_loads

        # Then profiles
        id_unmapping = pd.Series(
            self.plant_id_mapping.index, index=self.plant_id_mapping
        )
        # Get original IDs
        original_id_values = self.variable_capacity_factors.assign(
            plant_id=self.variable_capacity_factors.GENERATION_PROJECT.map(id_unmapping)
        ).drop("GENERATION_PROJECT", axis=1)
        # Un-melt data frame
        reshaped_values = (
            original_id_values.set_index(["timepoint", "plant_id"]).squeeze().unstack()
        )
        # Expand to full time dimension
        full_time_profiles = reshaped_values.loc[
            self.timestamps_to_timepoints["timepoint"]
        ]
        full_time_profiles.index = self.timestamps_to_timepoints.index
        # Un-normalize, selecting from and multiplying by the built capacities
        # in each year
        for year, grid in self.grids.items():
            built_variable_plants = grid.plant.query(
                "type in @const.variable_types"
            ).index
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
                self.input_profiles[r][year] = unnormalized_profiles[
                    grid.plant.query("type in @matching").index
                ]

    def get_demand(self):
        """Get time series demand input profiles for each investment year.

        :return: (*dict*) -- keys are investment years, values are data frames indexed
            by timestamps with zone_id as columns.
        """
        return self.input_profiles["demand"]

    def get_hydro(self):
        """Get time series hydro input profiles for each investment year.

        :return: (*dict*) -- keys are investment years, values are data frames indexed
            by timestamps with plant_id as columns.
        """
        return self.input_profiles["hydro"]

    def get_wind(self):
        """Get time series wind input profiles for each investment year.

        :return: (*dict*) -- keys are investment years, values are data frames indexed
            by timestamps with plant_id as columns.
        """
        return self.input_profiles["wind"]

    def get_solar(self):
        """Get time series solar input profiles for each investment year.

        :return: (*dict*) -- keys are investment years, values are data frames indexed
            by timestamps with plant_id as columns.
        """
        return self.input_profiles["solar"]


def get_output_scenarios(switch_files_root):
    """Process Switch results into a series of Scenario objects, one for each
    investment year.

    :param str switch_files_root: file path of files prepared by :func:`prepare_inputs`.
    :return: (*dict*) -- keys are investment years, values are PowerSimData MockScenario
        objects emulating the functionality of PowerSimData Scenario objects.
    """
    # Look up paths based on locations standardized via the `prepare_inputs` function.
    grid_file = os.path.join(switch_files_root, "switchwrapper_inputs", "grid.pkl")
    loads_file = os.path.join(switch_files_root, "inputs", "loads.csv")
    results_file = os.path.join(switch_files_root, "outputs", "results.pickle")
    timepoints_file = os.path.join(
        switch_files_root, "switchwrapper_inputs", "timepoints.csv"
    )
    timestamps_to_timepoints_file = os.path.join(
        switch_files_root, "switchwrapper_inputs", "timestamp_to_timepoints.csv"
    )
    variable_capacity_factors_file = os.path.join(
        switch_files_root, "inputs", "variable_capacity_factors.csv"
    )
    # Then load and use the information
    with open(grid_file, "rb") as f:
        grid = pickle.load(f)
    se = SwitchExtract(
        results_file=results_file,
        timestamps_to_timepoints_file=timestamps_to_timepoints_file,
        timepoints_file=timepoints_file,
        loads_file=loads_file,
        variable_capacity_factors_file=variable_capacity_factors_file,
        grid=grid,
    )
    years = se.grids.keys()
    scenarios = {}
    for year in years:
        mock_scenario = MockScenario(
            pg=se.get_pg()[year],
            pf=se.get_pf()[year],
            dcline_pf=se.get_dcline_pf()[year],
            demand=se.get_demand()[year],
            hydro=se.get_hydro()[year],
            solar=se.get_solar()[year],
            wind=se.get_wind()[year],
        )
        mock_scenario.state.grid = se.grids[year]
        scenarios[year] = mock_scenario

    return scenarios
