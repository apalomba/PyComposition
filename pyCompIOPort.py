try:
    import rtmidi    
except:
    print ('Failed to import rtmidi')
try:
    import csnd6
except:	
    print ('Failed to import csnd6.')
import time
import EventScheduler
import threading
import datetime


INPUT=0
OUTPUT=1

defaultCSD = '''<CsoundSynthesizer>
<CsOptions>
; Select audio/midi flags here according to platform
;-odac0         ;; -iadc         ;;;RT audio I/O
</CsOptions>
<CsInstruments>

; Initialize the global variables.
	sr	= 44100
	kr	= 4410
	ksmps	= 10
	nchnls	= 1

; Instrument #1.
	instr 1
kamp 	=	31129.60
kfreq 	=	440
krat	= 	0.127236
kvibf 	=	6.12723
ifn 	=	1

; Create an amplitude envelope for the vibrato.
kenv 	linseg 0, 0.15, 1, p3-0.4, 1, 0.25, 0
kv 	linseg	0, 0.5, 0, 1, 1, p3-0.5, 1
kvamp 	=	kv * 0.01

a1 	oscili	kamp*kenv, kfreq, 1
	out	a1 * 0.5
	endin


</CsInstruments>
<CsScore>	

; Table #1, a sine wave.
f	1	0	128	10	1	
f 0 3600	;'DUMMY' SCORE EVENT KEEPS REALTIME PERFORMANCE GOING FOR 1 HOUR
; Play Instrument #1 for two seconds.
;i	1	0	5	
e	


</CsScore>
</CsoundSynthesizer>'''

def ms(interval):
    ''' convert sec to ms '''    
    return EventScheduler.sec2ms(interval)

#//////////////////////////////////////////////////////////////////////////////
#ENUMS
class eMidiCommands:
    NOTE_OFF = 0x80     
    NOTE_ON = 0x90     
    AFTER_TOUCH = 0xA0     
    CNTRL = 0xB0     # Continuous controller
    PATCH = 0xC0     # Patch change
    CHAN_PRESSURE = 0xD0     #Channel Pressure
    PITCH_BEND = 0xE0     # Pitch bend
    MISC_COMMAND = 0xF0     # (non-musical commands)

class ePortType:
    """ Enum class that enumerates our output ports """
    NONE= object()
    MIDI=object()
    OSC=object()
    DAC=object()
    FILE=object()
    CSOUND=object()


class eEventParams:
    '''Enum of note parameters'''
    TIME= 0
    DUR=1
    NOTE_PARAMS=2


#//////////////////////////////////////////////////////////////////////////////
class NoteParams:
    ''' encapsulates our note parameters '''

    def __init__(self, key, vel, chan):
        self.key = key
        self.vel = vel
        self.chan = chan
    
    def Print(self):
        return '(key: {0}, vel: {1}, chan: {2})'.format(self.key, self.vel, self.chan)
    
#//////////////////////////////////////////////////////////////////////////////
class ControlParams:
    """ encapsulates our control parameters """

    def __init__(self):
        self.ctrl = 32
        self.data = 127
        self.chan = 1        
        
