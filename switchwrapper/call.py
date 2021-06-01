import os
import subprocess
import sys


def launch_switch(input_folder, solver="gurobi", suffixes="dual", verbose=True):
    """Launch switch using a folder of prepared input files.

    :param str input_folder: location containing the 'modules.txt' file and a subfolder
        'inputs' containing inputs CSVs.
    :param str solver: the solver for Switch to use. If None, use GLPK (Switch default).
    :param str suffixes: which additional information for Pyomo to collect from the
        solver. If None, use the Switch default (none).
    :param bool verbose: whether to pass the '--verbose' flag to Switch, to print more
        information about the process of building and solving the model.
    :raises TypeError: if ``input_folder`` is not a str, if ``solver`` or ``suffixes``
        are not str/None, or if ``verbose`` is not bool.
    :raises ValueError: if ``input_folder`` does not point to a valid directory, or if
        this directory does not contain a sub-directory named 'inputs'.
    """
    # Validate inputs
    if not isinstance(input_folder, str):
        raise TypeError(f"input_folder must be a str, got {type(input_folder)}")
    if not os.path.isdir(input_folder):
        abspath = os.path.abspath(input_folder)
        raise ValueError(f"input_folder must be a valid directory, got {abspath}")
    inputs_subfolder = os.path.join(input_folder, "inputs")
    if not os.path.isdir(inputs_subfolder):
        raise ValueError("input_folder must contain a subdirectory named 'inputs'")
    modules_filepath = os.path.join(input_folder, "modules.txt")
    if not os.path.isfile(modules_filepath):
        raise ValueError("input_folder must contain a file named 'modules.txt'")
    if not isinstance(solver, str) and solver is not None:
        raise TypeError("solver must be a str or None")
    if not isinstance(suffixes, str) and suffixes is not None:
        raise TypeError("suffixes must be a str or None")
    if not isinstance(verbose, bool):
        raise TypeError("verbose must be bool")

    # Construct subprocess call, starting with user-provided inputs
    cmd = ["switch", "solve"]
    if solver is not None:
        cmd += ["--solver", solver]
    if suffixes is not None:
        cmd += ["--suffixes", suffixes]
    if verbose:
        cmd += ["--verbose"]

    # Then add inferred inputs about the folders
    outputs_subfolder = os.path.join(input_folder, "outputs")
    cmd += ["--inputs-dir", inputs_subfolder]
    cmd += ["--module-list", modules_filepath]
    cmd += ["--outputs-dir", outputs_subfolder]

    # Finally, launch
    subprocess.run(cmd)


if __name__ == "__main__":
    launch_switch(sys.argv[1])
