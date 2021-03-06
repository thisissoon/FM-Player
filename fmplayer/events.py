#!/usr/bin/env python
# encoding: utf-8

"""
fmplayer.events
===============

Event handler classes / helpers.
"""

import gevent
import json
import logging
import random

from fmplayer.player import STOP_EVENT


logger = logging.getLogger('fmplayer')


PLAYLIST_KEY = 'fm:player:queue'


class EventHandler(object):
    """ Handles events from redis, performing tasks on the player and
    maintaining the player state.
    """

    def __init__(self, redis, player, channel):
        """ Initialises the handler.

        Arguments
        ---------
        redis : obj
            The redis connection instance
        player : obj
            The Spotify player instance
        channel : str
            The channel to listen on
        """

        self.redis = redis
        self.player = player
        self.channel = channel

    def play(self, uri, user):
        """ Handles the play event, this is called directly by the player
        queue watcher.

        Arguments
        ---------
        uri : str
            The Spotify URI (spotify:track:1234)(
        user : str
            The User Primary Key
        """

        # Publish the Play event - Just the URI needed
        event = json.dumps({
            'event': 'play',
            'uri': uri,
            'user': user
        })

        self.redis.publish(self.channel, event)
        logger.debug('Play Event: {0}'.format(event))

        # Set the current track - needs to hold the uri and user
        self.redis.set('fm:player:current', json.dumps({
            'uri': uri,
            'user': user
        }))

        # Start playing the track
        self.player.play(uri)

    def stop(self, data):
        """ Handles the stop event. This triggered when a track should be
        skipped during playback and the next track should be played.
        """

        logger.debug('Stop current track')
        self.player.stop()

    def end(self, uri):
        """ Handles the end event. This is triggered directly by the queue
        watcher.
        """

        logger.debug('Remove current track')
        current = json.loads(self.redis.get('fm:player:current'))
        self.redis.delete('fm:player:current')
        logger.debug('Publish end event')
        self.redis.publish(self.channel, json.dumps({
            'event': 'end',
            'uri': uri,
            'user': current['user']
        }))

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
            logger.debug('Set Volume: {0}'.format(volume))
            self.player.set_volume(volume)
            self.redis.set('fm:player:volume', volume)
            self.redis.publish(self.channel, json.dumps({
                'event': 'volume_changed',
                'volume': volume
            }))

    def set_mute(self, data):
        """ Handles the mute event. Sets the player mute state and also sets
        the mute player state to either True (1) or False (0).
        """

        mute = data.get('mute')
        if mute is not None:
            logger.debug('Set Mute: {0}'.format(mute))
            self.player.set_mute(mute)
            self.redis.set('fm:player:mute', int(mute))
            self.redis.publish(self.channel, json.dumps({
                'event': 'mute_changed',
                'mute': mute
            }))


def event_watcher(redis, player, handler):
    """ This method watches the Redis PubSub channel for events. Once a valid
    event is fired it will execute the desired functionality for that event.

    Arguments
    ---------
    redis : obj
        Redis connection instance
    player : str
        The Spotify player instance
    hadnler : str
        The event handler instance
    """

    logger.info('Starting Redis Event Loop')

    pubsub = redis.pubsub()
    pubsub.subscribe(handler.channel)

    events = {
        'pause': handler.pause,
        'resume': handler.resume,
        'stop': handler.stop,
        'set_volume': handler.set_volume,
        'set_mute': handler.set_mute,
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


def queue_watcher(redis, handler):
    """ This method watches the playlist queue for tracks, once the queue has
    a track the player will be told to play the track, this will cause the
    method to block until the track has completed playing the track. Once the
    track is finished we will go round again.

    Arguments
    ---------
    redis : EventHandler, obj
        Redis connection instance
    handler : str
        Event handler instance
    """

    # If we have a track in current play that first before watching the
    # playlist
    current = redis.get('fm:player:current')
    logger.debug(current)
    if current is not None:
        logger.info('Playing current track before watching playlist')
        current = json.loads(current)
        handler.play(current['uri'], current['user'])
        STOP_EVENT.wait()

    logger.info('Watching Playlist')

    while True:
        if redis.llen(PLAYLIST_KEY) > 0:
            data = json.loads(redis.lpop(PLAYLIST_KEY))
            uri = data['uri']
            user = data['user']
            logger.debug('Track popped of list: {0}'.format(uri))
            handler.play(uri, user)
            logger.debug('Waiting for {0} to Finish'.format(uri))
            STOP_EVENT.wait()
            logger.debug('Fire end event')
            handler.end(uri)

        gevent.sleep(random.randint(0, 2) * 0.001)