#//////////////////////////////////////////////////////////////////////////////
class MIDIEventQueue():
    ''' Encapsulation of list containing MIDI events '''
    def __init__(self):
        self.theQ = list() 
        
    def AddEvent(self, eventParams):
        ''' adds note to end of queue '''
        self.theQ.append(eventParams)

    def AddEventTimeSorted(self, eventParams):
        ''' adds note to queue at proper place in time'''
        bFound = False
        
        #go through and find where in time we should insert this note
        noteParams = eventParams[eEventParams.NOTE_PARAMS]
        noteTime = eventParams[eEventParams.TIME]           
        for ev in self.theQ:
            curTime = ev[eEventParams.TIME]
            if(curTime > noteTime):
                self.theQ.insert(0, eventParams) #insert in front of
                bFound = True
                break;
                #Insert an item at a given position. The first argument is the index of the 
                #element before which to insert, so a.insert(0, x) inserts at the front of the list
        if(bFound == False):
            self.theQ.append(eventParams) #just add to end
         
        #self.DumpEvents()       
                
    def GetFirstEvent(self):
        ''' will return the next note that needs to be played '''
        if(self.isEmpty()):
            return None
        else:
            return self.theQ[eEventParams.TIME]

    def RemoveEvent(self):
        ''' will remove the first note (oldest) note in the queue '''
        self.theQ.pop(0)

    def Flush(self):
        ''' remove all notes from queue '''
        for i in range(self.theQ.count()):
            self.theQ.pop(0)

    def SortEvents(self):
        self.theQ = sorted(self.theQ, key=lambda param: param[eEventParams.TIME])   # sort on time
        # convert absolute duration of note to relative duration of event
        for i in range (0, len(self.theQ)-1):
            event1 = self.theQ[i]
            event2 = self.theQ[i+1]
            time1 = event1[eEventParams.TIME]
            time2 = event2[eEventParams.TIME]
            event1[eEventParams.DUR] = time2 - time1
            
    def isEmpty(self):
        if(len(self.theQ) == 0):
            return True
        else:
            return False
        
    def Count(self):
        return len(self.theQ) 

    def DumpEvents(self):
        for params in self.theQ:
            time = params[eEventParams.TIME]
            dur= params[eEventParams.DUR]
            event = params[eEventParams.NOTE_PARAMS]
            #print "The sum of 1 + 2 is {0}".format(1+2)
            #print 'We are the {} who say "{}!"'.format('knights', 'Ni')
            print ('time: {0},  dur:{1}, event: {2}'.format(time, dur, event.Print()))
            #print 'time: ' +  time ' event: ' + event
            
    def PrintEvent(self, event = []):
        liststr = ''
        for value in event:
            liststr += (value + " ")
        return liststr
            
#//////////////////////////////////////////////////////////////////////////////
class MIDIStream(threading.Thread):
    def __init__(self, Port, realTime = False):
        ''' MIDIStream: (Port: midi port to use, realTime: process events in real time'''
        threading.Thread.__init__(self)       
        self.midiPort = Port  # reference to the port we will be using for output
        self.midiEventQ = MIDIEventQueue()
        self.bStop = False
        self.bRealTimeOutput = realTime
        self.lastEvent = None
        
    def run(self):     
        ''' this is our event thread, it process all our midi events'''
        #print 'MIDIStream: run thread ({0})...'.format(self.midiPort .GetTime())
        while (self.bStop == False):
            if(self.midiEventQ .isEmpty() == False):
                if(self.bRealTimeOutput):
                    self.ProcessQ_RealTime()
                else:
                    self.ProcessQ_NonRealTime()
                    
    def ProcessQ_Realtime(self):
        #print 'MIDIStream: ProcessQ_Realtime ({0})'.format(self.midiPort .GetTime())
        event = self.midiEventQ.GetFirstEvent()
        if(event != None):
            self.midiEventQ .RemoveEvent() # remove this event from queue     
            dur = event[eEventParams.DUR]
            params = event[eEventParams.NOTE_PARAMS]
            if(dur != 0):
                self.midiPort.NoteOut(params)     # send event 
                threading._sleep(dur)  # go to sleep for duration of event
                params.vel = 0 # send note off
                self.midiPort.NoteOut(params)     # send event 
            
    def ProcessQ_NonRealtime(self):
        event = self.midiEventQ.GetFirstEvent()
        if(event != None):
            time = event[eEventParams.TIME]
            dur = event[eEventParams.DUR]
            params = event[eEventParams.NOTE_PARAMS]
            self.midiPort.NoteOut(params)     # send event 
            self.midiEventQ .RemoveEvent() # remove this event
            if(dur != 0):
                threading._sleep(dur)  # go to sleep for duration of event
            
    
    
    def Start(self):
        bStop = False
        print ('MIDIStream: start thread ({0})...'.format(self.midiPort .GetTime()))
        self.start()       
        

    def Stop(self):
        self.bStop = True  
        print ('MIDIStream: stop thread ({0}), Q: {1}'.format(self.midiPort .GetTime(), self.midiEventQ.Count()))
        
    def NoteEvent(self, time = 0.0, key  = 60, amp  = 100, dur  = .5, chan  = 0):
        '''' will send a note out using the event scheduler. dur is in seconds
        time(ms) = 0.0, dur  = .5, key  = 60, amp  = .5, chan  = 0 '''
        timestamp = self.midiPort.GetTime()
        
        #add note on
        event = NoteParams(key, amp, chan)
        eventList = [time, dur, event]
        self.midiEventQ.AddEvent(eventList)

        if(self.bRealTimeOutput == False):
            #add note off
            event = NoteParams(key, 0, chan)
            eventList = [time + dur, 0, event]
            self.midiEventQ.AddEvent(eventList)        

    def NoteEvent2(self, key  = 60, amp  = 100, dur  = .5, chan  = 0):
        '''' will send a note out using the event scheduler. dur is in seconds. dur  = .5, key  = 60, amp  = .5, chan  = 0 '''
        timestamp = self.midiPort.Time()
        self.NoteEvent(timestamp, key, amp, dur, chan)

    def ControlEvent(self, time = 0, ctrl  = 32, val = 127, chan  = 0):    
        pass
    
    def SyncEventList(self):
        self.midiEventQ.SortEvents()
        self.midiEventQ.DumpEvents()
            
    def AddNote(self, NoteParams):
        pass

    def Flush(self):
        pass
    def isComplete(self):
        return self.midiEventQ.isEmpty()
    
    def WaitForStreamEnd(self):
        while(self.isComplete() == False):
            time.sleep(.125)
            
    def send(self):
        pass
    
    
    
