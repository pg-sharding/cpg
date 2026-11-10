#!/usr/bin/env python3
"""Offline byte/check/count replay only; never compiles, connects to a DB, or uses network."""
import argparse,json,pathlib,subprocess,time,traceback
HERE=pathlib.Path(__file__).resolve().parent

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir();state=dict(status='RUNNING_OFFLINE_RECOUNT',started_ns=time.time_ns(),commands=[],new_Linux_runtime=False)
 try:
  view=out/'input-view';view.mkdir()
  for member in (HERE/'inputs').iterdir():(view/member.name).symlink_to(member.resolve(),target_is_directory=member.is_dir())
  (view/'build-selected-r1').symlink_to((HERE/'evidence/build-selected-r1').resolve(),target_is_directory=True)
  commands=[['python3','-B',str(HERE/'portable-replay-r1.py'),'--static-check'],['python3','-B',str(HERE/'review-tools/audit-qualification-independent-r1.py'),'--inputs',str(view),'--collection',str(HERE/'evidence/runtime-selected-r1'),'--output',str(out/'qualification.json')],['python3','-B',str(HERE/'review-tools/audit-captures-independent-r1.py'),'--inputs',str(view),'--collection',str(HERE/'evidence/runtime-selected-r1'),'--output',str(out/'captures.json')]]
  for command in commands:
   result=subprocess.run(command,capture_output=True,text=True,timeout=120);state['commands'].append(dict(args=command,returncode=result.returncode,stdout=result.stdout,stderr=result.stderr));assert result.returncode==0,result.stderr
  for generated,recorded in [('qualification.json','QUALIFICATION-INDEPENDENT-AUDIT-r1.json'),('captures.json','CAPTURE-INDEPENDENT-AUDIT-r1.json')]:
   fresh=json.loads((out/generated).read_text());old=json.loads((HERE/'evidence'/recorded).read_text())
   for value in [fresh,old]:
    for key in ['started_ns','finished_ns']:value.pop(key,None)
   assert fresh==old,(generated,'recorded recount differs')
  state.update(status='PASS_RECORDED_QUALIFICATION_AND_EIGHTEEN_CAPTURE_REPLAY',finished_ns=time.time_ns())
 except BaseException as exc:state.update(status='FAILED_PRESERVED',error=repr(exc),traceback=traceback.format_exc());raise
 finally:(out/'status.json').write_text(json.dumps(state,indent=2)+'\n')
 print(json.dumps(dict(status=state['status'],new_Linux_runtime=False)))
if __name__=='__main__':main()
