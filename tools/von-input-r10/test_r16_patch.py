import gzip
import hashlib
import io
import json
import tarfile
import unittest
import build_r16_patch as p

class PatchTests(unittest.TestCase):
    def setUp(self):
        self.original = (p.PARENT, p.PARENT_CONFIG, p.VIEWS_SHA)
        self.views = b'def load_image(path): return path\n'
        self.config = {'architecture':'amd64', 'os':'linux',
            'config':{'WorkingDir':'/app', 'Entrypoint':['python3','-m','von_read.warm_runtime','supervise']},
            'rootfs':{'type':'layers','diff_ids':['sha256:'+f'{i:064x}' for i in range(19)]},
            'history':[{'created_by':'base'} for _ in range(19)]}
        self.c = p.encoded(self.config)
        self.parent = {'schemaVersion':2,'mediaType':'application/vnd.oci.image.manifest.v1+json',
            'config':{'mediaType':'application/vnd.oci.image.config.v1+json','digest':p.digest(self.c),'size':len(self.c)},
            'layers':[{'mediaType':'application/vnd.oci.image.layer.v1.tar+gzip',
                       'digest':'sha256:'+f'{i+100:064x}','size':100+i} for i in range(19)]}
        self.m = p.encoded(self.parent)
        p.PARENT, p.PARENT_CONFIG, p.VIEWS_SHA = p.digest(self.m), p.digest(self.c), hashlib.sha256(self.views).hexdigest()

    def tearDown(self):
        p.PARENT, p.PARENT_CONFIG, p.VIEWS_SHA = self.original

    def test_one_file_and_parent_identity(self):
        out = p.compose(self.m, self.c, self.views)
        m, c = json.loads(out['manifest.json']), json.loads(out['config.json'])
        self.assertEqual(m['layers'][:19], self.parent['layers'])
        self.assertEqual(c['rootfs']['diff_ids'][:19], self.config['rootfs']['diff_ids'])
        self.assertEqual(c['config'], self.config['config'])
        self.assertEqual(len(m['layers']), 20)
        raw = gzip.decompress(out['patch.tar.gz'])
        with tarfile.open(fileobj=io.BytesIO(raw)) as t:
            self.assertEqual(t.getnames(), ['app/von_read/views.py'])
            self.assertEqual(t.extractfile(t.getmembers()[0]).read(), self.views)
        self.assertEqual(c['rootfs']['diff_ids'][-1], p.digest(raw))
        self.assertEqual(m['config']['digest'], p.digest(out['config.json']))

    def test_deterministic(self):
        self.assertEqual(p.compose(self.m,self.c,self.views), p.compose(self.m,self.c,self.views))

    def test_changed_parent_rejected(self):
        with self.assertRaises(ValueError): p.compose(self.m+b' ',self.c,self.views)

    def test_changed_decoder_rejected(self):
        with self.assertRaises(ValueError): p.compose(self.m,self.c,self.views+b'\n')

    def test_changed_config_rejected(self):
        with self.assertRaises(ValueError): p.compose(self.m,self.c+b' ',self.views)

if __name__ == '__main__': unittest.main()
