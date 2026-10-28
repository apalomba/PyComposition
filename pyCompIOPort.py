try:
    import rtmidi
except:
    print('Failed to import rtmidi')
    
try:
    from libcsound import *
except ImportError:
    print('Failed to import libcsound.')

import time
import EventScheduler
import datetime
import platform

INPUT = 0
OUTPUT = 1

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


# //////////////////////////////////////////////////////////////////////////////
# ENUMS
class eMidiCommands:
    NOTE_OFF = 0x80
    NOTE_ON = 0x90
    AFTER_TOUCH = 0xA0
    CNTRL = 0xB0  # Continuous controller
    PATCH = 0xC0  # Patch change
    CHAN_PRESSURE = 0xD0  # Channel Pressure
    PITCH_BEND = 0xE0  # Pitch bend
    MISC_COMMAND = 0xF0  # (non-musical commands)


class ePortType:
    """ Enum class that enumerates our output ports """
    NONE = object()
    MIDI = object()
    OSC = object()
    DAC = object()
    FILE = object()
    CSOUND = object()


class eEventParams:
    '''Enum of note parameters'''
    TIME = 0
    DUR = 1
    EVENT_PARAMS = 2


# //////////////////////////////////////////////////////////////////////////////
class NoteParams:
    ''' encapsulates our note parameters '''

    def __init__(self, key, vel, chan):
        self.key = key
        self.vel = vel
        self.chan = chan

    def Print(self):
        return '(key: {0}, vel: {1}, chan: {2})'.format(self.key, self.vel, self.chan)


# //////////////////////////////////////////////////////////////////////////////
class ControlParams:
    """ encapsulates our control parameters """

    def __init__(self, ctrl, data, chan):
        self.ctrl = ctrl
        self.value = data
        self.chan = chan

    def Print(self):
        return '(cntrl: {0}, value: {1}, chan: {2})'.format(self.ctrl, self.value, self.chan)

# //////////////////////////////////////////////////////////////////////////////


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

        # go through and find where in time we should insert this note
        noteParams = eventParams[eEventParams.EVENT_PARAMS]
        noteTime = eventParams[eEventParams.TIME]
        for ev in self.theQ:
            curTime = ev[eEventParams.TIME]
            if (curTime > noteTime):
                self.theQ.insert(0, eventParams)  # insert in front of
                bFound = True
                break;
                # Insert an item at a given position. The first argument is the index of the
                # element before which to insert, so a.insert(0, x) inserts at the front of the list
        if (bFound == False):
            self.theQ.append(eventParams)  # just add to end

        # self.DumpEvents()

    def GetFirstEvent(self):
        ''' will return the next note that needs to be played '''
        if (self.isEmpty()):
            return None
        else:
            return self.theQ[eEventParams.TIME]

    def RemoveEvent(self):
        ''' will remove the first note (oldest) note in the queue '''
        self.theQ.pop(0)

    def Flush(self):
        ''' remove all notes from queue '''
        self.theQ = []

    def SortEvents(self):
        self.theQ = sorted(self.theQ, key=lambda param: param[eEventParams.TIME])  # sort on time
        # convert absolute duration of note to relative duration of event
        for i in range(0, len(self.theQ) - 1):
            event1 = self.theQ[i]
            event2 = self.theQ[i + 1]
            time1 = event1[eEventParams.TIME]
            time2 = event2[eEventParams.TIME]
            event1[eEventParams.DUR] = time2 - time1

    def isEmpty(self):
        if (len(self.theQ) == 0):
            return True
        else:
            return False

    def Count(self):
        return len(self.theQ)

    def DumpEvents(self):
        for params in self.theQ:
            time = params[eEventParams.TIME]
            dur = params[eEventParams.DUR]
            event = params[eEventParams.EVENT_PARAMS]
            # print "The sum of 1 + 2 is {0}".format(1+2)
            # print 'We are the {} who say "{}!"'.format('knights', 'Ni')
            print('time: {0},  dur:{1}, event: {2}'.format(time, dur, event.Print()))
            # print 'time: ' +  time ' event: ' + event

    def PrintEvent(self, event=[]):
        liststr = ''
        for value in event:
            liststr += (value + " ")
        return liststr


# //////////////////////////////////////////////////////////////////////////////
class IOPort():
    """ Base class of our output port """

    def __init__(self, portType):
        if (property == ePortType.MIDI):
            self = MIDIPort()
        elif (property == ePortType.CSOUND):
            self = CSoundPort()
        else:
            raise Exception('Unknown i/o port specified')
        pass

    def Open(self):
        print("OutputPort:Open")

    def Close(self):
        print("OutputPort:Close")


