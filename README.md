# FAROS: A Framework for Benchmarking and Analysis of Compiler Optimization

FAROS is an extensible framework to automate and structure the analysis 
of compiler optimizations of OpenMP programs. FAROS provides a generic 
configuration interface to profile and analyze OpenMP applications with 
their native build configurations.

## Description and usage

This repo contains a benchmark harness to fetch, build, and run programs
with different compilation options for analyzing the impact of
compilation on performance. The usecase is contrasting OpenMP compilation
with its serial elision to understand performance differences due to
different compilation.


### Harness script

The harness script in python, named benchmark.py, takes as input a YAML
configuration file and a set of options to build and run programs
described in that configuration. You can see below the help
output describing possible options. The configuration file input is set
with the `-i, --input` argument. There are three different actions the
harness performs:
1. fetch sources, with the option `-f, --fetch`,
fetches the program sources from the specified repositories;
2. build programs, with
the option `-b, --build`, builds the selected program using the specified
compilation options in the configuration, also fetching if needed;
3. generate reports, with the option `-g, --generate`, generates compilation reports
by combining optimization remarks for different compilation
configurations, creating remark diff files between them, from all the
sources of an application to a single file;
4. run tests, with the option `-r,--run` and a following argument on how many repetitions to perform, that
runs the executable with the specified input, repeating up to the number
of repetitions set.

The flags can be individually set doing multiple runs of the harness, or
combined to perform multiple actions in a single run -- fetching takes
precedence over building, building over generating reports and running.
The user select the list of programs to operate usin `-p,--programs`
followed by individual program names or the keyword `all` for all the
programs specified in the configuration input.  Alternatively, the user
may select the list of programs by provide a tag list with `-t,--tags`
that matches tags for each program specified in the configuration.
Also, the harness has a dry run option, `-d,--dry-run`, that prints what
actions would be performed without actually performing them.

Below is the output when running help, `-h, --help` on the harness
script:
```
Benchmark and analyze programs compiled with different compilation options.

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, --input INPUT
                        configuration YAML input file for programs
  -f, --fetch           fetch program repos (without building)
  -b, --build           build programs (will fetch too)
  -r RUN, --run RUN     run <repetitions>
  -g, --generate        generate compilation reports
  -p PROGRAMS [PROGRAMS ...], --programs PROGRAMS [PROGRAMS ...]
                        programs to run from the config
  -t TAGS [TAGS ...], --tags TAGS [TAGS ...]
                        tagged program to use from the config
  -s, --stats           show run statistics
  -d, --dry-run         enable dry run
```
The harness creates four extra directories for its
operation when building and running:
1. the directory `repos` to download the benchmark application
    specified in the configuration;
2. the directory `bin` to store the generated executable from
    building to run them;
3. the directory `reports`, where it store compilation
    reports, including optimization remarks;
4. the directory `results` to store profiling results, which
    contain execution times from running different built configurations and
    inputs.

### YAML configuration input

Configuring YAML creates is a hierarchy of keys for each program to
include that prescribe actions for the harness script. We describe those
keys here. For a working example please see `config.yaml` in the repo,
which iincludes configuration for 39 HPC programs including proxy/mini
applications, NAS and Rodinia kernels, and the open-source large
application GROMACS.  The root of the hierarchy is a user-chosen,
descriptive name per program configuration.  The harness creates a
sub-directory matching the name of this root key under `bin` to store
executables

The key `fetch` contains the shell command to fetch the
application code, for example cloning from a GitHub repo. Note that the
fetching command can include also a patching file, if needed, provided
by the user. In this repo we provide patch files for programs in
`config.yaml` undr the directory `patches`.  For example, for some
programs, we apply a patch to guard calls to OpenMP runtime functions
using the standard approach of enabling those calls within `#ifdef OPENMP
... endif` preprocessor directives.

The key `tags` sets a list of user-defined tags which can be used by the
harness to include programs when performing its operation.

The key `build_dir` specifies the directory to build the application, so
harness changes to this directory to execute the build commands
specified under the key build. There is a different sub-key for each
different compilation specification, denoted by a user-provided
identifier.  The harness creates different sub-directories under
`bin/<program>`for each different compilation configurations

The key `copy` specifies a list of files or directories that the harness
copies out to those sub-directories. The list contains the executable
file and possibly any input files needed for executing, if the user
desires to have self-contained execution in `bin` by avoiding referring to
input files in the directory repos -- this is useful for
relocating the directory bins without needing to copy over
repos.

Further, the key `run` specifies the command to
execute, which is typically the executable binary of the application,
prepended with any environment variables to set.

Moreover, the key `input` specifies the input arguments
for the application in the run command.

The key `measure`
specifies a regular expression to match in the application's executable
output to capture the desired measure of performance, such as execution
time or some other Figure of Merit (FoM). If the value of the key
measure is empty, the harness measures end-to-end, wall clock  execution
time from launching the application to its end, using python's
time module.

Lastly, the key `clean` specifies the commands that harness executes to
clean the repo for building a different compilation configuration.

## Contributing
To contribute to this repo please send a [pull
request](https://help.github.com/articles/using-pull-requests/) on the
develop branch of this repo.

## Authors

This code was created by Giorgis Georgakoudis (LLNL),
georgakoudis1@llnl.gov, assisted with technical design input from
Ignacio Laguna (LLNL), Tom Scogland, and Johannes Doerfert (ANL).

### Citing FAROS

Please cite the following paper: 

* Georgakoudis G., Doerfert J., Laguna I., Scogland T.R.W. (2020) [FAROS: A
  Framework to Analyze OpenMP Compilation Through Benchmarking and Compiler
  Optimization
  Analysis](https://link.springer.com/chapter/10.1007/978-3-030-58144-2_1). In: Milfeld K., de Supinski B., Koesterke L.,
  Klinkenberg J. (eds) OpenMP: Portable Multi-Level Parallelism on Modern
  Systems. IWOMP 2020. Lecture Notes in Computer Science, vol 12295. Springer,
  Cham. https://doi.org/10.1007/978-3-030-58144-2_1

## License

This repo is distributed under the terms of the Apache License (Version
2.0) with LLVM exceptions. Other software that is part of this
repository may be under a different license, documented by the file
LICENSE in its sub-directory.

All new contributions to this repo must be under the Apache License (Version 2.0) with LLVM exceptions.

See files [LICENSE](LICENSE) and [NOTICE](NOTICE) for more information.

SPDX License Identifier: "Apache-2.0 WITH LLVM-exception"

LLNL-CODE-813267
