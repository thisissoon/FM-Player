#!/usr/bin/env python
# encoding: utf-8

"""
fmplayer.cli
============

CLI interface for FM Player.
"""

import click
import logging

from fmplayer.player import Player


@click.group()
@click.option(
    '--log-level',
    '-l',
    type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']),
    default='ERROR')
@click.pass_context
def cli(ctx, log_level):
    """FM Player is the thisissoon.fm Player software.
    """

    ctx.obj['LOG_LEVEL'] = logging.getLevelName(log_level)
    click.echo('Log Level: {0}'.format(log_level))


@cli.command()
@click.pass_context
def play(ctx):
    """ Start the Player
    """

    Player()


if __name__ == '__main__':
    cli()
