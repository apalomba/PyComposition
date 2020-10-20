pyComposition is a realt-time python environment for parametric music composition. 

To Install:

1. Install anaconda3 on your computer

2. pyComposition uses python-rtmidi to send data to your computers midi port. You can find details here:
https://pypi.org/project/python-rtmidi/
Installation can be done via the command line in anaconda using the pip command:
pip install python-rtmidi

3. When installed you will then be able to access your midi ports. Please note that your midi ports may be named
differently. The examples may need to be modified so that they match your system.

4. pyComposition only generates midi data, so you will need some midi device or soft synth listening
to the midi port you are sending data to generate sound.
