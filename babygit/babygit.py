# Copyright 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import hashlib
import os
import struct
import zlib
import binascii

import store

def get_delta_hdr_size(data, offset):
    byte = ord(data[offset])
    offset += 1
    size = byte & 0x7f
    shift = 7
    while byte & 0x80:
        byte = ord(data[offset])
        offset += 1
        size += (byte & 0x7f) << shift
        shift += 7
    return size, offset

def patch_delta(ref, delta):
    src_size, offset = get_delta_hdr_size(delta, 0)
    data_off = ref.find('\x00') + 1
    if src_size != len(ref) - data_off: raise ValueError('size mismatch')
    result_size, offset = get_delta_hdr_size(delta, offset)
    size_remaining = result_size
    result = [obj_type(ref) + ' ' + str(result_size) + '\x00']
    while offset < len(delta):
        oo = offset
        cmd = ord(delta[offset])
        offset += 1
        if cmd & 0x80:
            # copy from reference
            copy_off = data_off
            copy_size = 0
            for i in range(4):
                if cmd & (1 << i):
                    copy_off += ord(delta[offset]) << (i << 3)
                    offset += 1
            for i in range(3):
                if cmd & (0x10 << i):
                    copy_size |= ord(delta[offset]) << (i << 3)
                    offset += 1
            if copy_size == 0: copy_size = 0x10000
            if copy_off + copy_size > len(ref):
                raise ValueError('size overflow')
            if copy_size > size_remaining:
                raise ValueError('output size overflow')
            result.append(ref[copy_off:copy_off + copy_size])
            size_remaining -= copy_size
        elif cmd > 0:
            if cmd > size_remaining: raise ValueError('output size overflow')
            result.append(delta[offset:offset + cmd])
            offset += cmd
            size_remaining -= cmd
        else:
            raise ValueError('caught zero command')
    if size_remaining: raise ValueError('didn\'t fill output buffer')
    return ''.join(result)

class FsStore(store.Store):
    def __init__(self, basedir = '_git'):
        self.basedir = basedir
        self.packs = None
    def getlooseobj(self, sha):
        path = os.path.join(self.basedir, 'objects', sha[:2], sha[2:])
        if os.path.exists(path):
            f = file(path)
            return f.read()
    def getinforefs(self):
        return {'refs/heads/master':
            '3e31b270c8d188dc1cc655cecfcebea433a74ba0'}
    def getpacks(self):
        if self.packs is None:
            self.packs = self.readpacks()
        return self.packs
    def readpacks(self):
        packs = []
        packpath = os.path.join(self.basedir, 'objects', 'pack') 
        for fn in os.listdir(packpath):
            if fn.endswith('.idx'):
                idx = file(os.path.join(packpath, fn)).read()
                packfn = os.path.join(packpath, fn[:-4] + '.pack')
                packs.append((idx, packfn))
        return packs
    def get_obj_from_pack(self, sha):
        #print 'fetching', sha, 'from pack'
        firstbyte = int(sha[:2], 16)
        binaryhash = binascii.unhexlify(sha)
        for idx, fn in self.getpacks():
            if firstbyte == 0:
                indexlo = 0
                indexhi, = struct.unpack('>I', idx[8:12])
            else:
                off = 4 + 4 * firstbyte
                indexlo, indexhi = struct.unpack('>II', idx[off:off+8])
            # Now try to find exact hash
            # todo: replace linear with binary or interpolation search
            found_ix = None
            for ix in range(indexlo, indexhi):
                off = 1032 + 20 * ix
                if idx[off:off+20] == binaryhash:
                    found_ix = ix
                    break
            if found_ix is not None:
                n_objs, = struct.unpack('>I', idx[1028:1032])
                off = 1032 + 24 * n_objs + 4 * found_ix
                pack_off, = struct.unpack('>I', idx[off:off + 4])
                #print 'found, ix =', ix, 'pack_off =', pack_off
                return self.get_pack_obj(fn, pack_off)
    def read_zlib(self, f, size):
        result = []
        d = zlib.decompressobj()
        sizeremaining = size
        while sizeremaining > 0:
            block = d.decompress(f.read(4096))
            result.append(block)
            sizeremaining -= len(block)
        return ''.join(result)
    def get_pack_obj(self, packfn, offset):
        f = file(packfn)
        f.seek(offset)
        t, size = self.get_type_and_size(f)
        if t < 5:
            hdr = store.obj_types[t] + ' ' + str(size) + '\x00'
            return hdr + self.read_zlib(f, size)
        elif t == 6:  # OBJ_OFS_DELTA
            byte = ord(f.read(1))
            off = byte & 0x7f
            while byte & 0x80:
                byte = ord(f.read(1))
                off = ((off + 1) << 7) + (byte & 0x7f)
            ref_offset = offset - off
            delta = self.read_zlib(f, size)
            ref = self.get_pack_obj(packfn, ref_offset)
            return patch_delta(ref, delta)
        elif t == 7:  # OBJ_REF_DELTA
            ref_sha = binascii.hexlify(f.read(20))
            #print ref_sha
            delta = self.read_zlib(f, size)
            return patch_delta(self.getobj(ref_sha), delta)
        else:
            print 'can\'t handle type =', t

    def get_type_and_size(self, f):
        byte = ord(f.read(1))
        t = (byte >> 4) & 7
        size = byte & 15
        shift = 4
        while byte & 0x80:
            byte = ord(f.read(1))
            size += (byte & 0x7f) << shift
            shift += 7
        return (t, size)