#//////////////////////////////////////////////////////////////////////////////   
class MIDIStreamRT(threading.Thread):
    def __init__(self, Port):
        ''' MIDIStreamRT: (Port: midi port to use, realTime: process events in real time. Supports concurrent notes.)'''
        threading.Thread.__init__(self)       
        self.port = Port  # reference to the port we will be using for output
        self.midiEventQ = MIDIEventQueue()
        self.bStop = False
        self.lastEvent = None
        self.lock = threading.BoundedSemaphore() #used to synchronize access to queue
        
    def run(self):     
        ''' this is our event thread, it process all our midi events'''
        #print 'MIDIStreamRT: run thread ({0})...'.format(self.port .GetTime())
        while (self.bStop == False):
            self.ProcessQ()
            time.sleep(EventScheduler.ms2sec(10))# sleep 
                    
    def ProcessQ(self):
        # get current time
        currentTime = self.port.GetTime()
        #print '+++ MIDIStream: ProcessQ ({0})\n'.format(portmidi.Time())
        # go through our midi event queue and sent messages that need to go
        self.lock.acquire()
        while(True):
            event = self.midiEventQ.GetFirstEvent()
            if(event == None):
                break #queue is empty
            
            noteTime = event[eEventParams.TIME]            
            if(noteTime <= currentTime):
                params = event[eEventParams.NOTE_PARAMS]    
                self.port.NoteOut(params)     # send event 
                self.midiEventQ.RemoveEvent()
            else:
                break # no need to continue
        self.lock.release()
    
    def Start(self):
        bStop = False
        #print 'MIDIStreamRT: start thread ({0})'.format(self.port .GetTime())
        self.start()       
        

    def Stop(self):
        self.Flush()
        self.bStop = True  
        #print 'MIDIStreamRT: stop thread ({0}), Q: {1}'.format(self.port .GetTime(), self.midiEventQ.Count())
        
    def NoteEvent(self, time = 0.0, key  = 60, amp  = 100, dur  = .5, chan  = 0):
        '''' will send a note out using the event scheduler. dur is in seconds
        time(ms) = 0.0, dur  = .5, key  = 60, amp  = .5, chan  = 0 '''
        
        noteOn = NoteParams(key, amp, chan)
        self.port.NoteOut(noteOn)     # send note on 

	#print '+++ MIDIStreamRT: NoteEvent ({0}, {1}, {2}, {3})\n'.format(time, key, amp, dur)

        #add note off
        event = NoteParams(key, 0, chan)
        eventList = [time + EventScheduler.sec2ms(dur), 0, event]
        self.lock.acquire()
        self.midiEventQ.AddEventTimeSorted(eventList)        
        self.lock.release()
        
    def NoteEvent2(self, key  = 60, amp  = 100, dur  = .5, chan  = 0):
        '''' will send a note out using the event scheduler. dur is in seconds. dur  = .5, key  = 60, amp  = .5, chan  = 0 '''
        timestamp = self.port.GetTime()
        self.NoteEvent(timestamp, key, amp, dur, chan)
        
    def ControlEvent(self, time = 0, ctrl  = 32, val = 127, chan  = 0):    
        pass
                    
    def Flush(self):
        pass
    
    def isComplete(self):
        return self.midiEventQ.isEmpty()
    
    def WaitForStreamEnd(self):
            while(self.isComplete() == False):
                time.sleep(.20)
       
