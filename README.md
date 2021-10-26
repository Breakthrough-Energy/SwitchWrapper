# SwitchWrapper

## Purpose

SwitchWrapper is a tool to interface between the Switch capacity expansion model and the
PowerSimData data management tool.
It can use PowerSimData data structures to create inputs for running Switch, and it can
interpret the decisions made by Switch back to PowerSimData data structures.

## Installation

SwitchWrapper can be installed like any other python package.
The most universal way is to run `pip install .` from the command line at the root of
the SwitchWrapper repository.
The default behavior of other package management tools (`pipenv`, `conda`, `poetry`)
should work as well.

## Usage

### Preparing inputs to Switch

The main user-facing function to prepare Switch inputs is
`switchwrapper.prepare.prepare_inputs`. Required inputs are:
- A PowerSimData `Grid` object.
- A dictionary of profiles for demand/hydro/solar/wind, where each profile is a pandas
DataFrame.
- A pandas DataFrame containing information on the timepoints for use with Switch.
- A mapping of timestamps of input profiles to timepoints for Switch.
- A location to store the prepared files.

Optional inputs are:
- A set of buses at which storage investments can be made. By default, no buses are
enabled for energy storage investments.

Running this function returns no output, but all required files to launch switch will be
created.

For full documentation, see the
[function docstring](https://github.com/Breakthrough-Energy/SwitchWrapper/blob/develop/switchwrapper/prepare.py).

### Launching Switch

The main user-facing function to launch Switch is `switchwrapper.call.launch_switch`.
Required inputs are:
- A location to read prepared files from. This is the same location used in the input
preparation.

Optional inputs are:
- The solver to use. By default, this is `gurobi`.
- The suffixes to query the solver for. By default, this is `dual`.
- The level of verbosity of Switch. By default, `verbose` is `True`.

Running this function returns no output, but Switch will be launched.

For full documentation, see the
[function docstring](https://github.com/Breakthrough-Energy/SwitchWrapper/blob/develop/switchwrapper/call.py).

### Interpreting Switch Results

The main user-facing function to interpret Switch results is
`switchwrapper.switch_extract.get_output_scenarios`. Required inputs are:
- A location to read input and output files from. This is the same location used in the
input preparation and the launch step.

Running this function returns a dictionary, where each key is an investment year
specified via the inputs and each value is a PowerSimData Scenario object representing
the Grid of that year and the input/output time-series for that year _as interpreted by
the temporal reduction specified via the inputs_.

For full documentation, see the
[function docstring](https://github.com/Breakthrough-Energy/SwitchWrapper/blob/develop/switchwrapper/switch_extract.py).

## Contributing

If something is not working as expected, please fill out a
[bug report](https://github.com/Breakthrough-Energy/SwitchWrapper/issues/new?labels=bug&template=bug_report.md).

If the package does not have a feature that you think it should, please fill out a
[feature request](https://github.com/Breakthrough-Energy/SwitchWrapper/issues/new?labels=feature+request&template=feature_request.md).