def obj_type(obj):
    return obj[:obj.find(' ')]

def obj_size(obj):
    return int(obj[obj.find(' ') + 1:obj.find('\x00')])

def obj_contents(obj):
    return obj[obj.find('\x00') + 1:]

# todo: delete (it's in repo)
def parse_tree(blob):
    if obj_type(blob) != 'tree': raise ValueError('wrong blob type')
    ix = blob.find('\x00') + 1
    if ix == 0: raise ValueError('missing nul')
    result = []
    while ix < len(blob):
        nul_ix = blob.find('\x00', ix)
        mode_and_name = blob[ix:nul_ix]
        mode, name = mode_and_name.split(' ', 1)
        sha = binascii.hexlify(blob[nul_ix + 1:nul_ix + 21])
        result.append((mode, name, sha))
        ix = nul_ix + 21
    return result


#ls(s, rootref)
#import sys
#sys.stdout.write(s.getobj('7e85906bee679d31506d1b9402aef71eb562a7bd'))

class MemStore(store.Store):
    def __init__(self):
        self.store = {}
    def getobj(self, sha):
        return self.store[sha]
    def getlooseobj(self, sha):
        return zlib.compress(self.store[sha])
    def getinforefs(self):
        return self.inforefs
    def putobj(self, sha, value):
        self.store[sha] = value
    def setinforefs(self, inforefs):
        self.inforefs = inforefs

def pack_tree(triples):
    result = []
    for mode, name, sha in triples:
        result.append(mode + ' ' + name + '\x00' + binascii.unhexlify(sha))
    return ''.join(result)

def put_test_repo(store):
    f0 = store.put('blob', 'hello, world\n')
    d0 = store.put('tree', pack_tree([('100644', 'hello', f0)]))
    c0 = store.put('commit', 'tree ' + d0 + '''
author Raph <raph> 1346820538 -0400
committer Raph <raph> 1346820538 -0400

Test of "hello world"
''')
    store.setinforefs({'refs/heads/master': c0})

def ensure_repo(store):
    if not store.getinforefs().has_key('refs/heads/master'):
        d = store.put('tree', pack_tree([]))
        author = 'Webapp user <anonymous@ghilbert.org>'
        c = store.put('commit', 'tree ' + d + '''
author ''' + author + ''' 1346820538 -0400
committer ''' + author + ''' 1346820538 -0400

Initial empty repo
''')
        store.setinforefs({'refs/heads/master': c})