#//////////////////////////////////////////////////////////////////////////////   
class MessageStreamRT(threading.Thread):
    def __init__(self, Port):
        ''' MIDIStreamRT: (Port: midi port to use, realTime: process events in real time. Supports concurrent notes.)'''
        threading.Thread.__init__(self)
        self.port = Port  # reference to the port we will be using for output
        self.midiEventQ = MIDIEventQueue()
        self.bStop = False
        self.lastEvent = None
        self.lock = threading.BoundedSemaphore() #used to synchronize access to queue
	
    def run(self):     
        ''' this is our event thread, it process all our midi events'''
        #print 'MIDIStreamRT: run thread ({0})...'.format(self.port .GetTime())
        while (self.bStop == False):
            self.ProcessQ()
            time.sleep(EventScheduler.ms2sec(10))# sleep
		    
    def ProcessQ(self):
        # get current time

        currentTime = self.port.GetTime()
        #print '+++ MIDIStream: ProcessQ ({0})\n'.format(currentTime)

        # go through our midi event queue and sent messages that need to go
        self.lock.acquire()
        while(True):
            event = self.midiEventQ.GetFirstEvent()
            if(event == None):
                break #queue is empty

            noteTime = event[eEventParams.TIME]
            if(noteTime <= currentTime):
                params = event[eEventParams.NOTE_PARAMS]
                self.port.NoteOut(params)     # send event
                self.midiEventQ.RemoveEvent()
            else:
                break # no need to continue
        self.lock.release()
    
    def Start(self):
        bStop = False
        #print 'MIDIStreamRT: start thread ({0})'.format(self.port .GetTime())
        self.start()
	
	

    def Stop(self):
        self.Flush()
        self.bStop = True
        #print 'MIDIStreamRT: stop thread ({0}), Q: {1}'.format(self.port .GetTime(), self.midiEventQ.Count())

    def NoteEvent(self, time = 0.0, key  = 60, amp  = 100, dur  = .5, chan  = 0):
        '''' will send a note out using the event scheduler. dur is in seconds
        time(ms) = 0.0, dur  = .5, key  = 60, amp  = .5, chan  = 0 '''

        #print '+++ MIDIStreamRT: NoteEvent ({0}, {1}, {2}, {3})\n'.format(time, key, amp, dur)

        noteOn = NoteParams(key, amp, chan)
        self.port.NoteOut(noteOn)     # send note on

        #add note off
        event = NoteParams(key, 0, chan)
        eventList = [time + EventScheduler.sec2ms(dur), 0, event]
        self.lock.acquire()
        self.midiEventQ.AddEventTimeSorted(eventList)
        self.lock.release()
	
    def NoteEvent2(self, key  = 60, amp  = 100, dur  = .5, chan  = 0):
        '''' will send a note out using the event scheduler. dur is in seconds. dur  = .5, key  = 60, amp  = .5, chan  = 0 '''
        timestamp = self.port.GetTime()
        self.NoteEvent(timestamp, key, amp, dur, chan)
	
    def ControlEvent(self, time = 0, ctrl  = 32, val = 127, chan  = 0):    
        pass
		    
    def Flush(self):
	    pass
    
    def isComplete(self):
	    return self.midiEventQ.isEmpty()
    
    def WaitForStreamEnd(self):    
        while(self.isComplete() == False):
            time.sleep(.20)
			
