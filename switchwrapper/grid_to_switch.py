import os

import pandas as pd
from haversine import haversine

from switchwrapper import const


def grid_to_switch(grid, outputfolder):
    # Create the outputfolder, if it doesn't already exist
    os.makedirs(outputfolder, exist_ok=True)

    # First, prompt the user for information not contained in const or the passed grid
    base_year = get_base_year()
    inv_period, period_start, period_end = get_inv_periods()

    # Then, calculate information which feeds multiple data frames
    cost_at_min_power, single_segment_slope = linearize_gencost(grid)
    average_fuel_cost = calculate_average_fuel_cost(grid.plant)

    # Finally, generate and save data frames to CSVs
    financials_filepath = os.path.join(outputfolder, "financials.csv")
    build_financials(base_year).to_csv(financials_filepath, index=False)

    fuels_filepath = os.path.join(outputfolder, "fuels.csv")
    build_fuels().to_csv(fuels_filepath, index=False)

    fuel_cost_filepath = os.path.join(outputfolder, "fuel_cost.csv")
    fuel_cost = build_fuel_cost(average_fuel_cost, base_year, inv_period)
    fuel_cost.to_csv(fuel_cost_filepath, index=False)

    generation_projects_info_filepath = os.path.join(
        outputfolder, "generation_projects_info.csv"
    )
    generation_project_info = build_generation_projects_info(
        grid.plant, single_segment_slope, average_fuel_cost
    )
    generation_project_info.to_csv(generation_projects_info_filepath, index=False)

    gen_build_costs_filepath = os.path.join(outputfolder, "gen_build_costs.csv")
    gen_build_costs = build_gen_build_costs(grid.plant, cost_at_min_power, inv_period)
    gen_build_costs.to_csv(gen_build_costs_filepath, index=False)

    gen_build_predetermined_filepath = os.path.join(
        outputfolder, "gen_build_predetermined.csv"
    )
    build_gen_build_predetermined(grid.plant).to_csv(
        gen_build_predetermined_filepath, index=False
    )

    load_zones_filepath = os.path.join(outputfolder, "load_zones.csv")
    build_load_zones(grid.bus).to_csv(load_zones_filepath, index=False)

    non_fuel_energy_source_filepath = os.path.join(
        outputfolder, "non_fuel_energy_source.csv"
    )
    build_non_fuel_energy_source().to_csv(non_fuel_energy_source_filepath, index=False)

    periods_filepath = os.path.join(outputfolder, "periods.csv")
    build_periods(inv_period, period_start, period_end).to_csv(
        periods_filepath, index=False
    )

    transmission_lines_filepath = os.path.join(outputfolder, "transmission_lines.csv")
    build_transmission_lines(grid).to_csv(transmission_lines_filepath, index=False)

    trans_params_filepath = os.path.join(outputfolder, "trans_params.csv")
    build_trans_params().to_csv(trans_params_filepath, index=False)


def get_base_year():
    """Prompt the user for a base year.

    :return: (*int*) -- base year.
    """
    year = input("Please enter base study year (normally PowerSimData scenario year): ")
    return int(year)


