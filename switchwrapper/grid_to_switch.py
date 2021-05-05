import os

import pandas as pd

from switchwrapper import const


def grid_to_switch(grid, outputfolder):
    base_year = get_base_year()
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
    build_gen_build_costs().to_csv(gen_build_costs_filepath, index=False)

    gen_build_predetermined_filepath = os.path.join(
        outputfolder, "gen_build_predetermined.csv"
    )
    build_gen_build_predetermined().to_csv(
        gen_build_predetermined_filepath, index=False
    )

    load_zones_filepath = os.path.join(outputfolder, "load_zones.csv")
    build_load_zones().to_csv(load_zones_filepath, index=False)

    non_fuel_energy_source_filepath = os.path.join(
        outputfolder, "non_fuel_energy_source.csv"
    )
    build_non_fuel_energy_source().to_csv(non_fuel_energy_source_filepath, index=False)

    periods_filepath = os.path.join(outputfolder, "periods.csv")
    build_periods().to_csv(periods_filepath, index=False)

    transmission_lines_filepath = os.path.join(outputfolder, "transmission_lines.csv")
    build_transmission_lines().to_csv(transmission_lines_filepath, index=False)

    trans_params_filepath = os.path.join(outputfolder, "trans_params.csv")
    build_trans_params().to_csv(trans_params_filepath, index=False)


def get_base_year():
    """Prompt the user for a base year.

    :return: (*str*) -- base year.
    """
    return input("Please enter base study year (normally PowerSimData scenario year): ")


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


def build_gen_build_costs():
    pass


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
    pass


def build_periods():
    pass


def build_transmission_lines():
    pass


def build_trans_params():
    """Parse transmission parameters constants to a data frame.

    :return: (*pandas.DataFrame*) -- single-row data frame with all params.
    """
    return pd.DataFrame([const.transmission_parameters])
