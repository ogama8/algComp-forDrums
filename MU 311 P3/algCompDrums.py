######################################################################################
# A program to make variations on drum loops using Markov Chains and other algorithms
# Eli Backer - MU 311 - Project 3 - Fall 2012
# Many thanks to EmergentMusics for their great midiUtil package
######################################################################################

import os
import sys
import random

from midiutil.MidiFile import MIDIFile

# Define "constants"
NUM_VARS = 64           # The number of variations on the beat produced
BEATS_PER = 4           # The top-half of a time signature.  The number of beats in a bar.
BAR_DIV = 4             # The bottom-half of a time signature.  The note value that gets one beat.
BREAK_EVERY = 8         # How many bars before a break is produced      For 4/4:    8 is good      For the Amen: 4

CM_MULT = 2             # Multiplier for the CM Matrix.                                                  2 is good 
CM_PLUS = 11            # Adder for the CM Matrix.  Raises the likelyhood of low chance beats.          11 is good
CM_DIV = 20             # Divisor for the CM Matrix.  Make sure that 4*CM_MULT+CM_PLUS / CM_DIV <= 1    20 is good
SWING = 1/2**4.0        # Of the form "1.0/2**[floating_number]" 
                        # Any value for [number] lower than 3.0 will not have the intended effect.

# These are all functions used in the main of the code.  They are here because python does not have function prototypes.
def name_to_num(string):
    """
    Given the name of a note (C is natural, c is sharp, etc) and an octave
    returns the corrisponding note number.  Ex. C4 -> 60
    """
    letters = ["C", "c", "D", "d", "E", "F", "f", "G", "g", "A", "a", "B"]
    for i in range(len(letters)):
        if string[0] == letters[i]:
            return (int(string[1:])+2)*12 +i
            
def matrix_sum(m1, m2):
    """
    Given matrices m1 and m2 of equal dimention, returns their sum.  ie. returnM[0][0] = m1[0][0] + m2[0][0]
    """
    ret = []
    for i in range(len(m1)):
        sub = []
        for j in range(len(m1[i])):
            sub.append(m1[i][j]+m2[i][j])
        ret.append(sub)
        
    return ret

def prob_matrix(input, mult, plus, div):
    """
    Given a 2d array of 1's and 0's produces a matrix of values from 0 to 1 of how likely it is that a
    sound be played at that given time.
    mult is the multiplier of the base values found
    plus is the number added to base*mult to raise the chance of non-specified beats
    div is the divisor to scale the values between 0 and 1 inclusive
    """
    cm = []
    for q in input:
        sub = []
        for y in range(BEATS_PER):
            sub.append(sum(q[y + (z)*BEATS_PER] for z in range(barLen/BEATS_PER)))
        cm.append(sub)
    
    return [[(y*mult + plus) / float(div) for y in t] for t in cm]
    

# The main code is here.
if __name__ == '__main__':
    if len(sys.argv) == 2:      # If there is a file name after the code is run, use it.
        f = sys.argv[1]
    else:                       # Otherwise just use this one.
        f = 'drumPattern.txt'

    # Convert table format binary data represented as ASCII into python 2d list, 
    # filtering out any character that is not 0 or 1
    dm = [map(int, filter(lambda s: s in '01', t)) for t in open(f, 'r').readlines()]
    
    # This defines the constants based on the file we read in.
    numDrums = len(dm)
    barLen = len(dm[0])

    # This makes sure that we don't have any errors the first time through the loop.
    dmc = [[q for q in y] for y in dm]
    dm1 = [[q for q in y] for y in dm]
    dm4 = [[q for q in y] for y in dm]
    
    cm = prob_matrix(dm, CM_MULT, CM_PLUS, CM_DIV)
    
    # Create the MIDIFile Object
    myMIDI = MIDIFile(1)
    
    
    # Add track name and tempo. The first argument to addTrackName and
    # addTempo is the time to write the event.
    track = 0
    time = 0
    myMIDI.addTrackName(track, time, "Algorithmic Drums")
    myMIDI.addTempo(track, time, 110)
    
    # Constants for all the notes
    channel = 0
    basePitch = name_to_num("C1")
    duration = 1
    volume = 127
    
    # Now add the notes.
    for loop in range(NUM_VARS):
        """ This conditional makes a break every BREAK_EVERY bar by shifting the probability of notes being 
        played over by 2.
        cm is still masked by dm which ultimately determines whether a note is played
        This conditional also copies the current state of dmc so that the probabilites for bar 1 can be those
        just before the break so the break does not "bleed" into bar one.  The state going into bar 1 saved into
        dm4 and replaced by dm1 (the state before bar BREAK_EVERY.)  Bar BREAK_EVERY/2 has a miniature break 
        created by the original state of bar 1 being fed into dmc before cm is calculated.
        """
        if(loop % BREAK_EVERY == BREAK_EVERY-1):
            dm1 = [[q for q in y] for y in dmc]         # We'll hold onto this state so bar 1 starts normaly.
            cm = matrix_sum(prob_matrix(dmc, CM_MULT, CM_PLUS, CM_DIV*4), prob_matrix(dm, CM_MULT, CM_PLUS, CM_DIV*4))
            """
            This doosie of a one-liner takes the first half and last half of a row in cm and switches them,
            increasing the probability of a pause, then drums.
            """
            cm = [a[1]+a[0] for a in [[r[0 + (BEATS_PER/2 * i):BEATS_PER/2 + (BEATS_PER/2 * i)] for i in range(2)] for r in cm]]
        else:
            if(loop % BREAK_EVERY == 0):
                dm4 = [[q for q in y] for y in dmc]     # Hold this for bar four.
                dmc = [[q for q in y] for y in dm1]     # Make bar one normal.
            elif(loop % BREAK_EVERY == BREAK_EVERY/2 - 1):
                dmc = [[q for q in y] for y in dm4]     # Make bar four a little strange.
            cm = matrix_sum(prob_matrix(dmc, CM_MULT, CM_PLUS, CM_DIV*2), prob_matrix(dm, CM_MULT, CM_PLUS, CM_DIV*2))
        
        for i in range(numDrums):
            for j in range(barLen):
                # By always using dm here we ensure that the beat does not die out and that we stay close to the original
                if dm[i][j] == 1 and cm[i][j%BEATS_PER] > random.random():
                    if j % 2 == 0:
                        myMIDI.addNote(track, channel, basePitch+i, loop*barLen/BEATS_PER + j/float(BAR_DIV), duration/float(BAR_DIV) + SWING, volume)
                    else:
                        myMIDI.addNote(track, channel, basePitch+i, loop*barLen/BEATS_PER + j/float(BAR_DIV) + SWING, duration/float(BAR_DIV) - SWING, volume)
                    dmc[i][j] = 1
                else:
                    dmc[i][j] = 0
    
    # Write it to disk.
    binfile = open("output.mid", 'wb')
    myMIDI.writeFile(binfile)
    binfile.close()
