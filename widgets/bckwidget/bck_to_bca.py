from testbck import *

BCAFILEMAGIC = b"J3D1bca1"

class AnimComponentBCA(object):
    def __init__(self, value):
        #self.time = time 
        self.value = value
    
    def convert_rotation(self, rotscale):
        self.value *= rotscale 
        #self.tangentIn *= rotscale
        #self.tangentOut *= rotscale
        
    def serialize(self):
        return self.value#[self.time, self.value]
        
    @classmethod
    def from_array(cls, offset, index, count, valarray):
        return cls(valarray[offset+index])


def interpolate(time, comp1, comp2):
    # Todo: proper interpolation 
    diff = comp2.time-comp1.time 
    valdiff = comp2.value-comp1.value 
    
    delta = valdiff/diff 
    
    return comp1.value + time*delta


def convert_keyframes_to_full_values(components, total):
    result = []
    assert components[0].time == 0.0 
    print(components)
    
    if len(components) == 1:
        value = components[0].value 
        result.append(AnimComponentBCA(value))
    else:
        for i in range(len(components)-1):
            curr = components[i]
            next = components[i+1]
            
            timediff = next.time - curr.time 
            for t in range(int(timediff)):
                value = interpolate(t, curr, next)
                result.append(AnimComponentBCA(value))
    assert len(result) == 1 or len(result) == total        

    if len(result) > 1:
        for i in range(1, len(result)):
            if result[i].value != result[0].value:
                break 
        else:
            result = [result[0]]
            print("optimized to 1 item")
    
    return result 


