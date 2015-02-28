#!/usr/bin/env python
# encoding: utf-8

"""
fmplayer.cli
============

CLI interface for FM Player.
"""

import click

from fmplayer.player import Player


@click.group()
def cli():
    """FM Player is the thisissoon.fm Player software.
    """

    pass


@cli.command()
def play():
    """ Start the Player
    """

    Player()


if __name__ == '__main__':
    cli()
