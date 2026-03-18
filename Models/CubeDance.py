# -*- coding: utf-8 -*-
import networkx as nx
from music21 import chord as m21chord
import matplotlib.pyplot as plt
import random


class DraggableGraph:
    def __init__(self, graph, pos, ax):
        self.graph = graph
        self.pos = pos
        self.ax = ax
        self.selected_node = None
        self.cids = []
        self.connect()
        self.draw()

    def connect(self):
        self.cids.append(self.ax.figure.canvas.mpl_connect('button_press_event', self.on_press))
        self.cids.append(self.ax.figure.canvas.mpl_connect('button_release_event', self.on_release))
        self.cids.append(self.ax.figure.canvas.mpl_connect('motion_notify_event', self.on_motion))

    def on_press(self, event):
        if event.inaxes != self.ax: return
        for node, (x, y) in self.pos.items():
            dist = (x - event.xdata)**2 + (y - event.ydata)**2
            if dist < 0.01:  # Threshold for clicking a node
                self.selected_node = node
                break

    def on_release(self, event):
        self.selected_node = None

    def on_motion(self, event):
        if self.selected_node is None or event.inaxes != self.ax: return
        self.pos[self.selected_node] = (event.xdata, event.ydata)
        self.draw()

    def draw(self):
        self.ax.clear()
        nx.draw(self.graph, self.pos, ax=self.ax, with_labels=True, node_color='lightblue', font_weight='bold', node_size=2000)
        self.ax.set_title("Cube Dance Graph")
        self.ax.figure.canvas.draw_idle()