def get_inv_periods():
    """Prompt the user for investment stage, investment period, start year of each
    period, end year of each period.

    :return: (*tuple*) -- 3-tuple of lists, investment periods, start years, end years
    """
    while True:
        num_inv_stages = input("Please enter the number of investment stages: ")
        if not num_inv_stages.isdigit():
            print("number of investment stages must be an integer, please re-enter.")
        else:
            num_inv_stages = int(num_inv_stages)
            break
    if num_inv_stages == 1:
        print("Single stage expansion identified.")
    else:
        print("Multi stage expansion identified.")

    while True:
        inv_period = input(
            "Please enter investment period year, separate by space: "
        ).split()
        if len(inv_period) == num_inv_stages:
            try:
                inv_period = [int(i) for i in inv_period]
                break
            except ValueError:
                print("All investment period years must be integers, please re-enter.")
                continue
        print(
            "investment period must match the number of investment stages, "
            "please re-enter."
        )

    while True:
        period_start = input(
            "Please enter start year for each period, separate by space: "
        ).split()
        if len(period_start) == num_inv_stages:
            try:
                period_start = [int(p) for p in period_start]
                break
            except ValueError:
                print("All start years must be integers, please re-enter.")
                continue
        print(
            "start year for each period must match the number of investment stages, "
            "please re-enter."
        )

    while True:
        period_end = input(
            "Please enter end year for each period, separate by space: "
        ).split()
        if len(period_end) == num_inv_stages:
            try:
                period_end = [int(p) for p in period_end]
                break
            except ValueError:
                print("All end years must be integers, please re-enter.")
                continue
        print(
            "end year for each period must match the number of investment stages, "
            "please re-enter."
        )
    return inv_period, period_start, period_end


def calculate_average_fuel_cost(plant):
    """Calculate average fuel cost, by bus_id for buses containing generators.

    :param pandas.DataFrame plant: plant data from a Grid object.
    :return: (*pandas.DataFrame*) -- data frame of average fuel cost by bus_id.
    """
    plant_mod = plant.copy()
    # Map our generator types to Switch fuel types
    plant_mod["fuel"] = plant_mod["type"].map(const.fuel_mapping)
    # Calculate the average fuel cost for each (bus_id, fuel)
    relevant_fuel_columns = ["bus_id", "fuel", "GenFuelCost"]
    fuel_cost = plant_mod[relevant_fuel_columns].groupby(["bus_id", "fuel"]).mean()
    return fuel_cost


def linearize_gencost(grid):
    """Calculate linearized cost parameters, incorporating assumed minimum generation.

    :param powersimdata.input.grid.Grid grid: grid instance.
    :return: (*tuple*) -- two pandas Series objects, indexed by plant ID within ``grid``:
        first is the cost of running each generator at minimum generation.
        second is the single-segment linearized slope of each generator's cost curve.
    """
    plant_mod = grid.plant.copy()
    plant_mod.Pmin = plant_mod.apply(
        lambda x:
        x.Pmax * const.assumed_pmins.get(x.type, const.assumed_pmins["default"])
        if const.assumed_pmins.get(x.type, const.assumed_pmins["default"]) is not None
        else x.Pmin,
        axis=1,
    )
    gencost = grid.gencost["before"]
    cost_at_min_power = (
        gencost.c0 + gencost.c1 * plant_mod.Pmin + gencost.c2 * plant_mod.Pmin ** 2
    )
    cost_at_max_power = (
        gencost.c0 + gencost.c1 * plant_mod.Pmax + gencost.c2 * plant_mod.Pmax ** 2
    )
    single_segment_slope = (cost_at_max_power - cost_at_min_power) / (
        plant_mod.Pmax - plant_mod.Pmin
    )
    single_segment_slope.fillna(0, inplace=True)
    return cost_at_min_power, single_segment_slope


def build_financials(base_year):
    """Parse financial parameters constants and base year input to a data frame.

    :param int/str base_year: Information to be added in the 'base_year' column.
    :return: (*pandas.DataFrame*) -- single-row data frame with all params.
    """
    financials = pd.DataFrame([const.financial_parameters])
    financials["base_year"] = base_year
    return financials


def build_fuels():
    """Parse set of fuels to a data frame.

    :return: (*pandas.DataFrame*) -- single-row data frame with all params.
    """
    fuels = pd.DataFrame({"fuel": const.fuels})
    fuels["co2_intensity"] = "."
    fuels["upstream_co2_intensity"] = "."
    return fuels


