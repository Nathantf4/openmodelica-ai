"""Provision narrow native-library dependencies without changing system packages."""
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT/'runtime/native-downloads'
PREFIX = Path.home()/'.local/opt/openmodelica-1.27.1'
packages = ['qt6-websockets','qt6-httpserver','openscenegraph','libcurl-gnutls']
lines = subprocess.check_output(['pacman','-Sp','--print-format','%n %v %l',*packages],text=True).splitlines()
records = []
for line in lines:
    name,version,url = line.split(maxsplit=2)
    if name not in packages:
        raise RuntimeError(f'Unexpected dependency {name}; inspect before expanding scope')
    package = CACHE/url.rsplit('/',1)[1]
    signature = Path(str(package)+'.sig')
    for path,address in [(package,url),(signature,url+'.sig')]:
        if not path.exists():
            subprocess.run(['curl','--fail','--silent','--show-error','--location','--max-time','90',address,'-o',str(path)],check=True)
    subprocess.run(['pacman-key','--verify',str(signature),str(package)],check=True)
    subprocess.run(['bsdtar','-xf',str(package),'-C',str(PREFIX),'--no-same-owner','usr/'],check=True)
    records.append({'package':name,'version':version,'source':url,'sha256':hashlib.sha256(package.read_bytes()).hexdigest(),'signature':'verified against installed pacman keyring'})
# These two CORBA runtime packages were already installed by signed Ubuntu apt
# in our pinned Qt6 image; unlike glibc/Qt, they do not replace host core libraries.
container = 'openmodelica-ai-omedit'
image = subprocess.check_output(['docker','inspect',container,'--format','{{.Image}}'],text=True).strip()
for package in ['libomniorb4-3t64','libomnithread4']:
    check = subprocess.run(['docker','exec',container,'dpkg','-V',package],capture_output=True,text=True,check=True)
    if check.stdout.strip():
        raise RuntimeError(f'Modified image package: {check.stdout}')
    files = subprocess.check_output(['docker','exec',container,'dpkg','-L',package],text=True).splitlines()
    for file in files:
        if file.startswith('/usr/lib/') and '.so.' in Path(file).name:
            target = PREFIX/file.lstrip('/')
            target.parent.mkdir(parents=True,exist_ok=True)
            subprocess.run(['docker','cp','-L',f'{container}:{file}',str(target)],check=True)
            records.append({'path':str(target.relative_to(PREFIX)),'package':package,'source_image':image,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
    target = PREFIX/'usr/share/doc'/package
    target.mkdir(parents=True,exist_ok=True)
    subprocess.run(['docker','cp',f'{container}:/usr/share/doc/{package}/copyright',str(target/'copyright')],check=True)
(PREFIX/'dependency-manifest.json').write_text(json.dumps(records,indent=2))
print('Native dependency files and provenance installed:',len(records))