#//////////////////////////////////////////////////////////////////////////////
class IOPort():   
    """ Base class of our output port """
    def __init__(self, portType):
        if(property == ePortType.MIDI):
            self = MIDIPort()
        elif (property == ePortType.CSOUND):
            self = CSoundPort()
        else:
            raise Exception('Unknown i/o port specified')
        pass
    
    def Open(self):
        print ("OutputPort:Open")

    def Close(self):
        print ("OutputPort:Close")

#//////////////////////////////////////////////////////////////////////////////
class MIDIPort(IOPort):   
    """ Represents our MIDI Port: uses portmidi"""
    def __init__(self):
        self.currentMidiPort = 0 # should be MS MIDI Mapper
        self.latency = 0 # used by pypm to specify MIDI latecny, does not seem to have any effect
        self.midiOut = rtmidi.MidiOut() 	
        self.bOpen = False
        self.availablePorts = self.midiOut.get_ports()
        self.startTime = datetime.datetime.now()
	

    def __del__(self):
        del self.midiOut
      
    
    # opens MIDI ports with specified name 
    def OpenNamed(self, portName):
        portNum = 0
        self.startTime = datetime.datetime.now()
        for systemPort in self.availablePorts:
            if systemPort == portName:
                self.currentMidiPort = portNum
                self.midiOut.open_port(portNum)
                print ("MIDIPort:Open " + systemPort)
                self.bOpen = True
                break
            portNum += 1

        if(self.bOpen == False):
            raise Exception("Could not open specified MIDI port")
	
        
    def Open(self, portNum = 0):
        self.startTime = datetime.datetime.now()
        if(portNum >= len(self.availablePorts)):
            print ("Specified midi port is beyond physical range.")
            return
         
        self.currentMidiPort = portNum
        self.midiOut.open_port(portNum)
        print ("MIDIPort:Open")
        self.bOpen = True
        

    def Close(self):
        if(self.midiOut != None):
            print ("MIDIPort:Close")
        self.bOpen = False
            

    def PrintDevices(self, InOrOut):
        for systemPort in self.availablePorts:
            print(systemPort)

    def SetPortID(self, portID):
        self.currentMidiPort = portID
        
    def NoteOut(self, params):
        '''' this will send a note out our midi port'''
        timestamp = self.GetTime()
        note_message = [0x90, (int)(params.key), (int)(params.vel)] # channel 1, note, velocity
        self.midiOut.send_message(note_message)
	        
    def CtrlOut(self):
        pass

    def GetTime(self):
        deltaTime = datetime.datetime.now() - self.startTime
        return deltaTime.total_seconds()*1000
    
    
 #//////////////////////////////////////////////////////////////////////////////
class MaxPort(IOPort):   
    """ Represents a port that will send data to max"""
    def __init__(self):
        self.currentMidiPort = -1 # not used in MaxPort
        self.latency = 1000 # used by pypm to specify MIDI latecny, does not seem to have any effect
        self.midiOut = None
        self.pyext = None #if we are in a Max environment, this will be set to pyext.MaxPyExt()

    def Open(self):
        print ("MaxPort:Open")

    def Close(self):
        print ("MaxPort:Close")

    def PrintDevices(self, InOrOut):
       pass

    def SetPortID(self, portID):
       pass

    def NoteOut(self, params):
        '''' this will send a note out our midi port'''
        #timestamp = self.midiOut.Time()
        #print 'NoteOut: {0}, {1}'.format(timestamp, params.Print())
        #self.midiOut.Write([[[0x90, params.key, params.vel], timestamp]])     # send note
        #self.midiOut.WriteShort(0x90, (int)(params.key), (int)(params.vel))
        noteStr = 'note {0} {1} {2}'.format(params.key, params.vel, params.chan)
        #self._outlet(1, noteStr)
        if self.pyext is not None:
            self.pyext.NoteOut(noteStr)
        else:
            print ('note: {0}'.format(noteStr))

    def CtrlOut(self):
        pass

    def GetTime(self):
        pass