def build_fuel_cost(average_fuel_cost, base_year, inv_period):
    """Create a data frame of average fuel costs by zone and fuel, and project these
        costs to future years.

    :param pandas.DataFrame average_fuel_cost: average fuel cost by bus_id.
    :param list inv_period: list of investment period years, as integers.
    :return: (*pandas.DataFrame*) -- data frame of fuel costs by period, zone, and fuel.
    """
    fuel_cost = average_fuel_cost.copy()
    # Retrieve the original `bus_id` and `fuel` columns, rename `bus_id` to `load_zone`
    fuel_cost.reset_index(inplace=True)
    fuel_cost.rename(columns={"bus_id": "load_zone"})
    # Duplicate each row N times, where N is the number of investment years
    original_fuel_cost_length = len(fuel_cost)
    fuel_cost = fuel_cost.loc[fuel_cost.index.repeat(len(inv_period))]
    # Fill in different years and inflation values for the repeated rows
    fuel_cost["period"] = inv_period * original_fuel_cost_length
    inflation_factors = [
        (1 + const.financial_parameters["interest_rate"])**(year - base_year)
        for year in inv_period
    ]
    fuel_cost["inflation"] = inflation_factors * original_fuel_cost_length
    # Use inflation values to calculate future fuel costs
    fuel_cost["fuel_cost"] = fuel_cost["GenFuelCost"] * fuel_cost["inflation"]
    fuel_cost["fuel_cost"] = fuel_cost["fuel_cost"].round(2)
    # Clean up columns we don't need
    fuel_cost.drop(columns=["GenFuelCost", "inflation"], inplace=True)
    # Clean up any rows we don't need
    fuel_cost = fuel_cost.query("fuel_cost > 0")

    return fuel_cost


def build_generation_projects_info(plant, single_segment_slope, average_fuel_cost):
    """Build data frame for generation_projects_info.

    :param pandas.DataFrame plant: data frame of current generators.
    :param pandas.Series single_segment_slope: single-segment linearized slope of each
        generator's cost curve, from :func:`linearize_gencost`.
    :param pandas.DataFrame average_fuel_cost: average fuel cost by bus_id, from
        :func:`calculate_average_fuel_cost`.
        This is single-column ("GenFuelCost") and multi-index ("bus_id", "fuel").
    :return: (*pandas.DataFrame*) -- data frame of generation project info.
    """
    # Extract information from inputs
    original_plant_indices = [f"g{p}" for p in plant.index.tolist()]
    hypothetical_plant_indices = [f"{o}i" for o in original_plant_indices]
    all_plant_indices = original_plant_indices + hypothetical_plant_indices

    # Use inputs for intermediate calculations
    fuel_gencost = single_segment_slope * const.assumed_fuel_share_of_gencost
    nonfuel_gencost = single_segment_slope * (1 - const.assumed_fuel_share_of_gencost)
    fuel_cost_per_generator = plant.apply(
        lambda x: average_fuel_cost.loc[
            (x.bus_id, const.fuel_mapping[x.type]), "GenFuelCost"
        ],
        axis=1,
    )
    estimated_heatrate = (fuel_gencost / fuel_cost_per_generator).fillna(0)

    # Finally, construct data frame and return
    df = pd.DataFrame()
    df["GENERATION_PROJECT"] = all_plant_indices
    df["gen_tech"] = plant.type.tolist() * 2
    df["gen_tech_zone"] = plant.bus_id.tolist() * 2
    df["gen_connect_cost_per_mw"] = 0
    df["gen_capacity_limit_mw"] = [
        const.assumed_capacity_limits.get(t, const.assumed_capacity_limits["default"])
        for t in plant.type.tolist() * 2
    ]
    df["gen_full_load_heat_rate"] = estimated_heatrate.tolist() * 2
    df["gen_variable_om"] = nonfuel_gencost.tolist() * 2
    df["gen_max_age"] = [
        const.assumed_ages_by_type.get(t, const.assumed_ages_by_type["default"])
        for t in plant.type.tolist() * 2
    ]
    df["gen_min_build_capacity"] = 0
    df["gen_scheduled_outage_rate"] = 0
    df["gen_forced_outage_rate"] = 0
    df["gen_is_variable"] = list(plant.type.isin(const.variable_types).astype(int)) * 2
    df["gen_is_baseload"] = list(plant.type.isin(const.baseload_types).astype(int)) * 2
    df["gen_is_cogen"] = 0
    df["gen_energy_source"] = plant.type.map(const.fuel_mapping).tolist() * 2
    df["gen_unit_size"] = "."
    df["gen_ccs_capture_efficiency"] = "."
    df["gen_ccs_energy_load"] = "."
    df["gen_storage_efficiency"] = "."
    df["gen_store_to_release_ratio"] = "."

    return df


