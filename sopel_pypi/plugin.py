"""sopel-pypi

A Sopel plugin to show information about linked PyPI Packages.

Copyright (c) 2020-2025 dgw

Licensed under the Eiffel Forum License 2
"""
from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parseaddr
import itertools

import requests

from sopel import plugin, tools


PYPI_API_TEMPLATE = 'https://pypi.org/pypi/{}/json'


class PyPIError(Exception):
    pass


class NoSuchVersionError(PyPIError):
    pass


def get_pypi_info(package, version=None):
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
            .format(package, '(any)' if version is None else version))
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise PyPIError("HTTP error: " + e.args[0])
    try:
        data = r.json()
    except ValueError:
        raise PyPIError("ValueError when decoding: " + r.content)

    return data


def get_release_date(file_list):
    """Given a single release dict, figure out when it was released."""
    most_recent = None
    for file in file_list:
        if not most_recent or file['upload_time'] > most_recent:
            most_recent = file['upload_time']

    # I wish strptime() would allow just saying "hey, I know the offset" out of
    # band from the input string
    return datetime.strptime(most_recent + 'Z', '%Y-%m-%dT%H:%M:%S%z')


def merge_names_and_emails(names, emails):
    """Format a string combining data from the ``names`` & ``emails`` fields.

    Either field can be ``None``; if both are empty, the function will safely
    fall back to ``'(unknown name)'``.
    """
    names_list = [a.strip() for a in names.split(', ')] if names else []
    emails_list = []

    if emails:
        for email in emails.split(', '):
            # trust the metadata to correctly format email entries
            # (parseaddr() is in strict mode by default)
            name, address = parseaddr(email)
            if name:
                emails_list.append(name)
            else:
                # if the name is empty, assume it's an email address, since
                # Python metadata puts bare names in the field without `_email`
                emails_list.append(address)

    combined = set(itertools.chain(names_list, emails_list))

    return ', '.join(combined) or '(unknown name)'


def format_pypi_info(data):
    """Format a PyPI project data dict for output."""
    template = "{name} {version} | Author: {author} | Released {release_relative} | {summary}"

    name = data['info']['name']
    version = data['info']['version']
    author = merge_names_and_emails(
        data['info']['author'],
        data['info']['author_email'],
    )
    summary = data['info']['summary']
    release_date = get_release_date(data['urls'])
    release_relative = tools.time.seconds_to_human(datetime.now(timezone.utc) - release_date)

    return template.format(
        name=name,
        version=version,
        author=author,
        release_relative=release_relative,
        summary=summary,
    )


def say_info(bot, package, version, commanded=False):
    """Fetch, format, and output the package info to IRC."""
    try:
        data = get_pypi_info(package, version)
    except NoSuchVersionError as e:
        if commanded:
            bot.say(e.args[0])
        return
    except PyPIError:
        if commanded:
            bot.say("Sorry, there was an error accessing PyPI. Please try again later.")
        return

    message = format_pypi_info(data)
    if commanded:
        # always use specific release so link targets won't change when clicked in old logs
        message += " | {}".format(data['info']['release_url'])

    bot.say("[PyPI] " + message, max_messages=2)


@plugin.url(r'https?:\/\/pypi\.(?:org|io)\/p(?:roject)?\/([\w\-\.]+)(?:\/([\w\d\.\-]+))?\/?')
def pypi_link(bot, trigger):
    """Show information about a PyPI link in the chat."""
    package = trigger.group(1)
    version = trigger.group(2)

    say_info(bot, package, version)


@plugin.commands('pypi')
@plugin.example('.pypi sopel 7.0.0', user_help=True)
@plugin.example('.pypi sopel', user_help=True)
def pypi_command(bot, trigger):
    """Show information about the given PyPI package."""
    package = trigger.group(3)
    version = trigger.group(4)

    say_info(bot, package, version, commanded=True)
