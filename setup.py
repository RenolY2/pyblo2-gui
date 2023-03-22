import sys
import os 
from cx_Freeze import setup, Executable
version = "0.7.0.1"
# Dependencies are automatically detected, but it might need fine tuning.

def files_from_folder(folder):
    return [(folder, x) for x in os.listdir(folder)]

#include_files = files_from_folder("resources/")
#include_files.extend(files_from_folder("object_templates"))
include_files = ["resources/", "lib/mkddobjects.json", "lib/music_ids.json", "lib/color_coding.json"]
build_exe_options = {
"packages": ["OpenGL", "numpy.core._methods", "numpy.lib.format"],
"includes": ["widgets"], 
"excludes": ["tkinter", "scipy", "PyQt5.QtWebEngine", "PyQt5.QtWebEngineCore"],
"optimize": 0,
"build_exe": "build/blo-gui-editor-v{}".format(version),
"include_files": include_files}

# GUI applications require a different base on Windows (the default is for a
# console application).
consoleBase = None
guiBase = None#"Win32GUI"
#if sys.platform == "win32":
#    base = "Win32GUI"

setup(  name = "Binary Layout Editor",
        version = version,
        description = "Binary Layout Editor",
        options={"build_exe": build_exe_options},
        executables = [Executable("blo_editor.py", base=guiBase, icon="resources/icon.ico")])