def build_gen_build_costs(plant, cost_at_min_power, inv_period):
    """Build a data frame of generation projects, both existing and hypothetical.

    :param pandas.DataFrame plant: data frame of current generators.
    :param pandas.Series cost_at_min_power: cost of running generator at minimum power.
    :param list inv_period: list of investment period years.
    :return: (*pandas.DataFrame*) -- data frame of existing and hypothetical generators.
    """
    # Build lists for each columns, which apply to one year
    original_plant_indices = [f"g{p}" for p in plant.index.tolist()]
    overnight_costs = plant["type"].map(const.investment_costs_by_type).tolist()
    gen_fixed_om = (cost_at_min_power / plant.Pmax).fillna(0.0).tolist()

    # Extend these lists to multiple years
    build_years = [2019] + inv_period
    hypothetical_plant_indices = [f"{o}i" for o in original_plant_indices]
    plant_index_lists = [original_plant_indices] + [
        hypothetical_plant_indices for i in inv_period
    ]
    all_indices = sum(plant_index_lists, [])
    all_build_years = sum([[b] * len(original_plant_indices) for b in build_years], [])
    all_overnight_costs = sum([overnight_costs for b in build_years], [])
    all_gen_fixed_om = sum([gen_fixed_om for b in build_years], [])

    # Create a dataframe from the collected lists
    gen_build_costs = pd.DataFrame(
        {
            "GENERATION_PROJECT": all_indices,
            "build_year": all_build_years,
            "gen_overnight_cost": all_overnight_costs,
            "gen_fixed_om": all_gen_fixed_om,
        }
    )
    return gen_build_costs


def build_gen_build_predetermined(plant):
    """Build a data frame of generator capacity and build year

    :param pandas.DataFrame plant: data frame of generators in a grid instance.
    :return: (*pandas.DataFrame*) -- data frame of existing generators.
    """
    gen_build_predetermined = plant["Pmax"].reset_index()
    gen_build_predetermined["build_year"] = 2019
    gen_build_predetermined.rename(
        columns={
            "plant_id": "GENERATION_PROJECT",
            "Pmax": "gen_predetermined_cap",
        },
        inplace=True,
    )
    gen_build_predetermined = gen_build_predetermined[
        ["GENERATION_PROJECT", "build_year", "gen_predetermined_cap"]
    ]
    return gen_build_predetermined


def build_load_zones(bus):
    """Parse bus data frame and load zone constants to a data frame.

    :param pandas.DataFrame bus: bus data from a Grid object.
    :return: (*pandas.DataFrame*) -- data frame with constants added to bus indices.
    """
    load_zones = bus.index.to_frame()
    load_zones["dbid"] = range(1, len(load_zones) + 1)
    for k, v in const.load_parameters.items():
        load_zones[k] = v
    return load_zones


def build_non_fuel_energy_source():
    """Parse list of non fuel energy sources to a data frame

    :return: (*pandas.DataFrame*) -- single column data frame with non-fuel energy
        sources
    """
    non_fuel_energy_source = pd.DataFrame({"energy_source": const.non_fuels})
    return non_fuel_energy_source


