#!/usr/bin/env python
# encoding: utf-8

"""
fmplayer.cli
============

CLI interface for FM Player.
"""

import click

from fmplayer.player import Player


@click.command()
@click.option(
    '--log-level',
    '-l',
    type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']),
    default='ERROR')
@click.option(
    '--spotify-user',
    '-u',
    envvar='SPOTIFY_USER',
    help='Spotify user name',
    required=True)
@click.option(
    '--spotify-pass',
    '-p',
    envvar='SPOTIFY_PASS',
    help='Spotify password',
    required=True)
@click.option(
    '--spotify-key',
    '-k',
    envvar='SPOTIFY_KEY',
    help='Path to Spotify API key',
    required=True)
@click.option(
    '--redis-uri',
    '-r',
    envvar='REDIS_URI',
    help='e.g: redis://localhost:6379/',
    default='redis://localhost:6379/')
@click.option(
    '--redis-channel',
    '-c',
    envvar='REDIS_CHANNEL',
    help='Channel to listen on for events',
    required=True)
@click.option(
    '--redis-db',
    '-d',
    envvar='REDIS_DB',
    type=int,
    help='Redis DB to connect too',
    required=True)
@click.option(
    '--audio-sink',
    '-s',
    type=click.Choice(['portaudio', 'alsa', 'fake']),
    default='portaudio')
def cli(*args, **kwargs):
    """FM Player is the thisissoon.fm Player software.
    """

    Player(*args, **kwargs)


if __name__ == '__main__':
    cli()