class BCAAnim(object):
    def __init__(self, loop_mode, anglescale, duration):
        self.animations = []
        self.loop_mode = loop_mode
        self.anglescale = anglescale
        self.duration = duration
    
    @classmethod
    def from_bck(cls, f):
        loop_mode, anglescale, duration, animations = read_bck(f)
        bca_animations = []
        for anim in animations:
            new_anim = JointAnimation(anim.jointindex)
            new_anim.scale["X"] = convert_keyframes_to_full_values(anim.scale["X"], duration)
            new_anim.scale["Y"] = convert_keyframes_to_full_values(anim.scale["Y"], duration)
            new_anim.scale["Z"] = convert_keyframes_to_full_values(anim.scale["Z"], duration)
            
            new_anim.rotation["X"] = convert_keyframes_to_full_values(anim.rotation["X"], duration)
            new_anim.rotation["Y"] = convert_keyframes_to_full_values(anim.rotation["Y"], duration)
            new_anim.rotation["Z"] = convert_keyframes_to_full_values(anim.rotation["Z"], duration)
            
            new_anim.translation["X"] = convert_keyframes_to_full_values(anim.translation["X"], duration)
            new_anim.translation["Y"] = convert_keyframes_to_full_values(anim.translation["Y"], duration)
            new_anim.translation["Z"] = convert_keyframes_to_full_values(anim.translation["Z"], duration)
            bca_animations.append(new_anim)
        
        bca = cls(loop_mode, anglescale, duration)
        bca.animations = bca_animations
        return bca 
        
    
    def write(self, f): 
        f.write(BCAFILEMAGIC)
        filesize_offset = f.tell()
        f.write(b"ABCD") # Placeholder for file size
        write_uint32(f, 1) # Always a section count of 1
        f.write(b"SVR1" + b"\xFF"*12)

        section_start = f.tell()
        f.write(b"ANF1")

        section_size_offset = f.tell()
        f.write(b"EFGH")  # Placeholder for ttk1 size
        write_uint8(f, self.loop_mode)
        write_sint8(f, self.anglescale)
        
        rotscale = (2.0**self.anglescale)*(180.0 / 32768.0)
        
        write_uint16(f, self.duration)
        write_uint16(f, len(self.animations)) 
        count_offset = f.tell()
        f.write(b"1+1=11")  # Placeholder for scale, rotation and translation count
        data_offsets = f.tell()
        #f.write(b"--OnceUponATimeInALandFarAway---")
        f.write(b"\x00"*(0x7C - f.tell()))

        write_uint32(f, 0)

        anim_start = f.tell()
        f.write(b"\x00"*(0x24*len(self.animations)))
        write_padding(f, multiple=4)

        all_scales = []
        all_rotations = []
        all_translations = []
        for anim in self.animations:
            for axis in "XYZ":
                # Set up offset for scale
                if len(anim.scale[axis]) == 1:
                    sequence = [anim.scale[axis][0].value]
                else:
                    sequence = []
                    for comp in anim.scale[axis]:
                        sequence.append(comp.value)
                    
                offset = find_sequence(all_scales,sequence)
                if offset == -1:
                    offset = len(all_scales)
                    all_scales.extend(sequence)
                    
                anim._set_scale_offset(axis, offset)

                # Set up offset for rotation
                if len(anim.rotation[axis]) == 1:
                    comp = anim.rotation[axis][0]
                    #angle = ((comp.value+180) % 360) - 180
                    sequence = [comp.value/rotscale]
                    #print("seq", sequence)
                else:
                    sequence = []
                    for comp in anim.rotation[axis]:
                        sequence.append(comp.value/rotscale)
                    #print("seq", sequence)
                offset = find_sequence(all_rotations, sequence)
                if offset == -1:
                    offset = len(all_rotations)
                    all_rotations.extend(sequence)
                anim._set_rotation_offset(axis, offset)

                # Set up offset for translation
                if len(anim.translation[axis]) == 1:
                    sequence = [anim.translation[axis][0].value]
                else:
                    sequence = []
                    for comp in anim.translation[axis]:
                        sequence.append(comp.value)
                    
                offset = find_sequence(all_translations, sequence)
                if offset == -1:
                    offset = len(all_translations)
                    all_translations.extend(sequence)
                anim._set_translation_offset(axis, offset)


        scale_start = f.tell()
        for val in all_scales:
            write_float(f, val)

        write_padding(f, 4)

        rotations_start = f.tell()
        for val in all_rotations:
            """angle = ((val+180) % 360) - 180  # Force the angle between -180 and 180 degrees
            print(val, "becomes", angle)
            if angle >= 0:
                angle = (angle/180.0)*(2**15-1)
            else:
                angle = (angle/180.0)*(2**15)"""
            write_sint16(f, int(val))

        write_padding(f, 4)

        translations_start = f.tell()
        for val in all_translations:
            print(val)
            write_float(f, val)
        
        write_padding(f, 32)

        total_size = f.tell()
        
        

        f.seek(anim_start)
        for anim in self.animations:
            for axis in "XYZ":
                write_uint16(f, len(anim.scale[axis])) # Scale count for this animation
                write_uint16(f, anim._scale_offsets[axis]) # Offset into scales
                #write_uint16(f, 1) # Tangent type, 0 = only TangentIn; 1 = TangentIn and TangentOut


                write_uint16(f, len(anim.rotation[axis])) # Rotation count for this animation
                write_uint16(f, anim._rotation_offsets[axis]) # Offset into rotations
                #write_uint16(f, 1) # Tangent type, 0 = only TangentIn; 1 = TangentIn and TangentOut


                write_uint16(f, len(anim.translation[axis])) # Translation count for this animation
                write_uint16(f, anim._translation_offsets[axis])# offset into translations
                #write_uint16(f, 1) # Tangent type, 0 = only TangentIn; 1 = TangentIn and TangentOut


        # Fill in all the placeholder values
        f.seek(filesize_offset)
        write_uint32(f, total_size)

        f.seek(section_size_offset)
        write_uint32(f, total_size - section_start)

        f.seek(count_offset)
        write_uint16(f, len(all_scales))
        write_uint16(f, len(all_rotations))
        write_uint16(f, len(all_translations))
        # Next come the section offsets

        write_uint32(f, anim_start  - section_start)
        write_uint32(f, scale_start         - section_start)
        write_uint32(f, rotations_start   - section_start)
        write_uint32(f, translations_start      - section_start)

if __name__ == "__main__":
    import json
    import sys 
    
    in_file = sys.argv[1]
    out_file = sys.argv[2]
    
    with open(in_file, "rb") as f:
        bca = BCAAnim.from_bck(f)
        
    #print("Animations:", len(bca.animations))
    with open(out_file, "wb") as f:
        bca.write(f)
    print("Done.")
    
    """with open("dataDirect.json", "w") as f:
        json.dump(bca.animations, f, cls=MyEncoder, indent=" "*4)"""

