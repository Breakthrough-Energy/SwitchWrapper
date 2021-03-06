switch_modules = [
    "switch_model",
    "switch_model.timescales",
    "switch_model.financials",
    "switch_model.balancing.load_zones",
    "switch_model.energy_sources.properties",
    "switch_model.generators.core.build",
    "switch_model.generators.core.dispatch",
    "switch_model.generators.core.no_commit",
    "switch_model.generators.extensions.storage",
    "switch_model.energy_sources.fuel_costs.simple",
    "switch_model.transmission.local_td",
    "switch_model.transmission.transport.build",
    "switch_model.transmission.transport.dispatch",
    "switch_model.reporting",
]

base_year = 2019

financial_parameters = {
    "discount_rate": 0.079,
    "interest_rate": 0.029,
}

storage_parameters = {
    "efficiency": 1,
    "max_age": 20,  # years
    "max_cycles": 200,  # cycles per year
    "overnight_power_cost": 0,
    "overnight_energy_cost": 2.13e5,
    "tech": "Battery",
}

fuels = ["Coal", "NaturalGas", "Uranium", "Petroleum", "Other"]

fuel_mapping = {
    "wind": "Wind",
    "wind_offshore": "Wind",
    "solar": "Solar",
    "hydro": "Water",
    "geothermal": "Geothermal",
    "coal": "Coal",
    "ng": "NaturalGas",
    "nuclear": "Uranium",
    "dfo": "Petroleum",
    "other": "Other",
    "storage": "Electricity",
}

load_parameters = {
    "existing_local_td": 99999,
    "local_td_annual_cost_per_mw": 0,
}

transmission_parameters = {
    "trans_capital_cost_per_mw_km": 621,
    "trans_lifetime_yrs": 40,
    "trans_fixed_om_fraction": 0,
    "distribution_loss_rate": 0,
}

non_fuels = [
    "Wind",
    "Solar",
    "Water",
    "Geothermal",
    "Electricity",
]

investment_costs_by_type = {
    "coal": 5.255e6,
    "dfo": 1e7,
    "geothermal": 7.696e6,
    "hydro": 5.983e6,
    "ng": 1.616e6,
    "nuclear": 7.186e6,
    "other": 1e7,
    "solar": 1.6e6,
    "wind": 1.956e6,
    "wind_offshore": 5.342e6,
}

assumed_pmins = {
    "coal": None,
    "default": 0,
    "geothermal": 0.95,
    "nuclear": 0.95,
}

assumed_branch_efficiencies = {
    115: 0.9,
    138: 0.94,
    161: 0.96,
    230: 0.97,
    345: 0.98,
    500: 0.99,
    765: 0.99,
    "default": 0.99,
}

assumed_capacity_limits = {
    "coal": 0,
    "default": 5000,
}

assumed_fuel_share_of_gencost = 0.7

assumed_ages_by_type = {
    "hydro": 60,
    "coal": 40,
    "nuclear": 40,
    "default": 20,
}

baseload_types = {"coal", "nuclear"}
variable_types = {"hydro", "solar", "wind", "wind_offshore"}
