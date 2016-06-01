import math
import wave
import struct
import random
FRAMERATE=11025

import time
start=time.clock()

class Signal(object):
    def __init__(self,val):
        self.val=val
        
    def amplify(self,const):
        self.val = [const*i for i in self.val]

    def append(self,other):
        self.val+=other.val

    def __add__(self,other):
        arr=[self.val[i] + other.val[i] for i in range(len(self.val)) ]
        return Signal(arr)

    def __mul__(self,other):
        #multiply two signals together elementwise
        if type(other)==Signal:
            arr=[ self.val[i]*other.val[i] for i in range(len(self.val)) ]
            return Signal(arr)
        #multiply signal by scalar
        elif (type(other)==float or type(other)==int):
            arr=[ other*self.val[i] for i in range(len(self.val)) ]
            return Signal(arr)
    def __rmul__(self,other):
        return other*self
    
    def save_wave(self,fname="testfile.wav"):
        amp =max( max(self.val), abs(min(self.val)) )

        sounds=[int(i*127*256/amp*0.9) for i in self.val]
        file = wave.open(fname,"w")
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(FRAMERATE)

        for i in sounds:
            inHex = struct.pack('h',i)
            file.writeframes(inHex)
        file.close()



"""
Functions that return commonly shaped signals
"""
def Sine_Sig(frames,inc,amp=1):
    arr=[amp*math.sin(inc*i) for i in range(frames) ]
    return Signal(arr)

def Linear_Sig(frames,start,end): # values is [start , end)
    inc = (end-start)/frames
    arr = [ start + inc*i for i in range(frames)]
    return Signal(arr)

def FM_Sig(frames,theta,alpha,beta):
    #theta/alpha/beta/amp must be signals or scalars(which represent cons sigs)

    #set theta/alpha/beta to lists of appropriate size
    theta = theta.val if type(theta)==Signal else [theta]*frames
    alpha = alpha.val if type(alpha)==Signal else [alpha]*frames
    beta = beta.val if type(beta)==Signal else [beta]*frames
    arr=[math.sin( theta[i]*i + alpha[i]*math.sin(beta[i]*i)) for i in range(frames)]
    return Signal(arr)

def Exp_Decay(frames,amp,frame_tau):
    arr=[amp*math.exp(-i/frame_tau/FRAMERATE) for i in range(frames)]
    return Signal(arr)

def Rand_Sig(frames): #in range [-1,1]
    arr=[random.random()*2-1 for i in range(frames)]
    return Signal(arr)



class Note(object):
    def __init__(self,name,amp,start,time,end):
        self.name=name
        self.start=start
        self.time=time
        self.end=end
        self.amp=amp
        self.sig=None

class Song(object):
    def __init__(self,bpm):
        #sheet is a 2d list of tuples
        self.notes=[]       #List of notes
        self.sig=Signal([]) #Final Song
        self.spb=60/bpm     #seconds per beat


            
    def play(self,instrument,sheet):
        #calculate meta-data on each note
        #and signal of note when played by given instrument
        #then add to self's list of notes
        beat_num=0
        for beat in sheet:
            num_notes = len(beat)
            sec_p_note = self.spb/num_notes
            for i in range(num_notes):
                key   = beat[i][0]
                amp   = beat[i][1]
                start = (beat_num+i/num_notes)*self.spb
                time  = instrument.dur
                end   = instrument.dur + start
                note  = Note(key,amp,start,time,end)
                note.sig = instrument.play_note(note)
                self.notes.append(note)
            beat_num+=1

    #compose signals (at different starting times) into one signal
    #stores signal in self.sig
    def compose(self):
        start=0
        end=0
        for note in self.notes:
            if note.end>end:
                end=note.end
        frames=int(FRAMERATE*end)
        self.sig=Signal([0]*frames)
        count =0
        for note in self.notes:
            offset = int(FRAMERATE*note.start)
            for i in range(len(note.sig.val)):
                try:
                    self.sig.val[i+offset]+=note.sig.val[i]
                except:
                    #some index off by something error is in this code
                    print(len(self.sig.val),i+offset)
                    print(len(note.sig.val),i)
                    print("\n")
                    break
    
    
            



