from switchwrapper.helpers import match_variables


def construct_grids_from_switch_results(grid, results):
    """Using the original Grid and Switch expansion results, construct expanded Grid(s).
    :param powersimdata.input.grid.Grid grid: Grid instance.
    :param pyomo.opt.results.results_.SolverResults results: results from Switch.
    :return: (*dict*) -- keys are integers representing the expansion year, values are
        Grid objects.
    """
    build_gen, build_tx = extract_build_decisions(results)


def extract_build_decisions(results):
    """Parse the results of the decision variables within Switch results.
    :param pyomo.opt.results.results_.SolverResults results: results from Switch.
    :return: (*tuple*) --
        pandas.DataFrame representing the generator build decisions. Columns are:
            'year', 'gen_id' (Switch indexing), and 'capacity'. There is no meaningful
            index.
        pandas.DataFrame representing the transmission build decisions. Columns are:
            'year', 'tx_id' (Switch indexing), and 'capacity'. There is no meaningful
            index.
    """
    gen_pattern = r"BuildGen\[(?P<gen_id>[a-z0-9]+),(?P<year>[0-9]+)\]"
    tx_pattern = r"BuildTx\[(?P<tx_id>[a-z0-9]+),(?P<year>[0-9]+)\]"

    variables = results.solution._list[0]["Variable"]
    build_gen = match_variables(variables, gen_pattern, ["year", "gen_id"])
    build_tx = match_variables(variables, tx_pattern, ["year", "tx_id"])

    return build_gen, build_tx