# //////////////////////////////////////////////////////////////////////////////
class MIDIPort(IOPort):
    """ Represents our MIDI Port: uses portmidi"""

    def __init__(self):
        self.currentMidiPort = 0  # should be MS MIDI Mapper
        self.latency = 0  # used by pypm to specify MIDI latecny, does not seem to have any effect
        self.midiOut = rtmidi.MidiOut()
        self.bOpen = False
        self.availablePorts = self.midiOut.get_ports()
        self.startTime = datetime.datetime.now()

    def __del__(self):
        del self.midiOut

    # opens MIDI ports with specified name 
    def OpenNamed(self, portName):
        portNum = 0
        cleanPortName = ""
        self.startTime = datetime.datetime.now()
        for systemPort in self.availablePorts:

            cleanPortName = systemPort
            # windows appends an integer on the end of the midi portname, we will remove it
            if (platform.system() == 'Windows'):
                cleanPortName = systemPort[:systemPort.rfind(' ')]

            if cleanPortName == portName:
                self.currentMidiPort = portNum
                self.midiOut.open_port(portNum)
                print("MIDIPort:Open " + systemPort)
                self.bOpen = True
                break
            portNum += 1

        if (self.bOpen == False):
            raise Exception("Could not open specified MIDI port")

    def Open(self, portNum=0):
        self.startTime = datetime.datetime.now()
        if (portNum >= len(self.availablePorts)):
            print("Specified midi port is beyond physical range.")
            return

        self.currentMidiPort = portNum
        self.midiOut.open_port(portNum)
        print("MIDIPort:Open")
        self.bOpen = True

    def Close(self):
        if (self.midiOut != None):
            print("MIDIPort:Close")
        self.bOpen = False

    def PrintDevices(self, InOrOut):
        for systemPort in self.availablePorts:
            print(systemPort)

    def SetPortID(self, portID):
        self.currentMidiPort = portID

    def NoteOut(self, params):
        '''' this will send a note out our midi port'''
        timestamp = self.GetTime()
        note_message = [0x90, (int)(params.key), (int)(params.vel)]  # channel 1, note, velocity
        self.midiOut.send_message(note_message)

    def ControlOut(self, params):
        timestamp = self.GetTime()
        control_message = [0xB0, (int)(params.ctrl), (int)(params.value)]  
        self.midiOut.send_message(control_message)

    def GetTime(self):
        deltaTime = datetime.datetime.now() - self.startTime
        return deltaTime.total_seconds() * 1000


# //////////////////////////////////////////////////////////////////////////////
class MaxPort(IOPort):
    """ Represents a port that will send data to max"""

    def __init__(self):
        self.currentMidiPort = -1  # not used in MaxPort
        self.latency = 1000  # used by pypm to specify MIDI latecny, does not seem to have any effect
        self.midiOut = None
        self.pyext = None  # if we are in a Max environment, this will be set to pyext.MaxPyExt()

    def Open(self):
        print("MaxPort:Open")

    def Close(self):
        print("MaxPort:Close")

    def PrintDevices(self, InOrOut):
        pass

    def SetPortID(self, portID):
        pass

    def NoteOut(self, params):
        '''' this will send a note out our midi port'''
        # timestamp = self.midiOut.Time()
        # print 'NoteOut: {0}, {1}'.format(timestamp, params.Print())
        # self.midiOut.Write([[[0x90, params.key, params.vel], timestamp]])     # send note
        # self.midiOut.WriteShort(0x90, (int)(params.key), (int)(params.vel))
        noteStr = 'note {0} {1} {2}'.format(params.key, params.vel, params.chan)
        # self._outlet(1, noteStr)
        if self.pyext is not None:
            self.pyext.NoteOut(noteStr)
        else:
            print('note: {0}'.format(noteStr))

    def CtrlOut(self):
        pass

    def GetTime(self):
        pass

# //////////////////////////////////////////////////////////////////////////////
class CSoundPort(IOPort):
    """ Represents a port that will send data to max"""

    def __init__(self, options = '-odac0'):
        self.currentMidiPort = -1  # not used in MaxPort
        self.latency = 1000  # used by pypm to specify MIDI latecny, does not seem to have any effect
        self.midiOut = None
        self.pyext = None  # if we are in a Max environment, this will be set to pyext.MaxPyExt()
        self.csound = Csound()
        # Output to the default audio device, using the default audio backend
        self.csound.setOption(options)
        self.startTime = datetime.datetime.now()
        self.performance = None

    def Open(self, csdFile):
        print("CSoundPort:Open")
        self.startTime = datetime.datetime.now()
        if (csdFile is None):
            res = self.csound.compileCsdText(defaultCSD)
        else:
            res = self.csound.compile(csdFile)

        self.performance = self.csound.performanceThread()
        self.csound.start()
        self.performance.play()

    def Close(self):
        print("CSoundPort:Close")
        self.performance.stop()
        self.performance.join()
        self.csound.stop()

    def PrintDevices(self, InOrOut):
        print(self.csound.version_info)

    def NoteOut(self, params):
        '''' this will send a note to our csound port'''
        timestamp = self.GetTime()
        # print 'CSoundPort:NoteOut {0}, {1}'.format(timestamp, params.Print())
        self.csound.inputMessageAsync("i1 0 1")

    def ControlOut(self, params):
        # In csound we don't use control messages, we use pfields to pass values in to our instrument 
        #timestamp = self.GetTime()  # use portMidi for timing
        #ctrlStr = 'i1 0 .5 ' + str(params.value) # this will send the control message to csound
        #self.csound.inputMessage(ctrlStr)
        pass

    def GetTime(self):
        deltaTime = datetime.datetime.now() - self.startTime
        return deltaTime.total_seconds() * 1000


# //////////////////////////////////////////////////////////////////////////////

if __name__ == '__main__':

    print("Port Test\n Select 1 for MIDI or 2 for CSound    ")
    print("Enter your choice: ")
    choice = input()
    if choice == "1":
        port = MIDIPort()
        port.OpenNamed("IAC Driver Bus 1")
        port.NoteOut(NoteParams(60, 100, 1))
        port.ControlOut(ControlParams(1, 110, 1))
        time.sleep(1)
        port.NoteOut(NoteParams(60, 0, 1))
    elif choice == "2":
        port = CSoundPort("-odac1")
        port.Open(None)
        time.sleep(1)
        port.NoteOut(NoteParams(60, 100, 1))
        time.sleep(1)

    port.Close()