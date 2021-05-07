financial_parameters = {
    "discount_rate": 0.079,
    "interest_rate": 0.029,
}

fuels = ["Coal", "NaturalGas", "Uranium"]

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
