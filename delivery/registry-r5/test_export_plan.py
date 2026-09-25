import copy, io, json, tarfile
import pytest
from publish_candidate import export_plan, verify_export_manifest, read_manifest, compress_new_layer, digest


def candidate():
    return {'Id':'sha256:'+'a'*64,'RootFS':{'Layers':['sha256:'+'b'*64,'sha256:'+'c'*64]}}


def test_observed_manifest_must_match_plan():
    p=export_plan(candidate())
    assert verify_export_manifest([{**p,'RepoTags':['local:only']}],p)==p


@pytest.mark.parametrize('value',[[],None,{},[{}],[{},{}]])
def test_missing_manifest_rejected(value):
    with pytest.raises(ValueError):
        verify_export_manifest(value,export_plan(candidate()))


def test_order_mismatch_rejected():
    p=export_plan(candidate());bad=copy.deepcopy(p);bad['Layers'].reverse()
    with pytest.raises(ValueError):verify_export_manifest([bad],p)


def test_config_mismatch_rejected():
    p=export_plan(candidate());bad={**p,'Config':'blobs/sha256/'+'d'*64}
    with pytest.raises(ValueError):verify_export_manifest([bad],p)


def test_late_manifest_from_real_stream():
    p=export_plan(candidate());buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w') as t:
        for name,content in [(p['Layers'][0],b'layer-one'),(p['Config'],b'config'),('manifest.json',json.dumps([p]).encode())]:
            item=tarfile.TarInfo(name);item.size=len(content);t.addfile(item,io.BytesIO(content))
    buf.seek(0)
    with tarfile.open(fileobj=buf,mode='r|') as t:actual=read_manifest(t)
    assert verify_export_manifest([actual],p)==p


def test_invalid_content_id_rejected():
    c=candidate();c['RootFS']['Layers'][0]='sha256:'+'g'*64
    with pytest.raises(ValueError):export_plan(c)


def test_new_layer_hash_and_lossless_bytes(tmp_path):
    import gzip
    data=b'bounded layer fixture'*1000
    path=tmp_path/'layer.gz'
    d=compress_new_layer(io.BytesIO(data),len(data),digest(data),path)
    assert gzip.decompress(path.read_bytes())==data
    assert d['digest']==digest(path.read_bytes())


def test_wrong_layer_identity_rejected(tmp_path):
    with pytest.raises(ValueError):
        compress_new_layer(io.BytesIO(b'wrong'),5,'sha256:'+'f'*64,tmp_path/'layer.gz')
