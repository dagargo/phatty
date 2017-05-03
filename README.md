# Phatty

Phatty is an library editor for the Moog Little Phatty. It has been designed to work together with the synth by providing a easy edition of hidden parameters. However, it does not provide fully editing capabilities since no computer screen can replace real knobs. Besides, you will be able to rename and rearrange presets.

## Installation

The package dependencies for Debian based distributions are:
- python3
- python3-setuptools
- make
- gcc and g++
- libpython3-dev
- libasound2-dev
- libjack-jackd2-dev

You can easily install them by running `sudo apt-get install python3 python3-setuptools make gcc g++ libpython3-dev libasound2-dev libjack-jackd2-dev`.

To install Phatty symply run `make && sudo make install`.

## Known issues
At the moment, the underlying MIDI libraries do not raise an error if the synth is disconnected. Thus, neither the application can be aware of the error nor the user get any error message.
