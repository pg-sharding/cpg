#!/usr/bin/env python3
"""Prepare an independent fresh build; bind runtime identities only after that build. No command is executed."""
import argparse,ast,hashlib,json,pathlib,re,shutil
PACKET=pathlib.Path(__file__).resolve().parent.parent
OLD='/home/reshke/allfuzz/typed-leaf-v7-sql-20261108-r1'
ARCHIVE='32a396e875b17122dc05dad59ecd11a3cb5a78f5b229bb5ce11fb769feaddb64'
SOURCE={'base':'6f9a5d59e75cca4fb8e6ab23e502aeab3ae6db64d7af1bc431744fc1ce847649','v6':'681db606e5285bacc18faf073dca9ae1adb8e0a8396ccf96a9c56fdfbf88048f','v7':'f732479128691dc1b2ad927cbffff0c3d40e205a988e77d9ee601018129b642e'}
OLD_GATE='2a18f8b4dfa1cdbfa6043fa58abaffc58710f8b47bb9984ab80909fe79b70e01';OLD_SESSION='f85060bf57add263b6afc6d0714a872ed79961c16e6453fb83f6d3ee2733bcd2'
INPUTS_MANIFEST='8f1242578ee7b22d145b7f590f62a67b898333781a18e4d53e39516dc9f3cfab'
TEMPLATE_PINS={'build.py': '890b3bd6fa430f13ffb973d1e0652a5073aa1f6ec36e04000876c862aac4c53b', 'gate.py': '2a18f8b4dfa1cdbfa6043fa58abaffc58710f8b47bb9984ab80909fe79b70e01', 'session.py': 'f85060bf57add263b6afc6d0714a872ed79961c16e6453fb83f6d3ee2733bcd2', 'benchmark.py': '44bce5c3b748f50b72018b1c4c4ffc8fbba82bfac55d299e1cec1528bc2ca401', 'analyze.py': '163e85387adcf78fd1e9728abb24bdb3164fd84f6cac0876f973af085997d0b4', 'check-static-protocol.py': '6909894a0cd016748fe8104e504a5eb1c2877dea9ce6300aa53ba8fbef68287e'}
NAMES=['build.py','gate.py','session.py','benchmark.py','analyze.py','check-static-protocol.py']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inv(root):return {str(p.relative_to(root)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(root.rglob('*')) if p.is_file() and not p.is_symlink()}
def save(p,obj):
 with p.open('x') as f:f.write(json.dumps(obj,indent=2)+'\n')
def prepare(root,archive):
 assert not root.exists(),'Use a new empty namespace'
 assert re.fullmatch(r'/[A-Za-z0-9_./-]+',str(root)),'Current pg_ctl option strings require a simple absolute path without whitespace or quotes'
 assert sha(archive)==ARCHIVE,'Exact pinned git archive required'
 assert sha(PACKET/'inputs/inputs-manifest.json')==INPUTS_MANIFEST
 assert all(sha(PACKET/'runtime'/n)==pin for n,pin in TEMPLATE_PINS.items())
 expected=json.loads((PACKET/'inputs/inputs-manifest.json').read_text());assert len(expected)==20
 assert all(sha(PACKET/'inputs'/n)==v['sha256'] for n,v in expected.items())
 assert sha(PACKET/'runtime/gate.py')==OLD_GATE and sha(PACKET/'runtime/session.py')==OLD_SESSION
 root.mkdir(parents=True);shutil.copytree(PACKET/'inputs',root/'inputs');shutil.copy2(archive,root/'base72.tar.gz')
 originals={}
 for n in NAMES:
  source=PACKET/'runtime'/n;originals[n]=sha(source);text=source.read_text().replace(OLD,str(root))
  if n=='build.py':
   old_archive="archive=pathlib.Path('/home/reshke/allfuzz/hash-noop-sql-20261108-r1/inputs/base72.tar.gz')"
   assert old_archive in text;text=text.replace(old_archive,'archive=pathlib.Path('+repr(str(root/'base72.tar.gz'))+')')
  ast.parse(text);(root/n).write_text(text)
 save(root/'REPLAY-PREPARED.json',{'status':'PREPARED_NOT_BUILT_NOT_BOUND','root':str(root),'archive_sha256':ARCHIVE,'baseline_revision':'72b9498df9a369e747f8d96efb5a6cd33c2451e2','original_scripts':originals,'prepared_scripts':{n:sha(root/n) for n in NAMES},'inputs_manifest_sha256':sha(root/'inputs/inputs-manifest.json'),'scope':'Only root/archive path adaptation. Runtime ELF pins remain historical until bind-built after fresh complete builds. No build, SQL or timing has run.'})
 print('Prepared. Next, run explicitly: python3 '+str(root/'build.py'))
def bind(root):
 assert not (root/'REPLAY-BOUND.json').exists(),'Already bound; never rebind after samples'
 assert not (root/'gate-r5').exists() and not (root/'sql-r5').exists() and not list(root.glob('data-*')),'Bind only before any runtime cluster or sample'
 assert sha(root/'inputs/inputs-manifest.json')==INPUTS_MANIFEST
 prep=json.loads((root/'REPLAY-PREPARED.json').read_text());assert sha(root/'base72.tar.gz')==ARCHIVE
 status=json.loads((root/'build-status.json').read_text());freeze=json.loads((root/'BUILD-FREEZE.json').read_text())
 assert status['status']=='PASS_MATCHED4_BUILD_CORE239' and freeze['base_revision']=='72b9498df9a369e747f8d96efb5a6cd33c2451e2' and freeze['source_sha256']==SOURCE
 assert freeze['flags']=='-O2 -g' and freeze['core_each']==239 and sha(root/'build.py')==freeze['controller_sha256']
 assert all(sha(root/n)==prep['prepared_scripts'][n] for n in NAMES),'Prepared runtime changed before binding'
 assert all(sha(root/'inputs'/n)==v['sha256'] for n,v in freeze['inputs'].items())
 for v in ['base','v6','v7']:
  expected=json.loads((root/'build-proof'/f'source-{v}-7726.json').read_text());assert len(expected)==7726 and inv(root/f'source-{v}')==expected
  assert sha(root/f'source-{v}/src/backend/access/nbtree/nbtsearch.c')==SOURCE[v]
 elfs={};bindings={};prefix=root/'prefix'
 for v in ['base','v6','v7','v7assert']:
  stage=root/f'stage-{v}'/str(prefix).lstrip('/');proof=root/'build-proof'/v/'binding.json';binding=json.loads(proof.read_text())
  assert inv(stage)==binding['installed_files']
  assert 'CFLAGS=-O2 -g' in binding['configure'] and ('--enable-cassert' if v=='v7assert' else '--disable-cassert') in binding['configure']
  assert 'All 239 tests passed.' in (root/'build-proof'/f'{v}-core239.log').read_text()
  elfs[v]=sha(stage/'bin/postgres');bindings[v]=sha(proof)
 session=root/'session.py';text=session.read_text();text,count=re.subn(r'^EXPECTED_ELFS=.*$',lambda _: 'EXPECTED_ELFS='+repr(elfs),text,flags=re.M);assert count==1;ast.parse(text);session.write_text(text)
 gate_sha=sha(root/'gate.py');session_sha=sha(session)
 for name in ['analyze.py','check-static-protocol.py']:
  path=root/name;text=path.read_text();assert OLD_GATE in text and OLD_SESSION in text
  text=text.replace(OLD_GATE,gate_sha).replace(OLD_SESSION,session_sha);ast.parse(text);path.write_text(text)
 save(root/'REPLAY-BOUND.json',{'status':'BOUND_NEW_BUILD_IDENTITIES_BEFORE_RUNTIME','build_status_sha256':sha(root/'build-status.json'),'build_freeze_sha256':sha(root/'BUILD-FREEZE.json'),'build_binding_sha256':bindings,'source_sha256':SOURCE,'new_postgres_sha256':elfs,'new_runtime_sha256':{n:sha(root/n) for n in NAMES},'old_recorded_results_unchanged':True,'scope':'Only new root/archive path and exact freshly built ELF/session/gate identities rebound; original SQL/source/answers/schedule/assertions/source checks unchanged. No command executed by this adapter.'})
 print('Bound. Next run static checker, then gate, seed and smoke. Parent/manual review is still required before freeze and run.')
parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
p=sub.add_parser('prepare');p.add_argument('--root',required=True,type=pathlib.Path);p.add_argument('--archive',required=True,type=pathlib.Path)
p=sub.add_parser('bind-built');p.add_argument('--root',required=True,type=pathlib.Path)
a=parser.parse_args();root=a.root.resolve()
if a.command=='prepare':prepare(root,a.archive.resolve())
else:bind(root)
