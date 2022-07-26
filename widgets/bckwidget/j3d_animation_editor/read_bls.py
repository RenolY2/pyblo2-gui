


import animations.general_animation as j3d


from os import path

class bls:
    def __init__(self):
        self.clusters = []
        self.clusters_key = []
    
    def __repr__(self):
        return "clusters (" + str(len(self.clusters)) + "): " + str(self.clusters) + "\ncluster keys(" + str(len(self.clusters_key)) + "): " + str(self.clusters_key)

class cluster:
    def __init__(self, blendmaxangle = 0, blendminangle = 0, flag = 0, keys = 0):
        self.maxangle = blendmaxangle
        self.minangle = blendminangle
        self.clusterkey = None
        self.flag = flag
        
        self.name = ""
        
        self.keys = keys
        self.positions = []
        self.normal_blends = []
    def __repr__(self):
        string = "\ncluster " + self.name + ": maxangle: " + str(self.maxangle) + " minangle: " + str(self.minangle) + " key name: " + self.clusterkey.name + " flag: " + str(self.flag) + " num keys: " + str(self.keys)
        string += "\n\tpositions (" + str(len(self.positions)) + "): " + str(self.positions) + "\n\tnormal blends (" + str(len(self.normal_blends)) + "): " + str(self.normal_blends)
        return string
        
class clusterkey:
    def __init__(self):
        self.name = ""
        self.positions = []
        self.normals = []
        
    def __repr__(self):
        return "\ncluster key " + self.name + ":\n\tpositions (" + str(len(self.positions)) +  "): " + str(self.positions) + "\n\tnormals (" + str(len(self.normals)) + "): " + str(self.normals)

class normal_blend:
    def __init__(self):
        self.src = []
        self.dest = []
        
    def __repr__(self):
        string = "\n\tblend\n\t\tsource: " + str(self.src) + "\n\t\tdest: " + str(self.dest)  + "\n"
        return string
        
class position:
    def __init__(self, x = 0, y = 0, z = 0):
        self.x = x
        self.y = y
        self.z = z
        
    def __repr__(self):
        return "\n\t\tx: " + str(self.x) + " y: " + str(self.y) + " z: " + str(self.z)
        
    def neg(self, bits):
        x = self.x
        y = self.y
        z = self.z 
       
        
        if bits & 0x4:
            x = -1 * self.x
        if bits & 0x2:
            y = -1 * self.y
        if bits & 0x1 :
            z = -1 * self.z
        
        return position( x, y, z)
        
class normal:
    def __init__(self, x = 0, y = 0, z = 0):
        self.x = x
        self.y = y
        self.z = z
        
    def __repr__(self):
        return "\n\t\tx: " + str(self.x) + " y: " + str(self.y) + " z: " + str(self.z)
        
    def neg(self, bits):
        x = self.x
        y = self.y
        z = self.z 
        
        if bits & 0x4:
            x = -1 * self.x
        if bits & 0x2:
            y = -1 * self.y
        if bits & 0x1:
            z = -1 * self.z
        
        return position( x, y, z)

