#!/usr/bin/env python
# encoding: utf-8

"""
fmplayer.cli
============

CLI interface for FM Player.
"""

import click
import gevent
import logging
import urlparse

from gevent import monkey
from fmplayer.player import Player
from fmplayer.events import EventHandler, event_watcher, queue_watcher
from redis import StrictRedis


monkey.patch_all()

LOG_FORMAT = "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s"


logger = logging.getLogger('fmplayer')
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(LOG_FORMAT))
logger.addHandler(handler)


@click.option(
    '--log-level',
    '-l',
    type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']),
    default='ERROR')
@click.option('--log-file', '-f')
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
    type=click.Choice(['alsa', 'fake']))
@click.command()
def player(*args, **kwargs):
    """FM Player is the thisissoon.fm Player software.
    """

    logfile = kwargs.pop('log_file')
    if logfile is not None:
        handler = logging.FileHandler(filename=logfile)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)

    logger.setLevel(logging.getLevelName(kwargs.pop('log_level')))
    logger.info('Starting...')

    # Channel to listen for events
    channel = kwargs.pop('redis_channel')

    # Redis Connection
    uri = urlparse.urlparse(kwargs.pop('redis_uri'))
    redis = StrictRedis(
        host=uri.hostname,
        port=uri.port,
        password=uri.password,
        db=kwargs.pop('redis_db'))

    # Blocks until Login is complete
    logger.debug('Creating Playing')
    player = Player(
        kwargs.pop('spotify_user'),
        kwargs.pop('spotify_pass'),
        kwargs.pop('spotify_key'),
        kwargs.pop('audio_sink'))

    # Create Handler Instance
    handler = EventHandler(redis, player, channel)
    handler.set_volume({'volume': 80})  # Default volume
    handler.set_mute({'mute': False})  # Default mute off

    # Threads - Queue and Event Watcher
    threads = [
        gevent.spawn(event_watcher, redis, player, handler),
        gevent.spawn(queue_watcher, redis, handler),
    ]

    # Run
    gevent.joinall(threads)


def run():
    """ Main run command used for the entry point.
    """

    player(auto_envvar_prefix='FM_PLAYER')


if __name__ == '__main__':
    run()
