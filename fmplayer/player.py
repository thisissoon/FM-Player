#!/usr/bin/env python
# encoding: utf-8

"""
fmplayer.player
===============

This module handles playing the music.
"""

import json
import logging
import spotify
import threading
import urlparse

from redis import StrictRedis


LOG_FORMAT = "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s"

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(LOG_FORMAT))
logger.addHandler(handler)


PLAYLIST_KEY = 'fm:player:state:playlist'
PAUSED_KEY = 'fm:player:state:paused'
PLAYING_KEY = 'fm:player:state:playing'


class FakeSink(spotify.sink.Sink):
    """ A fake audio sink, doesen't pass the audio to a device, this is for
    development purposes only.
    """

    def __init__(self, session):
        logger.info('Running Fake Audio Sink - There will be no audio output')
        self._session = session
        self.on()

    def _on_music_delivery(self, session, audio_format, frames, num_frames):
        return num_frames


class Player(object):

    def __init__(
            self,
            spotify_user,
            spotify_pass,
            spotify_key,
            redis_uri,
            redis_db,
            redis_channel,
            log_level='ERROR',
            audio_sink='portaudio'):

        logger.setLevel(logging.getLevelName(log_level))
        logger.debug('Starting PLayer')

        self.config = spotify.Config()
        self.config.load_application_key_file(spotify_key)
        self.config.dont_save_metadata_for_playlists = True
        self.config.initially_unload_playlists = True

        self.session = spotify.Session(self.config)

        self.loop = spotify.EventLoop(self.session)
        self.loop.start()

        self.audio = {
            'portaudio': spotify.PortAudioSink,
            'alsa': spotify.AlsaSink,
            'fake': FakeSink
        }.get(audio_sink)(self.session)

        self.session.on(
            spotify.SessionEvent.CONNECTION_STATE_UPDATED,
            self.on_connection_state_updated)
        self.session.on(
            spotify.SessionEvent.END_OF_TRACK,
            self.on_end_of_track)

        self.session.login(spotify_user, spotify_pass)

        uri = urlparse.urlparse(redis_uri)
        self.redis = StrictRedis(
            host=uri.hostname,
            port=uri.port,
            password=uri.password,
            db=redis_db)

        self.logged_in = threading.Event()
        self.end_of_track = threading.Event()
        self.logged_in.wait()

        self.listen()

    def listen(self):
        pubsub = self.redis.pubsub()
        pubsub.subscribe('fm:player:channel')

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
                    if data['event'] == 'add':
                        self.add(data['track']['spotify_uri'])

    def play(self, uri):
        logger.info('Playing: {0}'.format(uri))

        try:
            track = self.session.get_track(uri).load()
            self.session.player.load(track)
            self.session.player.play()
            self.redis.set(PLAYING_KEY, uri)
        except (spotify.error.LibError, ValueError):
            self.play(self.redis.lpop(PLAYLIST_KEY))

    def add(self, uri):
        self.redis.rpush(PLAYLIST_KEY, uri)

    def pause(self):
        if self.session.player.state == spotify.PlayerState.PLAYING:
            logger.info('Pausing playback')
            self.redis.set(PAUSED_KEY, 1)
            self.session.player.pause()

    def resume(self):
        if self.session.player.state == spotify.PlayerState.PAUSED:
            logger.info('Resuming playback')
            self.redis.set(PAUSED_KEY, 0)
            self.session.player.play()

    def stop(self):
        if self.session.player.state != spotify.PlayerState.UNLOADED:
            logger.info('Stopping playback')
            self.session.player.unload()

    def watch_playlist(self):
        if self.session.player.state == spotify.PlayerState.UNLOADED:
            logger.debug('Watching playlist')
            while True:
                if self.redis.llen(PLAYLIST_KEY) > 0:
                    logger.debug('Playlist not empty - stopped watching')
                    self.play(self.redis.lpop(PLAYLIST_KEY))
                    return

    def on_connection_state_updated(self, session):
        if session.connection.state is spotify.ConnectionState.LOGGED_IN:
            logger.info('Logged In to Spotify')
            self.logged_in.set()

            if self.redis.llen(PLAYLIST_KEY) > 0:
                self.play(self.redis.lpop(PLAYLIST_KEY))
            else:
                logger.debug('Playlist Empty')
                self.watch_playlist()

    def on_end_of_track(self, *agrs, **kwargs):
        logger.info('End of Track')
        self.session.player.unload()
        self.redis.delete(PLAYING_KEY)
        if self.redis.llen(PLAYLIST_KEY) > 0:
            self.play(self.redis.lpop(PLAYLIST_KEY))
        else:
            logger.debug('Playlist Empty')
            self.watch_playlist()