class CSoundPort(IOPort):   
    """ Represents a port that will send data to max"""
    def __init__(self):
        self.currentMidiPort = -1 # not used in MaxPort
        self.latency = 1000 # used by pypm to specify MIDI latecny, does not seem to have any effect
        self.midiOut = None
        self.pyext = None #if we are in a Max environment, this will be set to pyext.MaxPyExt()
        self.csound = csnd6.Csound()
        self.startTime = datetime.datetime.now()
        self.performance = None

    def Open(self, csdFile):
        print ( "CSoundPort:Open")
        self.startTime = datetime.datetime.now()
        if(csdFile is None):
            res = self.csound.CompileCsdText(defaultCSD)
        else:
            res = self.csound.Compile(csdFile)

        self.performance = csnd6.CsoundPerformanceThread(self.csound)
        self.csound.Start()
        self.performance.Play()

    def Close(self):
        print ("CSoundPort:Close")
        self.performance.Stop()
        self.performance.Join()
        self.csound.Stop()

    def PrintDevices(self, InOrOut):
        print (csnd6.version_info)

    def NoteOut(self, params):
        '''' this will send a note to our csound port'''
        timestamp = self.GetTime()
        #print 'CSoundPort:NoteOut {0}, {1}'.format(timestamp, params.Print())
        self.csound.InputMessage("i1 0 .5")

    def CtrlOut(self, params):
        timestamp = self.port.GetTime() #use portMidi for timing
        ctrlStr = 'note {0} {1} {2}'.format(params.ctrl, params.data, params.chan)
        if(self.pyext != None):
            self.pyext.Write([[[eMidiCommands.CNTRL, params.ctrl, params.data], timestamp]])     # send control
        else:
            print ('control: {0}'.format(ctrlStr))


    def GetTime(self):
        deltaTime = datetime.datetime.now() - self.startTime
        return deltaTime.total_seconds()*1000
	
#//////////////////////////////////////////////////////////////////////////////
def TestMidiPolyphony(port):
    midiStream = MIDIStreamRT(port)    
    note = midiStream.NoteEvent2

    midiStream.Start()
    
    for i in range(0, 3):
        note(60, 100, 1, 1)
        note(64, 100, 1, 1)
        note(67, 100, 1, 1)
        time.sleep(2)
    
    midiStream.WaitForStreamEnd()
    midiStream.Stop()    
    
    
#//////////////////////////////////////////////////////////////////////////////
def TestCsoundPolyphony(port):
    msgStream = MessageStreamRT(port)    
    note = msgStream.NoteEvent2

    msgStream.Start()
    
    for i in range(0, 3):
        note(60, 100, 1, 1)
        note(64, 100, 1, 1)
        note(67, 100, 1, 1)
        time.sleep(2)
    
    msgStream.WaitForStreamEnd()
    msgStream.Stop()    
    
def TestNotes(midiPort):
    
    midiStream = MIDIStream(midiPort)    
    note = midiStream.NoteEvent
    
    note(0, 60, 100, 8, 1)
    note(1, 64, 100, 1, 1)
    note(2, 67, 100, 1, 1)
    note(3, 72, 100, 1, 1)
    midiStream.SyncEventList()
    midiStream.Start()
    
    midiStream.WaitForStreamEnd()
    midiStream.Stop()    
    
    
def TimingTest(midiPort):
    print ("start: {0}".format(midiPort.GetTime()))
    for x in range(10):
        time.sleep(1)
        print (midiPort.GetTime())
    

def TestMidiPort():
    midiPort = MIDIPort()    
    midiPort.PrintDevices(OUTPUT)
    midiPort.OpenNamed("IAC Driver Virtual MIDI Port 1")
    TestMidiPolyphony(midiPort)
    midiPort.Close()    

def TestCSoundPort():
    csport = CSoundPort()    
    #csport.Open(None)
    csport.Open("pytest3.csd")
    TestCsoundPolyphony(csport)
    csport.Close()   

#//////////////////////////////////////////////////////////////////////////////

if __name__ == '__main__':
        
    testCase = '0'
    print ('IO Port Test')
    testCase = input("Select 1:MIDI port, 2:Csound port... ")
    
    if(testCase == '1'):
	    TestMidiPort()
    else:
	    TestCSoundPort()
        
    print("test complete.")

    




    