#!/usr/bin/env python3
"""Same command history on EVERY timed backend; retained external answer oracle."""
import hashlib,json,os

def digest(value):
 return hashlib.sha256(json.dumps(value,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def verify_all(sessions,root,cases,fixtures,phase):
 oracle=json.loads((root/'oracle.json').read_text());answers={};checksums={};histories={v:[]for v in sessions};original={v:s.command for v,s in sessions.items()};status='INCOMPLETE'
 def wrap(v):
  def command(sql):
   entry={'sql':sql};histories[v].append(entry)
   result=original[v](sql);entry['result_sha256']=hashlib.sha256(result.encode()).hexdigest();return result
  return command
 for v,s in sessions.items():s.command=wrap(v)
 sequential='SET enable_seqscan=on;SET enable_indexscan=off;SET enable_indexonlyscan=off;SET enable_bitmapscan=off;'
 try:
  for name,d in cases.items():
   expected=oracle['cases'][name];refsql=expected['reference_sql'];answers[name]={'reference_sql':refsql,'reference_result':expected['reference_result'],'sequential_sha256':expected['sequential_sha256'],'variants':{}}
   for v,s in sessions.items():
    s.command(sequential);reference=s.command(refsql+';')
    assert hashlib.sha256(reference.encode()).hexdigest()==expected['sequential_sha256']and reference==expected['reference_result'],(v,name,'Sequential answer differs from retained oracle')
    s.settings(d['planner']);actual=s.command(d['sql']+';');assert actual==reference,(v,name,'Indexed answer mismatch')
    answers[name]['variants'][v]={'result':actual,'sha256':hashlib.sha256(actual.encode()).hexdigest()}
  for fixture in fixtures:
   name=fixture['name'];cols=','.join(fixture['indexed_columns']);query=f'SELECT json_build_array(count(*),sum(hashtextextended(ROW({cols})::text,0)::numeric))::text FROM {name};';expected=oracle['fixtures'][name]
   assert query==expected['query'],name
   checksums[name]={'query':query,'sequential_sha256':expected['sequential_sha256'],'variants':{}}
   for v,s in sessions.items():
    s.command(sequential);reference=s.command(query);assert hashlib.sha256(reference.encode()).hexdigest()==expected['sequential_sha256'],(v,name,'Sequential checksum mismatch')
    s.settings('forced_ios');actual=s.command(query);assert actual==reference,(v,name,'Indexed fixture checksum mismatch')
    checksums[name]['variants'][v]=hashlib.sha256(actual.encode()).hexdigest()
  command_lists={v:[x['sql']for x in trace]for v,trace in histories.items()};result_lists={v:[x.get('result_sha256')for x in trace]for v,trace in histories.items()};first=next(iter(sessions));expected_count=4*(len(cases)+len(fixtures))
  assert all(len(trace)==expected_count for trace in histories.values())
  assert all(x==command_lists[first]for x in command_lists.values()),'Different statement history'
  assert all(x==result_lists[first]for x in result_lists.values()),'Different validation responses'
  status='PASS'
 finally:
  for v,s in sessions.items():s.command=original[v]
  receipt={'status':status,'phase':phase,'scope':'Executed same sequential-reference/actual-query/checksum/GUC statement order in every timed persistent backend before CHECKPOINT and timed rounds. This does not prove all backend/shared state equal. Old R2 used asymmetric histories and remains unchanged.','expected_command_count_per_role':4*(len(cases)+len(fixtures)),'roles':{v:{'pid':sessions[v].pid,'command_count':len(trace),'statement_sequence_sha256':digest([x['sql']for x in trace]),'response_sequence_sha256':digest([x.get('result_sha256')for x in trace]),'statements':trace}for v,trace in histories.items()}}
  (root/f'results-confirm/validation-history-{phase}.json').write_text(json.dumps(receipt,indent=2)+'\n')
 prefix=os.environ.get('IOS_RESULT_PREFIX',f'phase-{phase}-')
 (root/f'results-confirm/{prefix}answers.json').write_text(json.dumps(answers,indent=2)+'\n')
 (root/f'results-confirm/{prefix}fixture-checksums.json').write_text(json.dumps(checksums,indent=2)+'\n')
 return receipt