class CubeDance(object):
    """ Python class definition of Douthett and Steinbach’s Cube Dance"""
        
    def __init__(self):
        self.chordGraph = nx.Graph()
        self.chords = {}
        self.chord_opposites = {
        # Augmented Nodes (Tritone pairs)
        "Ab+": "D+", "D+": "Ab+",
        "B+": "F+",  "F+": "B+",
        
        # Top Right (TR) <-> Bottom Left (BL)
        "C": "Bbmi",   "Bbmi": "C",
        "Cmi": "F#",   "F#": "Cmi",
        "Ab": "F#mi",  "F#mi": "Ab",
        "Abmi": "D",   "D": "Abmi",
        "E": "Dmi",    "Dmi": "E",
        "Emi": "Bb",   "Bb": "Emi",
        
        # Top Left (TL) <-> Bottom Right (BR)
        "Db": "Bmi",   "Bmi": "Db",
        "Dbmi": "G",   "G": "Dbmi",
        "A": "Gmi",    "Gmi": "A",
        "Ami": "Eb",   "Eb": "Ami",
        "F": "Ebmi",   "Ebmi": "F",
        "Fmi": "B",    "B": "Fmi"
        }

        # Helper to create and register a chord
        def add_chord(name, notes):
            if isinstance(notes, str):
                notes = notes.split()
            c = m21chord.Chord(notes)
            self.chords[name] = c
            self.chordGraph.add_node(name, chord=c)

        # 1. Augmented Triads (Hubs)
        add_chord("Ab+", "A-3 C4 E4")
        add_chord("B+", "B3 D#4 G4")
        add_chord("D+", "D4 F#4 B-4")
        add_chord("F+", "F4 A4 C#5")

        # 2. Hexatonic Cycles (Cubes)

        # Top Right (Northern)
        add_chord("C", "C4 E4 G4")
        add_chord("Cmi", "C4 E-4 G4")
        add_chord("Ab", "A-3 C4 E-4")
        add_chord("Abmi", "A-3 B3 E-4") # B3 is Cb4 enharmonically? Wait, B3 is B natural. Cb4 is B3.
        # Original: "Ab3 B3 Eb4". Ab minor is Ab Cb Eb. Cb is B. So A-3 B3 E-4 is correct.
        add_chord("E", "E4 G#4 B4")
        add_chord("Emi", "E4 G4 B4")

        # Bottom Right (Eastern)
        add_chord("B", "B3 D#4 F#4")
        add_chord("Bmi", "B3 D4 F#4")
        add_chord("G", "G3 B3 D4")
        add_chord("Gmi", "G3 B-3 D4")
        add_chord("Eb", "E-4 G4 B-4")
        add_chord("Ebmi", "E-4 G-4 B-4")

        # Bottom Left (Southern)
        add_chord("Bb", "B-3 D4 F4")
        add_chord("Bbmi", "B-3 D-4 F4")
        add_chord("F#", "F#3 A#3 C#4")
        add_chord("F#mi", "F#3 A3 C#4")
        add_chord("D", "D4 F#4 A4")
        add_chord("Dmi", "D4 F4 A4")

        # Top Left (Western)
        add_chord("Db", "D-4 F4 A-4")
        add_chord("Dbmi", "D-4 F-4 A-4") # Fb is E. F-4 is Fb4.
        add_chord("A", "A3 C#4 E4")
        add_chord("Ami", "A3 C4 E4")
        add_chord("F", "F3 A3 C4")
        add_chord("Fmi", "F3 A-3 C4")

        # 3. Connect Edges

        # Helper to connect two chords by name
        def connect(name1, name2):
            self.chordGraph.add_edge(name1, name2)

        # Cycle 1: Top Right
        connect("C", "Cmi")
        connect("Cmi", "Ab")
        connect("Ab", "Abmi")
        connect("Abmi", "E")
        connect("E", "Emi")
        connect("Emi", "C")

        # Cycle 2: Bottom Right
        connect("B", "Bmi")
        connect("Bmi", "G")
        connect("G", "Gmi")
        connect("Gmi", "Eb")
        connect("Eb", "Ebmi")
        connect("Ebmi", "B")

        # Cycle 3: Bottom Left
        connect("Bb", "Bbmi")
        connect("Bbmi", "F#")
        connect("F#", "F#mi")
        connect("F#mi", "D")
        connect("D", "Dmi")
        connect("Dmi", "Bb")

        # Cycle 4: Top Left
        connect("Db", "Dbmi")
        connect("Dbmi", "A")
        connect("A", "Ami")
        connect("Ami", "F")
        connect("F", "Fmi")
        connect("Fmi", "Db")

        # Connect Augmented Triads to Cycles

        # Ab+ connects to Top Right Majors and Top Left Minors
        connect("Ab+", "C")
        connect("Ab+", "Ab")
        connect("Ab+", "E")
        connect("Ab+", "Fmi")
        connect("Ab+", "Ami")
        connect("Ab+", "Dbmi")

        # B+ connects to Bottom Right Majors and Top Right Minors
        connect("B+", "B")
        connect("B+", "G")
        connect("B+", "Eb")
        connect("B+", "Cmi")
        connect("B+", "Abmi")
        connect("B+", "Emi")

        # D+ connects to Bottom Left Majors and Bottom Right Minors
        connect("D+", "D")
        connect("D+", "F#")
        connect("D+", "Bb")
        connect("D+", "Bmi")
        connect("D+", "Gmi")
        connect("D+", "Ebmi")

        # F+ connects to Top Left Majors and Bottom Left Minors
        connect("F+", "F")
        connect("F+", "Db")
        connect("F+", "A")
        connect("F+", "Dmi")
        connect("F+", "F#mi")
        connect("F+", "Bbmi")

    def find_chord(self, chord_name):
        """
        Finds the chord in the graph and returns the music21 Chord object.
        Returns None if the chord is not found.
        """
        if isinstance(chord_name, str):
            if chord_name in self.chords:
                return self.chords[chord_name]
        
        return None

    def get_connected_chords(self, input_chord):
        """
        Finds the chord in the graph and returns a list of connected chords (names).
        Input: input_chord is a string or music21 Chord object
        Returns an str list of chords or empty list if the chord is not found.
        """
        chord_name = None
        if isinstance(input_chord, str):
            chord_name = input_chord
        else:
            for name, chord_obj in self.chords.items():
                if chord_obj is input_chord:
                    chord_name = name
                    break

        if chord_name in self.chords:
            return list(self.chordGraph.neighbors(chord_name))
        else:
            return []

    def visualize(self):
        """
        Visualizes the chordGraph using matplotlib.
        """
        pos = nx.spring_layout(self.chordGraph, k=0.2, seed=42)
        fig, ax = plt.subplots(figsize=(8, 8))
        self.draggable = DraggableGraph(self.chordGraph, pos, ax)
        plt.show()

    def find_opposite(self, chord_name):
        """
        Finds the opposite chord in the graph and returns the node name.
        Returns None if the chord is not found.
        """
        return self.chord_opposites.get(chord_name, None)

    def get_chord_pitches(self, chord):
        """
        Input: chord is a music21 Chord object
        Returns a list of pitches in the chord.
        """
        return [p.nameWithOctave for p in chord.pitches]

# ////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
if __name__ == '__main__':

    print('Cube Dance Test')
    cube_dance = CubeDance()

    cdance = CubeDance()
    current_chord = "C"
    new_chord = cdance.find_chord(current_chord)
    chord_pitches = new_chord.pitches
    connected_chords = cdance.get_connected_chords(current_chord)
    random_chord = random.choice(connected_chords)

    print("Chord: " +  new_chord.root().name +  " (" + str(type(new_chord)) + ")")
    print("Pitches: " +  str(cdance.get_chord_pitches(new_chord)))    
    print("Connected chords: " + str(connected_chords))
    print("Opposite Chord: " + cdance.find_opposite("C"))
    print("Random Chord: " + random_chord)
    #cdance.visualize()

