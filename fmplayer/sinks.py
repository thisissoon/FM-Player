#!/usr/bin/env python
# encoding: utf-8

"""
fmplayer.sinks
==============

Custom Audio Sinks
"""

import logging
import spotify


logger = logging.getLogger('fmplayer')


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
