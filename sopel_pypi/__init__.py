# coding=utf8
"""sopel-pypi

A Sopel plugin to show information about linked PyPI Packages.
"""
from __future__ import unicode_literals, absolute_import, division, print_function

from datetime import datetime
import enum
import xmlrpc.client

import requests

from sopel import module, tools


PYPI_API_TEMPLATE = 'https://pypi.org/pypi/{}/json'


class PyPIError(Exception):
    pass


class NoSuchVersionError(PyPIError):
    pass


class ReturnCode(enum.Enum):
    FAILED = enum.auto()
    NOT_FOUND = enum.auto()


def get_pypi_info(package, version):
    """Get the package info from PyPI, and handle network errors."""
    try:
        r = requests.get(PYPI_API_TEMPLATE.format((package + '/' + version) if version else package))
    except requests.exceptions.ConnectTimeout:
        raise PyPIError("Connection timed out.")
    except requests.exceptions.ConnectionError:
        raise PyPIError("Couldn't connect to server.")
    except requests.exceptions.ReadTimeout:
        raise PyPIError("Server took too long to send data.")
    if r.status_code == 404:
        raise NoSuchVersionError(
            "PyPI couldn't find {} version {}. Are you sure it exists?"
            .format(package, version))
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise PyPIError("HTTP error: " + e.args[0])
    try:
        data = r.json()
    except ValueError:
        raise PyPIError("ValueError when decoding: " + r.content)

    return data


def get_release_date(release):
    """Given a single release dict, figure out when it was released."""
    most_recent = None
    for file in release:
        if not most_recent or file['upload_time'] > most_recent:
            most_recent = file['upload_time']

    return datetime.strptime(most_recent, '%Y-%m-%dT%H:%M:%S')


def format_pypi_info(data):
    """Format a PyPI project data dict for output."""
    template = "{name} {version} | Author: {author} | Released {release_relative} | {summary}"

    name = data['info']['name']
    version = data['info']['version']
    author = data['info']['author']
    summary = data['info']['summary']
    release_date = get_release_date(data['releases'][version])
    release_relative = tools.time.seconds_to_human(datetime.utcnow() - release_date)

    return template.format(
        name=name,
        version=version,
        author=author,
        release_relative=release_relative,
        summary=summary,
    )


def search_pypi(query):
    """Query PyPI's XML-RPC API for relevant packages."""
    # Making the XML-RPC client a global breaks Sopel's plugin loading;
    # see https://github.com/sopel-irc/sopel/issues/1931
    # Using bot.memory would require an extra `bot` param here.
    # Just take the slight perf hit of creating the object every time.
    pypi = xmlrpc.client.ServerProxy('https://pypi.org/pypi')
    return pypi.search({'name': query, 'summary': query}, 'or')


def say_info(bot, package, version, commanded=False):
    """Fetch, format, and output the package info to IRC."""
    try:
        data = get_pypi_info(package, version)
    except NoSuchVersionError as e:
        return ReturnCode.NOT_FOUND, e.args[0]
    except PyPIError:
        return ReturnCode.FAILED, "Sorry, there was an error accessing PyPI. Please try again later."

    message = format_pypi_info(data)
    if commanded:
        # always use specific release so link targets won't change when clicked in old logs
        message += " | {}".format(data['info']['release_url'])

    bot.say("[PyPI] " + message, max_messages=2)


@module.url(r'https?:\/\/pypi\.org\/p(?:roject)?\/([\w\-\.]+)(?:\/([\w\d\.\-]+))?\/?')
def pypi_link(bot, trigger, match):
    """Show information about a PyPI link in the chat."""
    package = match.group(1)
    version = match.group(2)

    say_info(bot, package, version)


@module.commands('pypi')
@module.example('.pypi sopel 7.0.0', user_help=True)
@module.example('.pypi sopel', user_help=True)
def pypi_command(bot, trigger):
    """Show information about the given PyPI package."""
    package = trigger.group(3)
    version = trigger.group(4)

    if not trigger.group(5):
        # If trigger group 5 exists, the user's input was too long for a
        # standard package query with optional version, and we shouldn't
        # even try to do anything but search.
        ret, msg = say_info(bot, package, version, commanded=True)

        if ret is None:
            return  # successful output

        if ret == ReturnCode.FAILED:
            # no reason to fall back on search if PyPI appears to be down
            bot.say(msg)
            return

        if version and ret == ReturnCode.NOT_FOUND and all(c in '1234567890.' for c in version):
            # Don't fall back on search for NOT_FOUND with a version number
            bot.say(msg)
            return

    # Fall back on search if the direct lookup returned no results
    hits = search_pypi(trigger.group(2))
    if hits:
        package = hits[0]
        say_info(bot, package['name'], package['version'], commanded=True)
