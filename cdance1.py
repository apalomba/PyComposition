from pyScore import *
from Patterns import *
from Models.CubeDance import *
import random
import music21

cdance = CubeDance()
current_chord = "C"

# Converts MIDI note name to MIDI not number

def MidiListToMidiNumbers(notelist):
    '''
    Converts a list of MIDI note names to a list of MIDI note numbers
    Args:
        notelist : list of strings, where each string is a MIDI note name
    Returns:
        list: list of integers, where each integer is a MIDI note number
    '''
    if isinstance(notelist, str):
        notelist = [notelist]
    
    return [music21.pitch.Pitch(n).midi for n in notelist]


def send_notes(note_list):
    note_numbers = MidiListToMidiNumbers(note_list)
    for p in note_numbers:
        theScore.noteOut(p, between(90, 120), 0.25)


@ spawn
def dance_inside_cube(elapsedTime, length, rate):
    global current_chord
    if (elapsedTime < length):
        cube_chord = cdance.find_chord(current_chord)
        connected_chords = cdance.get_connected_chords(cube_chord)
        random_chord = random.choice(connected_chords)
        current_chord = random_chord    
        random_chord_obj = cdance.find_chord(random_chord)
        note_list = cdance.get_chord_pitches(random_chord_obj)
        print("current_chord: " +  current_chord + " | note_list: " +  str(note_list))
        send_notes(note_list)
        return rate
    return DONE      



#///////////////////////////////////////////////////////////////////////////////////////////////////////////
    
#create out score environment and bind it to our physical port
theScore = Score()
theScore.OpenMidiPortNamed("IAC Driver Bus 1")
theScore.OpenStream()

# play our gesture
elapsedTime = 0
length = 10
dance_inside_cube(elapsedTime, length, .5)

#wait for end and close
theScore.wait(length+1)
theScore.Fin()

