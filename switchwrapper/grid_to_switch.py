import os

import pandas as pd

from switchwrapper import const


def grid_to_switch(grid, outputfolder):
    # Create the outputfolder, if it doesn't already exist
    os.makedirs(outputfolder, exist_ok=True)

    # First, prompt the user for information not contained in const or the passed grid
    base_year = get_base_year()
    inv_period, period_start, period_end = get_inv_periods()

    # Then, calculate information which feeds multiple data frames
    cost_at_min_power, single_segment_slope = linearize_gencost(grid)

    # Finally, generate and save data frames to CSVs
    financials_filepath = os.path.join(outputfolder, "financials.csv")
    build_financials(base_year).to_csv(financials_filepath, index=False)

    fuels_filepath = os.path.join(outputfolder, "fuels.csv")
    build_fuels().to_csv(fuels_filepath, index=False)

    fuel_cost_filepath = os.path.join(outputfolder, "fuel_cost.csv")
    build_fuel_cost().to_csv(fuel_cost_filepath, index=False)

    generation_projects_info_filepath = os.path.join(
        outputfolder, "generation_projects_info.csv"
    )
    build_generation_projects_info().to_csv(
        generation_projects_info_filepath, index=False
    )

    gen_build_costs_filepath = os.path.join(outputfolder, "gen_build_costs.csv")
    gen_build_costs = build_gen_build_costs(grid.plant, cost_at_min_power, inv_period)
    gen_build_costs.to_csv(gen_build_costs_filepath, index=False)

    gen_build_predetermined_filepath = os.path.join(
        outputfolder, "gen_build_predetermined.csv"
    )
    build_gen_build_predetermined().to_csv(
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
    build_transmission_lines().to_csv(transmission_lines_filepath, index=False)

    trans_params_filepath = os.path.join(outputfolder, "trans_params.csv")
    build_trans_params().to_csv(trans_params_filepath, index=False)


def get_base_year():
    """Prompt the user for a base year.

    :return: (*str*) -- base year.
    """
    return input("Please enter base study year (normally PowerSimData scenario year): ")


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
            break
        print(
            "investment period must match the number of investment stages, "
            "please re-enter."
        )

    while True:
        period_start = input(
            "Please enter start year for each period, separate by space: "
        ).split()
        if len(period_start) == num_inv_stages:
            break
        print(
            "start year for each period must match the number of investment stages, "
            "please re-enter."
        )

    while True:
        period_end = input(
            "Please enter end year for each period, separate by space: "
        ).split()
        if len(period_end) == num_inv_stages:
            break
        print(
            "end year for each period must match the number of investment stages, "
            "please re-enter."
        )
    return inv_period, period_start, period_end


def linearize_gencost(grid):
    """Calculate linearized cost parameters, incorporating assumed minimum generation.

    :param powersimdata.input.grid.Grid grid: grid instance.
    :return: (*tuple*) -- two pandas Series objects, indexed by plant ID within ``grid``:
        first is the cost of running each generator at minimum generation.
        second is the single-segment linearized slope of each generator's cost curve.
    """
    plant_mod = grid.plant.copy()
    plant_mod.Pmin = plant_mod.apply(
        lambda x: x.Pmax
        * const.assumed_pmins.get(x.type, const.assumed_pmins["default"])
        if const.assumed_pmins.get(x.type, const.assumed_pmins["default"]) != None
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


def build_fuel_cost():
    pass


def build_generation_projects_info():
    pass


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


def build_gen_build_predetermined():
    pass


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


def build_transmission_lines():
    pass


def build_trans_params():
    """Parse transmission parameters constants to a data frame.

    :return: (*pandas.DataFrame*) -- single-row data frame with all params.
    """
    return pd.DataFrame([const.transmission_parameters])
