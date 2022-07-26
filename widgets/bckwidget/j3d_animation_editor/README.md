# j3d-animation-editor
editor for a variety of j3d animation files. still a work in progress. any bugs can be reported to me on discord tarsa#8462.

# filetypes supported:

## j3d filetypes:
* .btk: texture srt key
* .brk: tev register key (integer values only)
* .bpk: color key (integer values only)
* .bck: joint key 
* .bca: joint all 
* .blk: cluster key 
* .bla: cluster all 
* .btp: texture palette all (integer values only)
* .bva: mesh visibility all (boolean values only)

## other filetypes:
* .anim: imports as .bck, can be exported from .bca or .bck
* .fbx: imports as .bck, can be exported from .bca or .bck
* .bvh: imports as .bck or as .bca
.fbx and .bvh import is still experimental and may be buggy.

All of these files can be opened by dragging a file onto the animation_editor.py file or the gui once the script is running.

# automatic operations
* can change between tangent types 0 (out tangent only) and 1 (in and out tangents)
* automatic tangent interpolation - can be linear or smooth depending on user choice
* conversion between key and all frame animations, where applicable
* yaz0 compression / decompression depending on user choice

# manual operations
* quick edit - to change multiple values at once based off a user-defined formula
* create new animation - to create a blank animation 
* mass animation editor - to edit all loaded files of a certain filetype
* frames editor - to add new frame columns to an existing animation

# config .ini file
* all but one option can be changed through the editor gui
* the "main_game" option needs to be set by the user. the game specific settings are as follows:
    * tww or tp enable the sound editor for .bck files
        * in the future, the editor will use game-specific names in the sound editor for the sound id
    * mkdd will make .bvh files be imported as .bca files
* if you mod another game, please let me know of any other game-specific options that should be involved

# run from source code:
the editor requires many libraries, the most important of which is PyQt5. this can be installed by 
`pip install PyQt5`

if you want .fbx support, the Autodesk Python FBX SDK (and Visual Studio Build Tools) need to be installed. More details about the FBX SDK installation can be found [here](https://gitlab.inria.fr/radili/fbxsdk_python).

# mass editing
the bones/materials/meshes in a mass editing .txt file should be in the same order that they appear in in the .bmd/.bdl

# instructions for maya users (from Skilar)
videos:
https://www.youtube.com/watch?v=sq3MA4Mtv9I
https://www.youtube.com/watch?v=0gEPX2dobKg
1: Make your animation using ripped model/skeleton
2: After your animation is done, select the most top bone that is know to be part of the characters armature. In this case, the bone name is center. Click it, and then go to select>Hierarchy. It is important you DO NOT select anything above that. For Link, there will be al_character or point000 (if you ripped using maxbmd), don not select!
3: Edit>keys>Bake simulation
4: Select the very top of the skeleton now, this time its okay since its for export. So select al_character, file>exportselection
5: select animExport (if you dont have this option, enable it in maya. Windows>settings/preferences/plug in manager)
6: In export settings under filetype specific options, make sure hierarchy is set to below. Name and export.
7: Open j3d-animation editor
8: Convert> Maya anim import. You can just click save after this and it will spit out your BCK

# special thanks:
* Yoshi2, from whom a lot of the animation reading / writing code, gui code, and yaz0 decompression is adapted
* NoClip.Website, which provided guidance on how to read/write certain file types (.brk, .bpk, .bva)
* fon-22, for providing .bva files to test with
* SuperHackio's Hack.io j3d scripts, which provided guidance on how to read certain file types (.bva)
* LagoLunatic's GCFT, for a yaz0 compression script
* BigSharkZ, for testing the script and suggesting new features
* Meyuelle, for the Peaches and Plums theme
* Skilar, for figuring out the process for maya users and being a test user
* Jasperr, for help in reading .bls files