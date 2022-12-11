from pyCompIOPort import *
import threading


# //////////////////////////////////////////////////////////////////////////////
class MIDIStream(threading.Thread):
    def __init__(self, Port, realTime=False):
        ''' MIDIStream: (Port: midi port to use, realTime: process events in real time'''
        super().__init__(self)
        self.midiPort = Port  # reference to the port we will be using for output
        self.midiEventQ = MIDIEventQueue()
        self.bStop = False
        self.bRealTimeOutput = realTime
        self.lastEvent = None

    def run(self):
        ''' this is our event thread, it process all our midi events'''
        # print 'MIDIStream: run thread ({0})...'.format(self.midiPort .GetTime())
        while (self.bStop == False):
            if (self.midiEventQ.isEmpty() == False):
                if (self.bRealTimeOutput):
                    self.ProcessQ_RealTime()
                else:
                    self.ProcessQ_NonRealTime()

    def ProcessQ_Realtime(self):
        # print 'MIDIStream: ProcessQ_Realtime ({0})'.format(self.midiPort .GetTime())
        event = self.midiEventQ.GetFirstEvent()
        if (event != None):
            self.midiEventQ.RemoveEvent()  # remove this event from queue
            dur = event[eEventParams.DUR]
            params = event[eEventParams.NOTE_PARAMS]
            if (dur != 0):
                self.midiPort.NoteOut(params)  # send event
                threading._sleep(dur)  # go to sleep for duration of event
                params.vel = 0  # send note off
                self.midiPort.NoteOut(params)  # send event

    def ProcessQ_NonRealtime(self):
        event = self.midiEventQ.GetFirstEvent()
        if (event != None):
            time = event[eEventParams.TIME]
            dur = event[eEventParams.DUR]
            params = event[eEventParams.NOTE_PARAMS]
            self.midiPort.NoteOut(params)  # send event
            self.midiEventQ.RemoveEvent()  # remove this event
            if (dur != 0):
                threading._sleep(dur)  # go to sleep for duration of event

    def Start(self):
        bStop = False
        print('MIDIStream: start thread ({0})...'.format(self.midiPort.GetTime()))
        self.start()

    def Stop(self):
        self.bStop = True
        print('MIDIStream: stop thread ({0}), Q: {1}'.format(self.midiPort.GetTime(), self.midiEventQ.Count()))

    def NoteEvent(self, time=0.0, key=60, amp=100, dur=.5, chan=0):
        '''' will send a note out using the event scheduler. dur is in seconds
        time(ms) = 0.0, dur  = .5, key  = 60, amp  = .5, chan  = 0 '''
        timestamp = self.midiPort.GetTime()

        # add note on
        event = NoteParams(key, amp, chan)
        eventList = [time, dur, event]
        self.midiEventQ.AddEvent(eventList)

        if (self.bRealTimeOutput == False):
            # add note off
            event = NoteParams(key, 0, chan)
            eventList = [time + dur, 0, event]
            self.midiEventQ.AddEvent(eventList)

    def NoteEvent2(self, key=60, amp=100, dur=.5, chan=0):
        '''' will send a note out using the event scheduler. dur is in seconds. dur  = .5, key  = 60, amp  = .5, chan  = 0 '''
        timestamp = self.midiPort.Time()
        self.NoteEvent(timestamp, key, amp, dur, chan)

    def ControlEvent(self, time=0, ctrl=32, val=127, chan=0):
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
        while (self.isComplete() == False):
            time.sleep(.125)

    def send(self):
        pass


# //////////////////////////////////////////////////////////////////////////////
class MIDIStreamRT(threading.Thread):
    def __init__(self, Port):
        ''' MIDIStreamRT: (Port: midi port to use, realTime: process events in real time. Supports concurrent notes.)'''
        super().__init__()
        self.port = Port  # reference to the port we will be using for output
        self.midiEventQ = MIDIEventQueue()
        self.bStop = False
        self.lastEvent = None
        self.lock = threading.BoundedSemaphore()  # used to synchronize access to queue


    def run(self):
        ''' this is our event thread, it process all our midi events'''
        # print 'MIDIStreamRT: run thread ({0})...'.format(self.port .GetTime())
        while (self.bStop == False):
            self.ProcessQ()
            time.sleep(EventScheduler.ms2sec(10))  # sleep

    def ProcessQ(self):
        # get current time
        currentTime = self.port.GetTime()
        # print '+++ MIDIStream: ProcessQ ({0})\n'.format(portmidi.Time())
        # go through our midi event queue and sent messages that need to go
        self.lock.acquire()
        while (True):
            event = self.midiEventQ.GetFirstEvent()
            if (event == None):
                break  # queue is empty

            noteTime = event[eEventParams.TIME]
            if (noteTime <= currentTime):
                params = event[eEventParams.NOTE_PARAMS]
                self.port.NoteOut(params)  # send event
                self.midiEventQ.RemoveEvent()
            else:
                break  # no need to continue
        self.lock.release()

    def Start(self):
        bStop = False
        # print 'MIDIStreamRT: start thread ({0})'.format(self.port .GetTime())
        self.start()

    def Stop(self):
        self.Flush()
        self.bStop = True
        # print 'MIDIStreamRT: stop thread ({0}), Q: {1}'.format(self.port .GetTime(), self.midiEventQ.Count())

    def NoteEvent(self, time=0.0, key=60, amp=100, dur=.5, chan=0):
        '''' will send a note out using the event scheduler. dur is in seconds
        time(ms) = 0.0, dur  = .5, key  = 60, amp  = .5, chan  = 0 '''

        noteOn = NoteParams(key, amp, chan)
        self.port.NoteOut(noteOn)  # send note on

        # print ( '+++ MIDIStreamRT: NoteEvent ({0}, {1}, {2}, {3})\n'.format(time, key, amp, dur))

        # add note off
        event = NoteParams(key, 0, chan)
        eventList = [time + EventScheduler.sec2ms(dur), 0, event]
        self.lock.acquire()
        self.midiEventQ.AddEventTimeSorted(eventList)
        self.lock.release()

    def NoteEvent2(self, key=60, amp=100, dur=.5, chan=0):
        '''' will send a note out using the event scheduler. dur is in seconds. dur  = .5, key  = 60, amp  = .5, chan  = 0 '''
        timestamp = self.port.GetTime()
        self.NoteEvent(timestamp, key, amp, dur, chan)

    def ControlEvent(self, time=0, ctrl=32, val=127, chan=0):
        pass

    def Flush(self):
        pass

    def isComplete(self):
        return self.midiEventQ.isEmpty()

    def WaitForStreamEnd(self):
        while (self.isComplete() == False):
            time.sleep(.20)


