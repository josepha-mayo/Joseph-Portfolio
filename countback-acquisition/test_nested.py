import io, struct, unittest, zipfile
import nested

class NestedTests(unittest.TestCase):
    def archives(self, compression=zipfile.ZIP_STORED):
        inner=io.BytesIO()
        with zipfile.ZipFile(inner,'w') as z:
            z.writestr('scene/example.txt',b'generated test data; not a photograph')
        outer=io.BytesIO()
        with zipfile.ZipFile(outer,'w',compression=compression) as z:
            z.writestr('scene.zip',inner.getvalue())
            z.writestr('other.txt',b'outside selected member')
        outer.seek(0)
        return outer,zipfile.ZipFile(outer)
    def test_nested_actual_zip_read(self):
        b,z=self.archives()
        with z, zipfile.ZipFile(nested.StoredSlice(b,z,'scene.zip')) as inner:
            self.assertEqual(inner.read('scene/example.txt'),b'generated test data; not a photograph')
    def test_stops_at_slice_end(self):
        b,z=self.archives()
        with z:
            s=nested.StoredSlice(b,z,'scene.zip'); s.seek(-3,2)
            self.assertEqual(len(s.read(100)),3); self.assertEqual(s.read(),b'')
    def test_invalid_seeks(self):
        b,z=self.archives()
        with z:
            s=nested.StoredSlice(b,z,'scene.zip')
            for offset,whence in [(-1,0),(s.size+1,0),(1,2),(0,9)]:
                with self.assertRaises(ValueError):s.seek(offset,whence)
    def test_compressed_outer_refused(self):
        b,z=self.archives(zipfile.ZIP_DEFLATED)
        with z,self.assertRaises(ValueError): nested.StoredSlice(b,z,'scene.zip')
    def test_unsafe_path_refused(self):
        b,z=self.archives()
        with z,self.assertRaises(ValueError): nested.StoredSlice(b,z,'../scene.zip')
    def test_crossed_boundary_refused(self):
        b,z=self.archives()
        with z:
            i=z.getinfo('scene.zip'); i.file_size+=100; i.compress_size+=100
            with self.assertRaises(ValueError): nested.StoredSlice(b,z,'scene.zip')
    def test_mismatched_local_name_refused(self):
        b,z=self.archives()
        b.seek(30); b.write(b'X')
        with z,self.assertRaises(ValueError): nested.StoredSlice(b,z,'scene.zip')
    def test_encrypted_refused(self):
        b,z=self.archives()
        with z:
            z.getinfo('scene.zip').flag_bits|=1
            with self.assertRaises(ValueError): nested.StoredSlice(b,z,'scene.zip')
    def test_nonzip_refused(self):
        b,z=self.archives()
        with z,self.assertRaises(ValueError): nested.StoredSlice(b,z,'other.txt')

if __name__=='__main__':unittest.main()
