# sopel-pypi

A Sopel plugin to show information about linked PyPI packages.

## Installing

Releases are hosted on PyPI, so after installing Sopel, all you need is `pip`:

```bash
$ pip install sopel-pypi
```

## Usage

Just send a link to a package or release:

```irclog
<dgw> https://pypi.org/project/sopel/7.1.9/
<Sopel> [PyPI] sopel 7.1.9 | Author: dgw | Released 2 years, 11 months ago |
        Simple and extensible IRC bot
<dgw> https://pypi.org/project/sopel/ no version this time
<Sopel> [PyPI] sopel 8.0.2 | Author: dgw, Florian Strzelecki, Sean B. Palmer,
        Else Powell, Elad Alfassa, Dimitri Molenaars, Michael Yanovich |
        Released 1 month, 26 days ago | Simple and extensible IRC bot
```

You can also look up packages (optionally, at a specific version) with the
`.pypi` command:

```irclog
<dgw> .pypi sopel-xkcdb
<Sopel> [PyPI] sopel-xkcdb 0.1.0 | Author: dgw | Released 1 day, 2 hours ago |
        XKCDB quotes plugin for Sopel IRC bots |
        https://pypi.org/project/sopel-xkcdb/0.1.0/
<dgw> .pypi sopel 6
<Sopel> [PyPI] sopel 6.0.0 | Author: Edward Powell | Released 9 years, 6 months
        ago | Simple and extendible IRC bot |
        https://pypi.org/project/sopel/6.0.0/
```

Note that specifying an incomplete version number relies on how PyPI chooses to
handle it. The behavior as of April 2025 is to find the earliest non-prerelease
version with that prefix, as shown above.
