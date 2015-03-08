#!/usr/bin/env python
# encoding: utf-8

"""
fmplayer.cli
============

CLI interface for FM Player.
"""

import click

from fmplayer.player import Player


@click.option(
    '--log-level',
    '-l',
    type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']),
    default='ERROR')
@click.option(
    '--spotify-user',
    '-u',
    help='Spotify user name',
    required=True)
@click.option(
    '--spotify-pass',
    '-p',
    help='Spotify password',
    required=True)
@click.option(
    '--spotify-key',
    '-k',
    help='Path to Spotify API key',
    required=True)
@click.option(
    '--redis-uri',
    '-r',
    help='e.g: redis://localhost:6379/',
    default='redis://localhost:6379/')
@click.option(
    '--redis-channel',
    '-c',
    help='Channel to listen on for events',
    required=True)
@click.option(
    '--redis-db',
    '-d',
    help='Redis DB to connect too',
    required=True)
@click.option(
    '--audio-sink',
    '-s',
    type=click.Choice(['portaudio', 'alsa', 'fake']))
@click.command()
def player(*args, **kwargs):
    """FM Player is the thisissoon.fm Player software.
    """

    Player(*args, **kwargs)


def run():
    """ Main run command used for the entry point.
    """

    player(auto_envvar_prefix='FM_PLAYER')


if __name__ == '__main__':
    run()