def read_bls(filepath):
    with open(filepath, "rb") as f:
        magic = f.read(8)
        size = j3d.read_uint32(f)
        
        sectioncount = j3d.read_uint32(f)
        assert sectioncount == 1
        
        svr_data = f.read(16)
        cls_start = f.tell()
        cls_magic = f.read(4)
        cls_size = j3d.read_uint32(f)
        
        # read counts
        
        cluster_count = j3d.read_uint16(f)
        keycluster_count = j3d.read_uint16(f)
        nrmblend_count = j3d.read_uint16(f)
        vtxpos_count = j3d.read_uint16(f)
        vtxnorm_count = j3d.read_uint16(f)
        
        f.read(2)
        
        #read offsets
        
        cluster_offset = j3d.read_uint32(f) + cls_start
        keycluster_offset = j3d.read_uint32(f) + cls_start
        nrmblend_offset = j3d.read_uint32(f) + cls_start
        vtxpos_offset = j3d.read_uint32(f) + cls_start
        vtxnorm_offset = j3d.read_uint32(f) + cls_start
        vtxnorm_part2_offset = vtxnorm_offset + 0xc * vtxnorm_count #index table
        
        clustername_offset = j3d.read_uint32(f) + cls_start
        clusterkeyname_offset = j3d.read_uint32(f) + cls_start
        
        #read vertex array
        vertex_poss = []
        f.seek(vtxpos_offset)
        for i in range(vtxpos_count):
            x = j3d.read_float(f)
            y =  j3d.read_float(f) 
            z = j3d.read_float(f) 
            vertex_poss.append( position(x, y, z) )
            
        #read the table that the normal blends refer to - so the normals
        vertex_norms = []
        f.seek(vtxnorm_offset)
        for i in range(vtxnorm_count):
            x = j3d.read_float(f)
            y =  j3d.read_float(f) 
            z = j3d.read_float(f) 
            vertex_norms.append( normal(x, y, z) )
        
        
        #read normal blend data
        nrmblends = []
        f.seek(nrmblend_offset)
        #the first four shorts starting from offset 0x4e20 are source indices. these source indices are indices into another "blend" table.
        for i in range(nrmblend_count):
            f.seek(nrmblend_offset + 0xc * i)
            num = j3d.read_uint16(f)
            f.read(2)
            src = j3d.read_uint32(f) + cls_start #offsets into section 5 part 2 - point to shorts
            dest = j3d.read_uint32(f) + cls_start
            
            curr_blend = normal_blend()
            
            f.seek(src)
            for j in range ( num ):
                index = j3d.read_uint16(f)
                curr_blend.src.append( vertex_norms[index] )
               
            f.seek(dest)
            for j in range ( num ):
                index = j3d.read_uint16(f)
                curr_blend.dest.append( vertex_norms[index] )
            
            #print( curr_blend )
            
            
            nrmblends.append( curr_blend )
        
        
        f.seek(clustername_offset)
        cluster_stringtable = j3d.StringTable.from_file(f)
        
        f.seek(clusterkeyname_offset)
        clusterkey_stringtable = j3d.StringTable.from_file(f)
        
        blls = bls()
        
        for i in range( keycluster_count ):
            f.seek( keycluster_offset + 0xc * i)
            #uhh only normals ig
            position_count = j3d.read_uint16(f)
            normal_count = j3d.read_uint16(f)
            
            position_offset = j3d.read_uint32(f)+ cls_start
            normal_offset = j3d.read_uint32(f)+ cls_start
            
            curr_key = clusterkey()
            
            curr_key.name = clusterkey_stringtable.strings[i]
            
            f.seek(position_offset)
            for j in range ( position_count ):
                index = j3d.read_uint16(f)
                
                sign_bits = (index >> 0xd)

                index = index & 0x1FFF
                curr_key.positions.append( vertex_poss[index].neg(sign_bits) )
               
            f.seek(normal_offset)
            for j in range ( normal_count ):
                index = j3d.read_uint16(f)
                sign_bits = (index >> 0xd)
                index = index & 0x1FFF
                curr_key.normals.append( vertex_norms[index].neg(sign_bits) )

            blls.clusters_key.append(curr_key)
        
        for i in range( cluster_count ):
            f.seek( cluster_offset + 0x24 * i)
            max_angle = j3d.read_float(f)
            min_angle = j3d.read_float(f)
            unk_addr = j3d.read_uint32(f) #usually the last clusterkeynum
            flag = j3d.read_uint8(f)
            f.read(3)
            
            key_num = j3d.read_uint16(f)
            pos_num = j3d.read_uint16(f)
            normal_num = j3d.read_uint16(f)
            normalblend_num = j3d.read_uint16(f)
            
            position_offset  = j3d.read_uint32(f)+ cls_start
            normalblend_offset  = j3d.read_uint32(f)+ cls_start
            deformer_offset  = j3d.read_uint32(f)+ cls_start
            
            curr_cluster = cluster(max_angle, min_angle, flag, key_num )
            curr_cluster.name = cluster_stringtable.strings[i]
            
            key_index = int( (unk_addr + cls_start - keycluster_offset) / 0xC )
            curr_cluster.clusterkey = blls.clusters_key[key_index]
            
            
            f.seek(position_offset)
            for j in range ( pos_num ):
                index = j3d.read_uint16(f)
                
                
                
                sign_bits = (index >> 0xd)
                #index = index & 0x1FFF
                curr_cluster.positions.append( index )
            
            for i in range( normalblend_num ):
                j = int( (normalblend_offset - nrmblend_offset) / 12 + i )
                curr_cluster.normal_blends.append( nrmblends[j]  )
                #print( nrmblends[j] )

            
            blls.clusters.append( curr_cluster )
            
        
    return blls
                
import sys
def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)

if __name__ == "__main__":
    #import sys
    import platform
    import argparse
    from PyQt5.QtCore import QLocale


    QLocale.setDefault(QLocale(QLocale.English))
    sys.excepthook = except_hook

    parser = argparse.ArgumentParser()
    parser.add_argument("input", default = None,  nargs = '?')

    args = parser.parse_args()

    if len(sys.argv) > 1 and path.exists(sys.argv[1]):
        if path.isfile(sys.argv[1]) and sys.argv[1].endswith(".bls"):
            bls = read_bls(sys.argv[1])
    
            with open( sys.argv[1]+".txt", "w") as f:
                f.write( str(bls) )
