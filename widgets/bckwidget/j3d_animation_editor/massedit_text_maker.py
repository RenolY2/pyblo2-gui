import animations.general_animation as j3d
import struct
import argparse
import os
from re import match



def get_bones_from_bmd(bmd_file):
    strings = []
    with open(bmd_file, "rb") as f:
        s = f.read()
        a = s.find(b'\x4A\x4E\x54\x31')
        #print(a)
        f.seek(a + 0x14);
        address = j3d.read_uint32(f)
        #print(address)
        f.seek(address + a)
        strings = j3d.StringTable.from_file(f).strings;
        print("bones in bmd ", strings)
        f.close()
        
    return strings

def get_materials_from_bmd(bmd_file):
    strings = []
    with open(bmd_file, "rb") as f:
        s = f.read()
        a = s.find(b'\x4D\x41\x54\x33')
        #print(a)
        f.seek(a + 0x14);
        address = j3d.read_uint32(f)
        #print(address)
        f.seek(address + a)
        strings = j3d.StringTable.from_file(f).strings;
        print(strings)
        f.close()
        
    return strings 

def get_meshes_from_bmd( bmd_file):
    strings = []
    print("get mesh")
    with open(bmd_file, "rb") as f:
        s = f.read()
        a = s.find(b'\x53\x48\x50\x31')
        print(a)
        f.seek(a + 0x8);
        count = j3d.read_uint16(f)
        strings = [ "Mesh " + str(i) for i in range(count) ]
        print(strings)
        f.close()
        
    return strings



if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("input",
                        help="Filepath of the .bmd/.bdl to generate a .txt file for")
    parser.add_argument("filetype", default = "bck", nargs = '?',
                        help="The filetype that the .txt file will be used for")
    parser.add_argument("output", default=None, nargs = '?',
                        help="Output path of the created mass edit .txt file")

    args = parser.parse_args()
    
    
    
    input_model = args.input
    filetype = args.filetype
    output_txt = args.output
    
    if filetype.startswith("."):
        filetype = filetype[1:]
    
    
    if args.output is None:
        output = input_model + ".txt"
    else:
        output = args.output
    
    cats = []
    transforms = []
    
    if filetype in ["bck", "bca"]:
        cats = get_bones_from_bmd( input_model)
        
    elif filetype in ["btp", "brk", "bpk", "btk"]:
        cats = get_materials_from_bmd( input_model)
    elif filetype in ["blk", "bla", "bva"]:
        cats = get_meshes_from_bmd( input_model)
    else:
        raise Exception("Not a valid filetype")


    transforms = []
    if filetype in ["bck", "bca", "btk"]:
        transforms = ["Scale X:", "Scale Y:", "Scale Z:", "Rotation X:","Rotation Y:","Rotation Z:", "Translation X:", "Translation Y:", "Translation Z:"]
    elif filetype in ["brk", "bpk"]:
        transforms = ["Red:", "Green:", "Blue:", "Alpha:"]
    
    with open(output, "w") as f:
        f.write(filetype + "\n\n")
        for cat in cats:
            f.write(cat + "\n")
            if len(transforms) > 0:
                for trans in transforms:
                    f.write("\\\\" + trans + " + 0\n")
            else:
                f.write("\\\\ + 0\n")
            f.write("end\n")
    
    
    
