#!/usr/bin/env python
# encoding: utf-8

"""




"""

import json
import logging


logger = logging.getLogger('fmplayer')


class EventHandler(object):
    """ Handles events from redis, performing tasks on the player and
    maintaining the player state.
    """

    def __init__(self, redis, player):
        """ Initialises the handler.

        Arguments
        ---------
        redis : obj
            The redis connection instance
        player : obj
            The Spotify player instance
        """

        self.redis = redis
        self.player = player

    def pause(self, data):
        """ Handles the pause event. Calls the ``pause`` method on the player.
        Also sets the player paused state to 1 (True).
        """

        self.player.pause()
        self.redis.set('fm:player:paused', 1)

    def resume(self, data):
        """ Handles the resume event. Calls the ``resume`` method on the player.
        Also sets the player paused state to 0 (False).
        """

        self.player.resume()
        self.redis.set('fm:player:paused', 0)

    def set_volume(self, data):
        """ Handles the volume set event. Sets the players volume and sets
        the player volume state to the current player volume level.
        """

        volume = data.get('volume')
        if volume is not None:
            self.player.set_volume(volume)
            self.redis.set('fm:player:volume', self.player.get_volume())

    def set_mute(self, data):
        """ Handles the mute event. Sets the player mute state and also sets
        the mute player state to either True (1) or False (0).
        """

        mute = data.get('mute')
        if mute is not None:
            self.player.set_mute(mute)
            self.redis.set('fm:player:mute', int(self.player.get_mute()))


def event_watcher(redis, player, channel):
    """ This method watches the Redis PubSub channel for events. Once a valid
    event is fired it will execute the desired functionality for that event.

    Arguments
    ---------
    redis : obj
        Redis connection instance
    player : str
        The Spotify player instance
    channel : str
        The channel to listen on
    """

    logger.info('Starting Redis Event Loop')

    handler = EventHandler(redis, player)

    pubsub = redis.pubsub()
    pubsub.subscribe(channel)

    events = {
        'pause': handler.pause,
        'resume': handler.resume,
        'volume': handler.set_volume,
        'mute': handler.set_mute,
    }

    for item in pubsub.listen():
        logger.debug('Got Event: {0}'.format(item))
        if item.get('type') == 'message':
            data = json.loads(item.get('data'))
            event = data.pop('event')
            if event in events:
                logger.debug('Fire: {0}'.format(event))
                function = events.get(event)
                function(data)
