"""Fonte oficial fixada: nenhum download mutável ou correção silenciosa."""
from pathlib import Path
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = '02111531f8661373aa7b6ba31c316c67d72d1dd2'
URL = f'https://raw.githubusercontent.com/google/meridian/{SOURCE_COMMIT}/meridian/data/simulated_data/csv/geo_all_channels.csv'
SHA256 = 'd9ee016f7cd21f5c90b50da10a794af91a372b69f881d3caa266edd41fdafbf6'
BLOB_SHA = '855e25fe5f76cc895d458f456f7a1d45ba5d87b8'

def verify_bytes(data):
    actual = hashlib.sha256(data).hexdigest()
    if actual != SHA256:
        raise ValueError(f'Integridade inválida: SHA-256 {actual}')
    blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    if blob != BLOB_SHA:
        raise ValueError('Blob diferente da árvore oficial consultada')
    return actual

def retrieve(path=None):
    path = Path(path) if path is not None else ROOT / 'data/raw/geo_all_channels.csv'
    if path.exists():
        verify_bytes(path.read_bytes())
    else:
        with urllib.request.urlopen(URL, timeout=60) as response:
            data = response.read()
        verify_bytes(data)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return path

def check_provenance():
    meta = json.loads((ROOT / 'data/metadata/provenance.json').read_text())
    if (meta['sha256'], meta['source_commit'], meta['url']) != (SHA256, SOURCE_COMMIT, URL):
        raise ValueError('Metadados divergentes do contrato de origem')
    return meta
