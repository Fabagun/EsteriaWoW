import json
from pathlib import Path
import struct
import tempfile
import unittest
from shell_review import approve_export, export_signature, key, source_snapshot, verify_proof


class ShellReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root/'source.bmd'; self.source.write_bytes(b'authored model')
        self.texture = self.root/'source.png'; self.texture.write_bytes(b'authored rgba')
        self.appearance = dict(fps=30, parts=[dict(model=str(self.source),texture=str(self.texture),animations={})],
                               legacy_texture_transparency=[dict(part=0,value=.4)])
        self.model = self.asset('a_'+'1'*20)
        source = source_snapshot(self.appearance)
        self.proof = dict(source_key=key(source),source=source,export=export_signature(self.model))
        self.registry = self.root/'reviews.json'
        self.registry.write_text(json.dumps(dict(schema=1,entries={key(source):dict(source=source,export=self.proof['export'])})))

    def asset(self, stem):
        path = self.root/(stem+'.m2')
        data = bytearray(320);data[:8]=b'MD20'+struct.pack('<I',264)
        struct.pack_into('<II',data,0x50,1,304)
        name=stem.encode()+b'\0';text=('Creature\\Battlemon3DBatch\\'+stem+'.blp').encode()+b'\0'
        struct.pack_into('<II',data,8,len(name),len(data));data.extend(name)
        struct.pack_into('<II',data,312,len(text),len(data));data.extend(text);data.extend(b'geometry')
        path.write_bytes(data);path.with_name(stem+'00.skin').write_bytes(b'all parts')
        path.with_suffix('.blp').write_bytes(b'original alpha')
        return path

    def test_cache_renaming_only_is_allowed(self):
        other=self.asset('a_'+'2'*20)
        self.assertEqual(approve_export(self.appearance,other,self.registry),self.proof)

    def test_unreviewed_source_or_transform_is_rejected(self):
        self.appearance['fps']=15
        with self.assertRaises(ValueError):approve_export(self.appearance,self.model,self.registry)

    def test_modified_geometry_and_alpha_are_rejected(self):
        for path in [self.model,self.model.with_suffix('.blp')]:
            before=path.read_bytes();path.write_bytes(before+b'changed')
            with self.assertRaises(ValueError):approve_export(self.appearance,self.model,self.registry)
            path.write_bytes(before)

    def test_later_source_edit_invalidates_proof(self):
        self.texture.write_bytes(b'replaced alpha')
        with self.assertRaisesRegex(ValueError,'source changed'):verify_proof(self.proof,self.registry)

    def test_missing_review_and_tampered_proof_are_rejected(self):
        self.proof['export']['skin']='wrong'
        with self.assertRaises(ValueError):verify_proof(self.proof,self.registry)
        self.registry.write_text(json.dumps(dict(schema=1,entries={})))
        with self.assertRaises(ValueError):approve_export(self.appearance,self.model,self.registry)

if __name__=='__main__':unittest.main()
