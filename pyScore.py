import thread
import threading
import EventScheduler
from pyCompLib import *

#////////////////////////////////////////////////////////////////////////////////////////////////
class Score(object):
    """ Holds common score environment variables """
    
    def __init__(self, port = None):
        self.tempo = 120
        self. keysig = "C"
        self.timesig = "4/4"    
        self.port = port 
        self.midiStream = None
    
    def OpenMidiPort(self , midiPortNumber):
        self.port = MIDIPort()    
        self.port.PrintDevices(OUTPUT)
        self.port.Open(midiPortNumber)     

    def OpenMidiPortNamed(self, portName):
        self.port = MIDIPort()
        self.port.OpenNamed(portName)

    def OpenStream(self):
        self.midiStream = MIDIStreamRT(self.port)
        self.midiStream.Start()
        
    def noteOut(self, key  = 60, amp  = 100, dur  = .5, chan  = 0):
        self.midiStream.NoteEvent2(key, amp, dur, chan)
    
    def wait(self, length):
        time.sleep(length+1) 
        
    def Fin(self):
        procManager.StopAll()
        self.midiStream.Stop()
        self.port.Close()        
        print 'Score finished'
        
        
#////////////////////////////////////////////////////////////////////////////////////////////////   
@ spawn
def testChords(elapsedTime, length):
    if (elapsedTime < length):
        theScore.noteOut(63, between(70, 100), 0.25)
        theScore.noteOut(65, between(70, 100), 0.25)
        theScore.noteOut(68, between(70, 100), 0.25)
        return 0.25
    return DONE        


if __name__ == '__main__':
           
    #create out score env and bind it to our physical port
    theScore = Score()
    theScore.OpenMidiPortNamed("IAC Driver Virtual MIDI Port 1")
    theScore.OpenStream()

    # play our gesture
    elapsedTime = 0; 
    length = 5
    testChords(elapsedTime, length)
    
    #wait for end and close
    theScore.wait(length+1) #wait for notes to finish playing
    theScore.Fin()