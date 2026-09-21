"""Install verified official native binaries into a user-owned prefix (no sudo).
No maintainer scripts are executed; dependencies are resolved separately.
"""
import gzip
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT/'runtime/native-downloads'
PREFIX = Path.home()/'.local/opt/openmodelica-1.27.1'
BASE = 'https://build.openmodelica.org/omc/builds/linux/releases/1.27.1/'
PACKAGES = ['omc-common','libomc','libomcsimulation','libomplot','libomsimulator','libomsensplugin','omc','omedit']
subprocess.run(['gpgv','--keyring',str(CACHE/'openmodelica.gpg'),str(CACHE/'Release.gpg'),str(CACHE/'Release')],check=True)
release = (CACHE/'Release').read_text().split('SHA256:\n',1)[1].split('SHA512:',1)[0]
checksums = {parts[2]:parts[0] for line in release.splitlines() if len(parts:=line.split()) == 3}
relative_index = 'release/binary-amd64/Packages.gz'
index = urllib.request.urlopen(BASE+'dists/resolute/'+relative_index,timeout=40).read()
assert hashlib.sha256(index).hexdigest() == checksums[relative_index], 'Package index digest mismatch'
(CACHE/'Packages.gz').write_bytes(index)
paragraphs = gzip.decompress(index).decode().split('\n\n')
metadata = {}
for paragraph in paragraphs:
    fields = {}
    for line in paragraph.splitlines():
        if ': ' in line and not line.startswith(' '):
            key,value = line.split(': ',1)
            fields[key] = value
    if fields.get('Package') in PACKAGES:
        metadata[fields['Package']] = fields
assert set(metadata) == set(PACKAGES)
PREFIX.mkdir(parents=True,exist_ok=True)
records = []
for name in PACKAGES:
    info = metadata[name]
    assert info['Version'] == '1.27.1-1', info['Version']
    destination = CACHE/Path(info['Filename']).name
    if not destination.exists():
        destination.write_bytes(urllib.request.urlopen(BASE+info['Filename'],timeout=90).read())
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    assert digest == info['SHA256'], f'{name}: package digest mismatch'
    members = subprocess.check_output(['ar','t',str(destination)],text=True).splitlines()
    member = next(n for n in members if n.startswith('data.tar.'))
    tarball = CACHE/(name+'-'+member)
    with tarball.open('wb') as stream:
        subprocess.run(['ar','p',str(destination),member],stdout=stream,check=True)
    subprocess.run(['bsdtar','-xf',str(tarball),'-C',str(PREFIX),'--no-same-owner'],check=True)
    records.append({'name':name,'version':info['Version'],'sha256':digest,'url':BASE+info['Filename']})
    print('Extracted verified',name,flush=True)
(PREFIX/'install-manifest.json').write_text(json.dumps({'prefix':str(PREFIX),'packages':records,'signature':'Release.gpg verified by gpgv; Packages and individual .deb SHA256 checked'},indent=2))
print(PREFIX)
