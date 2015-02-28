#!/usr/bin/env python
# encoding: utf-8

"""
fmplayer.player
===============

This module handles playing the music.
"""

import json
import logging
import os
import redis
import spotify
import sys
import threading


LOG_FORMAT = "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s"

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(LOG_FORMAT))
logger.addHandler(handler)


class Player(object):

    def __init__(self, log_level='ERROR'):
        logger.setLevel(logging.getLevelName(log_level))
        logger.debug('Starting PLayer')

        self.config = spotify.Config()
        self.config.load_application_key_file(
            os.environ.get('SPOTIFY_KEY_PATH'))
        self.config.dont_save_metadata_for_playlists = True
        self.config.initially_unload_playlists = True

        self.session = spotify.Session(self.config)

        self.loop = spotify.EventLoop(self.session)
        self.loop.start()

        self.audio = spotify.PortAudioSink(self.session)

        self.session.on(
            spotify.SessionEvent.CONNECTION_STATE_UPDATED,
            self.on_connection_state_updated)
        self.session.on(
            spotify.SessionEvent.END_OF_TRACK,
            self.on_end_of_track)

        self.session.login(
            os.environ.get('SPOTIFY_USER'),
            os.environ.get('SPOTIFY_PASS'))

        self.redis = redis.StrictRedis(
            host=os.environ.get('REDIS_HOST'),
            port=int(os.environ.get('REDIS_PORT')),
            db=int(os.environ.get('REDIS_DB')))

        self.logged_in = threading.Event()
        self.end_of_track = threading.Event()
        self.logged_in.wait()

        self.listen()

    def listen(self):
        pubsub = self.redis.pubsub()
        pubsub.subscribe('fm.player')

        while True:
            for item in pubsub.listen():
                if item.get('type') == 'message':
                    data = json.loads(item.get('data'))
                    if data['event'] == 'pause':
                        self.pause()
                    if data['event'] == 'resume':
                        self.resume()
                    if data['event'] == 'stop':
                        self.stop()

    def play(self, uri):
        logger.info('Playing: {0}'.format(uri))
        track = self.session.get_track(uri).load()

        self.session.player.load(track)
        self.session.player.play()

    def pause(self):
        if self.session.player.state == spotify.PlayerState.PLAYING:
            logger.info('Pausing playback')
            self.session.player.pause()

    def resume(self):
        if self.session.player.state == spotify.PlayerState.PAUSED:
            logger.info('Resuming playback')
            self.session.player.play()

    def stop(self):
        if self.session.player.state != spotify.PlayerState.UNLOADED:
            logger.info('Stopping playback')
            self.session.player.unload()

    def watch_playlist(self):
        if self.session.player.state == spotify.PlayerState.UNLOADED:
            logger.debug('Watching playlist')
            while True:
                if self.redis.llen('playlist') > 0:
                    logger.debug('Playlist not empty - stopped watching')
                    self.play(self.redis.lpop('playlist'))
                    return

    def on_connection_state_updated(self, session):
        if session.connection.state is spotify.ConnectionState.LOGGED_IN:
            logger.info('Logged In to Spotify')
            self.logged_in.set()

            if self.redis.llen('playlist') > 0:
                self.play(self.redis.lpop('playlist'))
            else:
                logger.debug('Playlist Empty')
                self.watch_playlist()

    def on_end_of_track(self, *agrs, **kwargs):
        logger.info('End of Track')
        self.session.player.unload()
        if self.redis.llen('playlist') > 0:
            self.play(self.redis.lpop('playlist'))
        else:
            logger.debug('Playlist Empty')
            self.watch_playlist()


if __name__ == '__main__':
    try:
        Player()
    except KeyboardInterrupt:
        sys.exit()
