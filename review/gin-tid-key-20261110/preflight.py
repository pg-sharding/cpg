#!/usr/bin/env python3
import argparse,importlib.util,json,pathlib,shlex,shutil,traceback
root=pathlib.Path(__file__).resolve().parent
loader=importlib.util.spec_from_file_location('bc',root/'build-harness/common.py');bc=importlib.util.module_from_spec(loader);loader.loader.exec_module(bc)
p=argparse.ArgumentParser();p.add_argument('--reference-build',type=pathlib.Path,required=True);a=p.parse_args()
out=root/'preflight';out.mkdir();s=dict(status='RUNNING',units=[],properties=[])
try:
 spec,_=bc.source_plan(root/'build-source/SOURCE.json');old=json.loads((a.reference_build/'build-receipt.json').read_text())
 assert old['base']==spec['base']
 for role,reference in [('P10','B'),('C10','C9'),('C10_assert','C9_assert')]:
  source_role='C10' if role=='C10_assert' else role
  overlay=out/role/'access';overlay.mkdir(parents=True)
  shutil.copy2(root/'build-source'/source_role/'src/include/access/gin_private.h',overlay/'gin_private.h')
  prefix=pathlib.Path(old['variants'][reference]['prefix']);pg=prefix/'bin/pg_config'
  flags=shlex.split(bc.capture([pg,'--cflags'],prefix))+shlex.split(bc.capture([pg,'--cppflags'],prefix))
  headers=pathlib.Path(bc.capture([pg,'--includedir-server'],prefix).strip());assert bc.inventory(headers)==old['variants'][reference]['headers']
  source=root/'build-source'/source_role/'src/backend/access/gin/ginget.c';obj=out/(role+'.o')
  inc=['-I'+str(overlay.parent),'-I'+str(headers),'-I'+str(prefix/'include')]
  bc.run(['gcc',*flags,'-Werror','-fPIC',*inc,'-c',source,'-o',obj],out/(role+'-compile.log'),prefix=prefix)
  bc.run(['objdump','-drwC',obj],out/(role+'-ASM.txt'))
  s['units'].append(dict(role=role,source_sha256=bc.sha(source),object_sha256=bc.sha(obj),header_sha256=bc.sha(overlay/'gin_private.h')))
  if role!='C10_assert':
   driver=root/'preflight-input/property.c';binary=out/(role+'-property')
   bc.run(['gcc',*flags,'-Werror',*inc,driver,'-o',binary],out/(role+'-property-compile.log'),prefix=prefix)
   value=json.loads(bc.capture([binary],prefix));assert value==dict(cases=1009216,sizeof_tid=6,alignment_residues=5)
   s['properties'].append(dict(role=role,**value,driver_sha256=bc.sha(driver),binary_sha256=bc.sha(binary)))
 s.update(status='PASS',source_plan_sha256=bc.sha(root/'build-source/SOURCE.json'),scope='Actual installed headers and production translation units; standalone ordering properties, no performance claim. Only little-endian execution tested.')
except BaseException as e:
 s.update(status='FAILED_PRESERVED',error=repr(e),traceback=traceback.format_exc());raise
finally:bc.save(out/'status.json',s)
print(json.dumps(s))