# //////////////////////////////////////////////////////////////////////////////
class MessageStreamRT(threading.Thread):
    def __init__(self, Port):
        ''' MIDIStreamRT: (Port: midi port to use, realTime: process events in real time. Supports concurrent notes.)'''
        super().__init__(self)
        self.port = Port  # reference to the port we will be using for output
        self.midiEventQ = MIDIEventQueue()
        self.bStop = False
        self.lastEvent = None
        self.lock = threading.BoundedSemaphore()  # used to synchronize access to queue

    def run(self):
        ''' this is our event thread, it process all our midi events'''
        # print 'MIDIStreamRT: run thread ({0})...'.format(self.port .GetTime())
        while (self.bStop == False):
            self.ProcessQ()
            time.sleep(EventScheduler.ms2sec(10))

    def ProcessQ(self):
        # get current time

        currentTime = self.port.GetTime()
        # print '+++ MIDIStream: ProcessQ ({0})\n'.format(currentTime)

        # go through our midi event queue and sent messages that need to go
        self.lock.acquire()
        while (True):
            event = self.midiEventQ.GetFirstEvent()
            if (event == None):
                break  # queue is empty

            noteTime = event[eEventParams.TIME]
            if (noteTime <= currentTime):
                params = event[eEventParams.NOTE_PARAMS]
                self.port.NoteOut(params)  # send event
                self.midiEventQ.RemoveEvent()
            else:
                break  # no need to continue
        self.lock.release()

    def Start(self):
        bStop = False
        # print 'MIDIStreamRT: start thread ({0})'.format(self.port .GetTime())
        self.start()

    def Stop(self):
        self.Flush()
        self.bStop = True
        # print 'MIDIStreamRT: stop thread ({0}), Q: {1}'.format(self.port .GetTime(), self.midiEventQ.Count())

    def NoteEvent(self, time=0.0, key=60, amp=100, dur=.5, chan=0):
        '''' will send a note out using the event scheduler. dur is in seconds
        time(ms) = 0.0, dur  = .5, key  = 60, amp  = .5, chan  = 0 '''

        # print '+++ MIDIStreamRT: NoteEvent ({0}, {1}, {2}, {3})\n'.format(time, key, amp, dur)

        noteOn = NoteParams(key, amp, chan)
        self.port.NoteOut(noteOn)  # send note on

        # add note off
        event = NoteParams(key, 0, chan)
        eventList = [time + EventScheduler.sec2ms(dur), 0, event]
        self.lock.acquire()
        self.midiEventQ.AddEventTimeSorted(eventList)
        self.lock.release()

    def NoteEvent2(self, key=60, amp=100, dur=.5, chan=0):
        '''' will send a note out using the event scheduler. dur is in seconds. dur  = .5, key  = 60, amp  = .5, chan  = 0 '''
        timestamp = self.port.GetTime()
        self.NoteEvent(timestamp, key, amp, dur, chan)

    def ControlEvent(self, time=0, ctrl=32, val=127, chan=0):
        pass

    def Flush(self):
        pass

    def isComplete(self):
        return self.midiEventQ.isEmpty()

    def WaitForStreamEnd(self):
        while (self.isComplete() == False):
            time.sleep(.20)


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


# //////////////////////////////////////////////////////////////////////////////
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
    print("start: {0}".format(midiPort.GetTime()))
    for x in range(10):
        time.sleep(1)
        print(midiPort.GetTime())


def TestMidiPort():
    midiPort = MIDIPort()
    midiPort.PrintDevices(OUTPUT)
    midiPort.OpenNamed("IAC Driver Virtual MIDI Port 1")
    TestMidiPolyphony(midiPort)
    midiPort.Close()


def TestCSoundPort():
    csport = CSoundPort()
    # csport.Open(None)
    csport.Open("pytest3.csd")
    TestCsoundPolyphony(csport)
    csport.Close()


# //////////////////////////////////////////////////////////////////////////////

if __name__ == '__main__':

    testCase = '0'
    print('IO Port Test')
    testCase = input("Select 1:MIDI port, 2:Csound port... ")

    if (testCase == '1'):
        TestMidiPort()
    else:
        TestCSoundPort()

    print("test complete.")