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
        self.session.login(user, password)
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
            self.on_track_of_end)

    def on_connection_state_updated(self, session):
        """ Fired when the connect to Spotify changes
        """

        if session.connection.state is spotify.ConnectionState.LOGGED_IN:
            logger.info('Login Complete')
            LOGGED_IN_EVENT.set()  # Unblocks the player from starting

    def on_track_of_end(self, session):
        """ Fired when a playing track finishes, ensures the tack is unloaded
        and the ``STOP_EVENT`` is set to ``True``.
        """

        logger.debug('Track End - Unloading')
        session.player.unload()
        logger.debug('STOP_EVENT set')
        STOP_EVENT.set()  # Unblocks the playlist watcher

    def play(self, uri):
        """ Plays a given Spotify URI. Ensures the ``STOP_EVENT`` event is set
        back to ``False``, loads and then plays the track.

        Arguments
        ---------
        uri : str
            The Spotify URI - e.g: ``spotify:track:3Esqxo3D31RCjmdgwBPbOO``
        """

        logger.info('Play Track: {0}'.format(uri))

        try:
            track = self.session.get_track(uri).load()
            self.session.player.load(track)
            self.session.player.play()
        except (spotify.error.LibError, ValueError):
            logger.error('Unable to play: {0}'.uri)
        else:
            logger.debug('STOP_EVENT cleared')
            STOP_EVENT.clear()  # Reset STOP_EVENT flag to False

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

        mixer = self.get_mixer()
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

        if volume >= 0 and volume <= 100:
            mixer = self.get_mixer()
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

        mixer = self.get_mixer()

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

        mixer = self.get_mixer()
        try:
            mixer.setmute(int(mute))
        except Exception as e:
            logging.exception(e)
