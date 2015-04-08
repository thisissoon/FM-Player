#!/usr/bin/env python
# encoding: utf-8

"""
fmplayer.player
===============

Classes and methods for running the Spotify player.
"""

import alsaaudio
import logging
import spotify
import threading

from fmplayer.sinks import FakeSink


logger = logging.getLogger('fmplayer')

LOGGED_IN_EVENT = threading.Event()
STOP_EVENT = threading.Event()


class Player(object):
    """ Handles playing music from Spotify.
    """

    def __init__(self, user, password, key, sink):
        """ Initialises the Spotify Session, logs the user in and starts
        the session event loop. The player does not manage state, it simply
        cares about playing music.

        Arguments
        ---------
        user : str
            The Spotify User
        password : str
            The Spotify User Password
        key : str
            Path to the Spotify API Key File
        sink : str
            The audio sink to use
        """

        # Session Configuration
        logger.debug('Configuring Spotify Session')
        config = spotify.Config()
        config.load_application_key_file(key)
        config.dont_save_metadata_for_playlists = True
        config.initially_unload_playlists = True

        # Create session
        logger.debug('Creating Session')
        self.session = spotify.Session(config)
        self.register_session_events()
        self.session.preferred_bitrate(spotify.audio.Bitrate(1))

        # Set the session event loop going
        logger.debug('Starting Spotify Event Loop')
        loop = spotify.EventLoop(self.session)
        loop.start()

        # Block until Login is complete
        logger.debug('Waiting for Login to Complete...')
        self.session.login(user, password, remember_me=True)
        LOGGED_IN_EVENT.wait()

        # Set the Audio Sink for the Session
        sinks = {
            'alsa': spotify.AlsaSink,
            'fake': FakeSink
        }
        logger.info('Settingw Audio Sink to: {0}'.format(sink))
        sinks.get(sink, FakeSink)(self.session)

    def register_session_events(self):
        """ Sets up session events to listen for and set an appropriate
        callback function.
        """

        self.session.on(
            spotify.SessionEvent.CONNECTION_STATE_UPDATED,
            self.on_connection_state_updated)

        self.session.on(
            spotify.SessionEvent.END_OF_TRACK,
            self.on_track_end)

        self.session.on(
            spotify.SessionEvent.CONNECTION_ERROR,
            self.on_connection_error)

    def on_connection_error(self, session, error):
        """ Fired when a connection error occures.
        """

        logger.error('Connection Error: {0}'.error)

        # Lets try and relogin
        self.session.relogin()

    def on_connection_state_updated(self, session):
        """ Fired when the connect to Spotify changes
        """

        if session.connection.state is spotify.ConnectionState.LOGGED_IN:
            logger.info('Login Complete')
            LOGGED_IN_EVENT.set()  # Unblocks the player from starting

        if session.connection.state is spotify.ConnectionState.LOGGED_OUT:
            logger.info('Logged Out')
            self.session.relogin()

    def on_track_end(self, session):
        """ Called when the track finishes playing.
        """

        self.stop()

    def play(self, uri):
        """ Plays a given Spotify URI. Ensures the ``STOP_EVENT`` event is set
        back to ``False``, loads and then plays the track.

        Arguments
        ---------
        uri : str
            The Spotify URI - e.g: ``spotify:track:3Esqxo3D31RCjmdgwBPbOO``
        """

        try:
            logger.info('Play Track: {0}'.format(uri))
            track = self.session.get_track(uri).load()
            self.session.player.load(track)
            self.session.player.play()
        except:  # Catch all cos I don't really know what will go wrong here
            logger.exception('Unable to play {0} - forcing stop'.format(uri))
            self.stop()

        logger.debug('Block Watcher - STOP_EVENT cleared')
        STOP_EVENT.clear()  # Reset STOP_EVENT flag to False

    def stop(self):
        """ Fired when a playing track finishes, ensures the tack is unloaded
        and the ``STOP_EVENT`` is set to ``True``.
        """

        logger.info('Track Stop - Unload')
        self.session.player.unload()
        logger.debug('Unblock Watcher: STOP_EVENT set')
        STOP_EVENT.set()

    def pause(self):
        """ Pauses the current playback if the track is in a playing state.
        """

        if self.session.player.state == spotify.PlayerState.PLAYING:
            logger.info('Pausing Playback')
            self.session.player.pause()
        else:
            logger.debug('Cannot Pause - No Track Playing')

    def resume(self):
        """ Resumes playback if the player is in a paused state.
        """

        if self.session.player.state == spotify.PlayerState.PAUSED:
            logger.info('Resuming Playback')
            self.session.player.play()
        else:
            logger.debug('Cannot Resume - Not in paused state')

    def get_mixer(self):
        """ Returns the mixer object. The mixer must be recreated every time
        it is used to be able to  observe volume/mute changes done by other
        applications.

        Returns
        -------
        alsaaudio.Mixer
            The mixer instance
        """

        return alsaaudio.Mixer(control='PCM', cardindex=0)

    def get_volume(self):
        """ Returns the current mixer volume. Adapted from:
        https://github.com/mopidy/mopidy-alsamixer

        Returns
        -------
        int
            The volume level from 0 to 100
        """

        try:
            mixer = self.get_mixer()
        except alsaaudio.ALSAAudioError:
            return None

        channels = mixer.getvolume()
        if not channels:
            return None
        elif channels.count(channels[0]) == len(channels):
            return int(channels[0])
        else:
            # Not all channels have the same volume
            return None

    def set_volume(self, volume):
        """ Set the player audio volume between 0 and 100.

        Arguments
        ---------
        volume : int
            The level to set the volume at
        """

        try:
            mixer = self.get_mixer()
        except alsaaudio.ALSAAudioError:
            return None

        if volume >= 0 and volume <= 100:
            mixer.setvolume(int(volume))
            logger.debug('Set volume level to {0}'.format(volume))
        else:
            logger.error('{0} is not a valid volume level'.format(volume))

    def get_mute(self):
        """ Returns the current mute state of the player. Amended from:
        https://github.com/mopidy/mopidy-alsamixer

        Returns
        -------
        bool
            Mute state of the player
        """

        try:
            mixer = self.get_mixer()
        except alsaaudio.ALSAAudioError as e:
            return False

        try:
            channels_muted = mixer.getmute()
        except alsaaudio.ALSAAudioError as e:
            logger.debug('Getting mute state failed: {0}'.format(e))
            return None
        if all(channels_muted):
            return True
        elif not any(channels_muted):
            return False
        else:
            return None

    def set_mute(self, mute):
        """ Set the players mute state, basically setting the volume to 0.

        Arguments
        ---------
        mute : bool
            ``True`` to set mute, ``False`` to remove mute.
        """

        try:
            mixer = self.get_mixer()
        except alsaaudio.ALSAAudioError as e:
            return None

        try:
            mixer.setmute(int(mute))
        except Exception as e:
            logging.exception(e)
