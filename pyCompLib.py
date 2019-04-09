from scipy import interpolate ,random
import numpy as np
import threading
import time
import EventScheduler
from pyCompIOPort import *
from EventScheduler import ms2sec, sec2ms
from Patterns import *



#//////////////////////////////////////////////////////////////////////////////
#Globals

DONE = -1

normSpace = np.linspace(0.0, 1.0, 32)
    
# global proc manager needed for spawn and sync        
procManager = EventScheduler.ProcessManager()

def PlayChord(noteList, vel, dur):
    for k in noteList:
        note(k, vel, dur)

#//////////////////////////////////////////////////////////////////////////////
# Probability
def randFromList(theList):
    ''' will randomly pick an element from the given list'''
    index = int(between(0, len(theList)-1))
    return theList[index]
    
def random(*args):
    if (len(args) == 0):
        return np.random.rand()
    elif (len(args) == 2): 
        return between( args[0], args[1])
    else:
        return between(0, args[0])

def between(low, high):
    x = np.random.rand()
    return low+x*(high-low)


#//////////////////////////////////////////////////////////////////////////////
# Form
def interpRange(c, x1, y1, x2, y2, base = None):
    '''Maps range (x1 <= y1) on to (x2 <= y2) base : ('linear', 'nearest', 'zero', 'slinear', 'quadratic, 'cubic') '''
    if(c < x1):
        return y1
    if(c > x2):
        return y2
    range1 = np.linspace(x1, x2, 32)
    range2 = np.linspace(y1, y2, 32)
    f = interpolate.interp1d(range1, range2)
    return f(c)  

def interpList(c, rangeList, base = None):
    ''' Maps list of points (x1, x2, x3, x4) on to (y1, y2, y3, y4)  interpList(75, [(0, 500), (50, 550), (100, 1000)]) '''
    x, y = np.array(rangeList).transpose()    
    f = interpolate.interp1d(x, y)
    return f(c)

def intempo  (beats, tempo) :
    pass

def wait (msDelay):
    ''' delay in miliseconds '''
    time.sleep(ms(msDelay))

        
#//////////////////////////////////////////////////////////////////////////////
class spawn(object):
    '''this is a function decorator that enables us to spawn a function and create a thread for it'''
    def __init__(self, function):
        #print 'spawn: __init__ {0}'.format(function.__name__)
        self.func = function
        
    def __call__(self,  *args):
        print ('spawn: __call__ {0}{1}'.format(self.func.__name__, args))
        #self.func(args)
        self.pID = procManager.AddProcess(self.func, ms(1000), args)    
        procManager.StartProcess(self.pID)

#//////////////////////////////////////////////////////////////////////////////
class sync(object):
    '''this is a function decorator that enables us to execute function and wait until it is completed'''
    def __init__(self, function):
        print ('sync: __init__ {0}'.format(function.__name__))
        self.func = function
        
    def __call__(self,  *args):
        print ('sync: __call__ {0}{1}'.format(self.func.__name__, args))
        #self.func(args)
        self.pID = procManager.AddProcess(self.func, ms(1000), args)    
        procManager.StartProcess(self.pID)
        proc = procManager.GetProcess(self.pID)
        while(proc.WaitInterval != DONE):
            time.sleep(.25)
        print ('sync: complete {0}{1}'.format(self.func.__name__, args))

#//////////////////////////////////////////////////////////////////////////////

@ sync 
def syncGesture(elapsedTime, length, rate, key, keyrange, mintempo, maxtempo,minamp, maxamp, mid):
    '''elapsedTime, length, rate, key, keyrange, mintempo, maxtempo,minamp, maxamp mid '''
    if (elapsedTime < length):
        k = key + random(keyrange)
        amp = interpRange( elapsedTime, mid, maxamp, length, minamp)
        dur = interpList( elapsedTime, [(0, mintempo), (mid, maxtempo), (length, mintempo)])
        note(k, amp*127,  dur)
        #print 'elapsedTime: {0}, key: {1}, amp: {2}, dur: {3}' .format(elapsedTime, k, a, d)
        #print 'interpGesture - Time: {0}, wait: {1}, elapsedTime: {2}' .format(midiPort.GetTime(), rate * d, elapsedTime)
        return dur
    return DONE


@ spawn
def spawnGesture(elapsedTime, length, key, keyrange):
    if (elapsedTime < length):
        k = int(key + random(keyrange))
        #dur = .25
        dur = between(.25, 1)
        amp = int(between(75, 110))
        
        note(k, amp, dur)
        noteInterval = interpRange( elapsedTime, 0, 0, length, 10)
        
        m = int(k + noteInterval)
        note(m, amp, dur)
        
        print ('interpGesture - Time: {0}, note: {1}, {2}' .format(midiPort.GetTime(), k, m))
        return dur
    return DONE


duration = 0

   
if __name__ == '__main__':
    
    midiPort = MIDIPort()    
    midiPort.PrintDevices(OUTPUT)
    midiPort.Open(1)
    
    midiStream = MIDIStreamRT(midiPort)
    midiStream.Start()
    
    note = midiStream.NoteEvent2
    
    # setup our gesture
    elapsedTime = 0; length= 10; rate = .2
    key = 84; keyrange= 12
    mintempo = .5; maxtempo = .125
    minamp = .4; maxamp = .8
    mid = (.2 * length) + random( .6 * length)    # random mid point between 20 and 80 percent of the gesture
    
    #syncGesture(elapsedTime, length, rate, key, keyrange, mintempo, maxtempo,minamp, maxamp, mid)
    spawnGesture(elapsedTime, length, key, keyrange)
    
    #wait until finished
    time.sleep(length+1) #wait for notes to finish playing
    #midiStream.WaitForStreamEnd()
    procManager.StopAll()
    midiStream.Stop()
    midiPort.Close()        
    
    print ('Test complete')
   
