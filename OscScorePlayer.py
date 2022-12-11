from pyScore import *
from Patterns import *
from OscServer import *

keys = ["e-4", "f#-4", "b-4", "c#-5", "d-5", "f#-4", "e-4", "c#-5", "b-4", "f#-4", "d-5", "c#-5"]
keyPattern = Cycle(keys) 
keyPattern2 = Cycle(keys) 

@ spawn
def pianoPhase(elapsedTime, length, inputKeys, rate):
    if (elapsedTime < length):
        #p = m21pitch.Pitch(inputKeys.Next())
        p = MidiStringToInt(inputKeys.Next())
        note(p, between(80, 110), rate)
        return rate
    return DONE      

# Converts MIDI note name to MIDI not number
def MidiStringToInt(midstr):
    midstr = midstr.upper()
    Notes = [["C"],["C#","Db"],["D"],["D#","Eb"],["E"],["F"],["F#","Gb"],["G"],["G#","Ab"],["A"],["A#","Bb"],["B"]]
    answer = 0
    i = 0
    #Note
    letter = midstr.split('-')[0].upper()
    for note in Notes:
        for form in note:
            if letter.upper() == form:
                answer = i
                break;
        i += 1
    #Octave
    answer += (int(midstr[-1]))*12
    return answer

#///////////////////////////////////////////////////////////////////////////////////////////////////////////

oscServer = OscServer()

#create out score environment and bind it to our physical port
theScore = Score()
theScore.OpenMidiPortNamed("IAC Driver Virtual MIDI Port 1")
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

