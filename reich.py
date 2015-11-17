from pyScore import *
from music21 import pitch as m21pitch
from Patterns import *

keys = ["e4", "f#4", "b4", "c#5", "d5", "f#4", "e4", "c#5", "b4", "f#4", "d5", "c#5"]
keyPattern = Cycle(keys) 
keyPattern2 = Cycle(keys) 

@ spawn
def pianoPhase(elapsedTime, length, inputKeys, rate):
    if (elapsedTime < length):
        p = m21pitch.Pitch(inputKeys.Next())
        note(p.midi, between(80, 110), rate)
        return rate
    return DONE      


#///////////////////////////////////////////////////////////////////////////////////////////////////////////
    
#create out score environment and bind it to our physical port
theScore = ScoreEnvironment()
theScore.OpenMidiPort(4)
theScore.OpenStream()
note = theScore.noteOut #for convenience

# play our gesture
elapsedTime = 0
length = 30
pianoPhase(elapsedTime, length, keyPattern, .167)
pianoPhase(elapsedTime, length, keyPattern2, .170)

#wait for end and close
theScore.wait(length+1)
theScore.Fin()


# this is the Common music version
#; steve reich's piano phase

#define process piano-phase (endtime, keys, rate)
  #run with pat = make-cycle(keys)
    #while elapsed() < endtime
    #send "mp:midi", key: next(pat), dur: rate
    #wait rate
  #end

#; this plays the example in real time out your midi port

#begin
  #with keys = key({e4 fs4 b4 cs5 d5 fs4 e4 cs5 b4 fs4 d5 cs5}),
       #stop = 20
  #sprout list(piano-phase(stop, keys, .167),
              #piano-phase(stop, keys, .170))
#end
