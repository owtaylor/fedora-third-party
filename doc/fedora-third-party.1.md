% fedora-third-party 1

## NAME
fedora-third-party - manage third-party software repositories

## SYNOPOSIS
**fedora-third-party** [*--verbose* | *-v*] *COMMAND* [*ARGS*]

## DESCRIPTION
The `fedora-third-party` tool is used to manage third-party software
repositories that are distributed with editions of Fedora Linux, but
not enabled unless the user opts-in.

## COMMON OPTIONS
The following options are understood:

**--verbose, v**

Print detailed information about what is being done.

## COMMANDS

The following commands are understood:

### enable [*--config-only*]

Enables third-party repositories. Configured DNF repositories are enabled,
and configured Flatpak remotes are created unless they already exist.

If *--config-only* is specified, existing repositories are not modified,
but the configuration is updated so that newly added repositories will
be enabled when `fedora-third-party refresh` is called.

### disable [*--config-only*]

Disables third-party repositories. Configured DNF repositories are disabled.
Configured Flatpak remotes are disabled, unless:

* the remote previously existed and was not created by fedora-third-party.
* the remote has been modified to remove a filter and the `keep_unfiltered`
  flag is configured for the remote.

The last exception exists because, if a Fedora third-party repository has a
filter (see flatpak-remote-add(1)), this filter will be removed if the
user installs a .flatpakrepo file for the same remote name without a filter.
At this point, the remote is different from what was distributed with the
Fedora edition and should be left untouched.

If *--config-only* is specified, existing repositories are not modified,
but the configuration is updated so that newly added repositories will
not be enabled when `fedora-third-party refresh` is called.

### query [*--quiet* | *-q*]

Prints a human-readable string describing the whether third-party repositories
hae been enabled.

When *--quiet* is specified, no output is printed, and the status is
given by the exit code (0 for enabled, 1 for disabled, 2 for disabled
if no selection has yet been made).

### refresh

Look for newly added third-party repository definitions, and if third-party
repositories are enabled, enable DNF repositories and create Flatpak
remotes.

### list [*-a* | *--all* | *--csv* | *--columns=col1,col2*]

Prints the list of currently configured repositories. By default, the list
will be pretty-printed in tabular form with headers. The *--csv* option can
be used to switch the output to comma-separated-value format without headers.

The columns to be printed can be specified with the *--columns* options.
Currently supported values are `name` for the name of the repository
(which is the same as the DNF repository name or Flatpak remote name)), and
`type` for the type of the repository (either `dnf` or `flatpak`).

*--columns* should always be specified together with *--csv* to
get stable output - the default set of columns may change. With
the current columns, you can assume that the values will
not be quoted.

Flatpak repositories with the `keep_unfiltered` option set are hidden by
default from the list if there is a matching remote without a filter.
*a* or *--all* can be passed to show all repositories.

## CONFIGURATION

Repositories are configured by files in `/usr/lib/fedora-third-party/conf.d`.
All files in this directory ending with `.conf` are read. Each section found
defines a repository that should be controlled by fedora-third-party.

Example of configuration for a DNF repository:

``` ini
[somerepo]
# The DNF repository must match and also be 'somerepo'
type=dnf
```

Example of configuration for a Flatpak remote:

``` ini
[somerepo]
# The Flatpak remote must match and also be 'somerepo'
type=flatpak

# Path to a flatpakrepo file defining the remote. If it's a relative
# path, it will be interpreted relative to the directory where the
# config file is.
flatpakrepo=somerepo.flatpakrepo
# If present, 'fedora-third-party disable' will leave this repository
# untouched if it has been modified to not have a filter, and it will
# also be hidden from the output of 'fedora-third-party list'
keep_unfiltered=yes
```

## FILES

`/usr/lib/fedora-third-party/conf.d` - repository configuration files

`/var/lib/fedora-third-party/state` - current state is stored in this file.

## SEE ALSO
`dnf.conf(5)`, `flatpak(1)`