def build_periods(inv_period, period_start, period_end):
    """Parse user input investment period information into a data frame.

    :param list inv_period: list of strings for each investment period year
    :param list period_start: list of strings for start year of each period
    :param list period_end: list of strings for end year of each period
    :return: (*pandas.DataFrame*) -- periods data frame with investment period
        information.
    """
    periods = pd.DataFrame(columns=["INVESTMENT_PERIOD", "period_start", "period_end"])
    periods["INVESTMENT_PERIOD"] = inv_period
    periods["period_start"] = period_start
    periods["period_end"] = period_end
    return periods


def branch_efficiency(from_bus_voltage, to_bus_voltage):
    """Calculate branch efficiency based on start and end bus baseKV.

    :param int/float from_bus_voltage: start bus baseKV
    :param int/float to_bus_voltage: end bus baseKV
    :return: (*float*) -- efficiency rate of a branch
    """
    if from_bus_voltage == to_bus_voltage:
        return const.assumed_branch_efficiencies.get(
            from_bus_voltage, const.assumed_branch_efficiencies["default"]
        )
    else:
        return const.assumed_branch_efficiencies["default"]


def build_aclines(grid):
    """Create a data frame for ac transmission lines with required columns for
    :func:`build_transmission_lines`.

    :param powersimdata.input.grid.Grid grid: grid instance
    :return: (*pandas.DataFrame*) -- ac transmission line data frame
    """
    acline = grid.branch[["from_bus_id", "to_bus_id", "rateA"]].reset_index()
    acline["trans_length_km"] = list(
        map(
            haversine,
            grid.bus.loc[acline["from_bus_id"], ["lat", "lon"]].values,
            grid.bus.loc[acline["to_bus_id"], ["lat", "lon"]].values,
        )
    )
    acline["trans_efficiency"] = list(
        map(
            branch_efficiency,
            grid.bus.loc[acline["from_bus_id"], "baseKV"],
            grid.bus.loc[acline["to_bus_id"], "baseKV"],
        )
    )
    return acline.round(2)


def build_dclines(grid):
    """Create a data frame for dc transmission lines with required columns for
    :func:`build_transmission_lines`.

    :param powersimdata.input.grid.Grid grid: grid instance
    :return: (*pandas.DataFrame*) -- dc transmission line data frame
    """
    dcline = grid.dcline[["from_bus_id", "to_bus_id", "Pmax"]].reset_index()
    dcline["trans_length_km"] = list(
        map(
            haversine,
            grid.bus.loc[dcline["from_bus_id"], ["lat", "lon"]].values,
            grid.bus.loc[dcline["to_bus_id"], ["lat", "lon"]].values,
        )
    )
    dcline["trans_efficiency"] = 0.99
    dcline["dcline_id"] = dcline["dcline_id"].apply(lambda x: str(x) + "dl")
    dcline.rename(columns={"dcline_id": "branch_id", "Pmax": "rateA"}, inplace=True)
    return dcline.round(2)


def build_transmission_lines(grid):
    """Parse branch and dcline data frames of a grid instance into a transmission
    line data frame with new columns for length and efficiency.

    :param powersimdata.input.grid.Grid grid: grid instance
    :return: (*pandas.DataFrame*) -- transmission line data frame
    """
    acline = build_aclines(grid)
    dcline = build_dclines(grid)
    transmission_line = pd.concat([dcline, acline], ignore_index=True)
    transmission_line.rename(
        columns={
            "branch_id": "TRANSMISSION_LINE",
            "from_bus_id": "trans_lz1",
            "to_bus_id": "trans_lz2",
            "rateA": "existing_trans_cap",
        },
        inplace=True,
    )
    transmission_line = transmission_line[
        [
            "TRANSMISSION_LINE",
            "trans_lz1",
            "trans_lz2",
            "trans_length_km",
            "trans_efficiency",
            "existing_trans_cap",
        ]
    ]
    return transmission_line


def build_trans_params():
    """Parse transmission parameters constants to a data frame.

    :return: (*pandas.DataFrame*) -- single-row data frame with all params.
    """
    return pd.DataFrame([const.transmission_parameters])