class Instrument(object):
    def __init__(self):
        self.notes={}    #dic of signals of notes that had been computed
        self.freqdic={   #dic of frequencies relative to a4
            "c2":0.1486,"d2":0.1668,"e2":0.1872,"f2":0.1984,"g2":0.2227,
            "a2":0.2500,"b2":0.2806,"c3":0.2973,"d3":0.3337,"e3":0.3745,
            "f3":0.3968,"g3":0.4454,"a3":0.5000,"b3":0.5612,"c4":0.5946,
            "d4":0.6674,"e4":0.7491,"f4":0.7937,"g4":0.8909,"a4":1,
            "b4":1.1224,"c5":1.1892,"d5":1.3348,"e5":1.4983,
            "f5":1.5874,"g5":1.7818,"a5":2,"b5":2.2449,"r":0,
        }
        
    #def play_note(self,note):
        #needs to return a signal based on the note
        #should have frames=int(self.dur*FRAMERATE)

 
class FM_Instrument(Instrument):
    def __init__(self,theta,alpha,beta,env,dur):
        self.theta=theta #sig
        self.alpha=alpha #sig
        self.beta =beta  #sig
        self.env  =env   #sig
        self.dur  =dur   #time (sec)
        self.sig  ={}
        Instrument.__init__(self)
        

    #returns Signal of note played by instrument
    #when possible uses instrument's dicionary of earlier
    #computed signals to speed up computacion.
    def play_note(self,note):
        sig = self.sig.get(note.name,None)
        frames=int(FRAMERATE*self.dur)
        
        #Calculate note if not already computed
        if sig==None:
            notemod = self.freqdic[note.name]
            theta = self.theta*notemod
            alpha = self.alpha
            beta  = self.beta *notemod
            fm = FM_Sig(frames,theta,alpha,beta)
            fm*=self.env
            self.notes[note.name]=fm
            sig=fm
        #sig = a Signal object
        return Signal( [sig.val[i]*note.amp for i in range(frames)] )

def Gong_Like(fc,fm,I0,dur,amp_tau,ind_tau):
    conv = 2*math.pi/FRAMERATE
    frames = int(dur*FRAMERATE)
    
    theta = Linear_Sig(frames,fc*conv,fc*conv)
    alpha = Exp_Decay(frames,I0,ind_tau)
    beta  = Linear_Sig(frames,fm*conv,fm*conv)
    env   = Exp_Decay(frames,1,amp_tau)
    return FM_Instrument(theta,alpha,beta,env,dur)

def Pluck(theta,a0,a1,beta,dur=0.5):
    conv=2*math.pi/FRAMERATE
    frames=int(FRAMERATE*dur)
    theta = Signal([theta*conv]*frames)
    alpha = Signal(Linear_Sig(frames//2,a0,a1).val+Linear_Sig(frames-frames//2,a1,a1).val)
    beta = Signal([beta*conv]*frames)
    env=(Exp_Decay(frames,1,0.125))
    return FM_Instrument(theta,alpha,beta,env,dur)    

def Pluck_Env2(theta,a0,a1,beta,dur=1):
    frames=int(FRAMERATE*dur)
    mayo = Mayo(theta,a0,a1,beta,dur)
    arr=[1-math.exp(-i/FRAMERATE/0.25) for i in range(frames)]
    env=Signal( [arr[i]*arr[-1-i] for i in range(frames)] )
    env*=1/max(-min(env.val),max(env.val))
    mayo.env = env
    return mayo





pluck1 = Pluck(700,5,2.5,700)
#gong = Gong_Like(85,65,15,2,0.25,0.5)

hot_cross=[
    [("b4",1),("a4",1),("g4",1),("r",1)],
    [("b4",1),("a4",1),("g4",1),("r",1)],
    [("b4",1),("b4",1),("b4",1),("b4",1),("g4",1),("g4",1),("g4",1),("g4",1)],
    [("b4",1),("a4",1),("g4",1),("r",1)],
]

song=Song(30)
song.play(pluck1,hot_cross)
song.play(gong,hot_cross)
song.compose()
song.sig.save_wave("hot.wav")
