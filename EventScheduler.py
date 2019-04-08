import threading
import uuid
import time

totalTime = 0

def ms2sec(mscount):
    ''' convert ms to sec '''
    return mscount/1000.0;
def sec2ms(sec):
    ''' convert sec to ms '''
    return sec*1000.0;

def TupleToList(tupleIn):
    ''' will convert a tuple to a list '''
    listOut = []
    for item in tupleIn:
        listOut.append(item)
    return listOut

        
class eProcessType:
    '''eProcessType: is an enum class that specifies different types of processes'''
    unknown=0
    Continuous=1
    Scheduled=2
  


class Process(threading.Timer):
    '''class Process encapsulates a behavior that will run'''
  
    def __init__(self, *args, **kwargs):
        #print "Process: __init__"
        threading.Timer.__init__(self, *args, **kwargs)
        
        #ARGS: interval, process, args, kwargs
        # make copy of our args so we can modify it
        argCopy = []
        for arg in args:
            argCopy.append(arg)
            
        self.WaitInterval = argCopy[0]
        self.args = TupleToList(argCopy[2]) #argCopy[2]
        self.ID = uuid.uuid1()
        self.setDaemon(True)
        self.bHalt = False
        self.elapsedTimed = 0
        
    def run(self):
        while (self.bHalt != True):
            if not self.finished.isSet():
                argTuple = tuple(self.args)
                self.WaitInterval = self.function(*argTuple)                  # function should return a new wait time
                self.elapsedTimed += self.WaitInterval                         # update accum time
                self.args[0] = self.elapsedTimed                                  # notify process of elapsed time
                if(self.WaitInterval == -1): # a wait time of -1 means that the process is done 
                    self.finished.set()
                    return
               
            if(self.WaitInterval != 0):    
                self.finished.wait(self.WaitInterval)     # wait is in seconds
            
class ProcessManager(object):

    ProcessQ = []
            
    def AddProcess(self, process, interval, args=[], kwargs={}):
        """ this will add a process to the process queueu. It will not start the process untill you call StartProcess"""
        p = Process(interval, process, args, kwargs)
        self.ProcessQ.append(p)
        return self.ProcessQ.index(p) + 1 # ID that is zero based makes no sense
        
    def SetWaitInterval(self, processID, time):
        ''' Sets wait interval that the thread will sleep'''
        if(processID > self.ProcessQ.count) :
            return
          
        p = (Process)(self.ProcessQ[processID-1])
        p.WaitInterval = time
        
    def IsActive(self, processID):
        ''' Returns the if this process is active or not'''
        p = (Process)(self.ProcessQ[processID-1])
        return p.finished.isSet()
        
    def GetProcess(self, processID):
        ''' Returns pointer to a Process with the specified ID'''
        if processID > self.ProcessQ.__len__():
            return None  
        return self.ProcessQ[processID-1]
    
    def StartProcess(self, processID):
        ''' spawns a new thread for process with process ID '''
        #print 'Process: StartProcess'
        p = self.GetProcess(processID)
        threading.Thread(target=p.run).start()

    def ResetProcess(self, processID):
        #print 'ResetProcess'
        p = self.GetProcess(processID)
        p.finished.clear()
        p.bHalt = False
        
        
    def StopProcess(self, processID):
        #print 'StopProcess'
        p = self.GetProcess(processID)
        p.cancel()
        p.finished.set()
        p.bHalt = True
    
    def StopAll(self):
        for p in self.ProcessQ:
            p.cancel()
            p.finished.set()
            p.bHalt = True
       # self._event.set()

        
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
        
def proc1(*args):
    print ("proc1: {0}".format(args[0]))
    return ms2sec(500)  #new wait time

if __name__ == '__main__':
    # Print "Hello World!" every 1 seconds
    
    elaspedTime = 0
    test = 0
    argList = [elaspedTime, test]
    
    pman = ProcessManager()
    pID = pman.AddProcess(proc1, 0, argList)    
    print ('Process ID: %i' % pID)
   
    print (' Starting process...')
    pman.StartProcess(pID)
    
    count = 0
    while (count < 5):
        time.sleep(1)
        count += 1

    print ('Stopping process')
    
    pman.StopProcess(pID)
           
    print ('Wait 3 seconds...')
    
    count = 0
    while (count < 3):
        time.sleep(1)
        count += 1

    print (' Starting process again...')
    pman.ResetProcess(pID)
    pman.StartProcess(pID)
   
    count = 0
    while (count < 5):
        time.sleep(1)
        count += 1
    
    print (' Stopping process...')
    pman.StopProcess(pID)
    print (' test complete')
      
    print (' Stopping process...')
    pman.StopProcess(pID)
    print (' test complete')
 