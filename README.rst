FM Player
=========

This repository holds the code for running the music player. The player will
listen for events on a Redis pub/sub channel and also emit events to this channel.
It will watch a Redis list which acts as the Playlist queue containing Spotify track
URIs. The player will pop tracks of the top of the list and play them one by one.

See Also
--------

* API Service: https://github.com/thisissoon/FM-API
* Web Socket Service: https://github.com/thisissoon/FM-Socket
* FE Client: https://github.com/thisissoon/FM-Frontend

Running the Player
------------------

The player cannot be installed on OSX as for Linux the Alsa Audio bindings are
required which is not support on OSX.

Docker
~~~~~~

The easiest way to run the player is through Docker.

If you are running on OSX and therefore via Boot2Docker there is currently no support
for sound, this means you will have to run the player with a fake audio sink, which
means the music will stream but there will be no audio out.

If you are running on Linux remember to give docker access to your sound device, via
``--device /dev/snd:/dev/snd``.

Simply run ``docker build -t soon/fm-player .``.

The docker entry command is ``fm-player`` - See environment variables below for
configuration.

Configuration / Environment Variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For the player to run it must be told about your Spotify credentials, where Redis is,
what channel to listen and publish events on and what audio sink to use. These can be
passed as environment variables or arguments passed into the application at run time.
Command line arguments will always override Environment Variables.

* ``-l / --log-level / FM_PLAYER_LOG_LEVEL`` - Verbosity of out out ('DEBUG', 'INFO',
  'WARNING', 'ERROR', 'CRITICAL')
* ``-u / --spotify-user / FM_PLAYER_SPOTIFY_USER`` - Your Spotify Username
* ``-p / --spotify-pass / FM_PLAYER_SPOTIFY_PASS`` - Your Spotify Password
* ``-k / --spotify-key / FM_PLAYER_SPOTIFY_KEY`` - Path to your Spotify API Key File (If you
  are running via Docker you will need to mount the file into the container)
* ``-r / --redis-uri / FM_PLAYER_Redis_URI`` - The Redis server url, e.g: ``Redis://host:port/``
* ``-c / --redis-channel / FM_PLAYER_Redis_CHANNEL`` - The channel to listen for / publish events
* ``-d / --redis-db / FM_PLAYER_Redis_DB`` -  The Redis DB Number
* ``-s / --audio-sink / FM_PLAYER_AUDIO_SINK`` - The Audio Sink to user ('portaudio', 'alsa', 'fake')
