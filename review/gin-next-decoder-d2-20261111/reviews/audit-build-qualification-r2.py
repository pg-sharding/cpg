#!/usr/bin/env python3
"""Local independent metadata/source/ordinary valid decoder and SQL recount; no remote/DB/compiler."""
import argparse,hashlib,importlib.util,json,pathlib,shlex,time
HERE=pathlib.Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(pathlib.Path(p).read_text())
def nodes(n):
 yield n
 for x in n.get('Plans',[]):yield from nodes(x)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=pathlib.Path,default=HERE/'evidence-r1');p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();assert not a.output.exists();r=a.evidence;bdir=r/'build-r1';q=r/'qualification-r1';out=dict(status='RUNNING_LOCAL_METADATA_RECOUNT',started_ns=time.time_ns(),timing_samples=0)
 try:
  collection=load(HERE/'ROOT-COLLECTION-BUILD-QUALIFICATION-r1.json');assert collection['status']=='PASS_ROOT_READONLY_SSH_LIST_AND_EXPLICIT_SCP_TEXT';manifest=load(r/'REMOTE-SELECTED-TEXT-r1.json');assert len(manifest['files'])==collection['files']==329
  for name,x in manifest['files'].items():assert(r/name).stat().st_size==x['bytes']and sha(r/name)==x['sha256'],name
  b=load(bdir/'build-receipt.json');bs=load(bdir/'status.json')if(bdir/'status.json').exists()else None;s=load(q/'status.json');spec=load(HERE/'build-source/SOURCE.json');baseline={n:{k:v[k]for k in ['bytes','sha256']}for n,v in load(HERE/'build-source/base-source-files.json').items()}
  assert b['status']=='PASS_GIN_D2_MATCHED_BUILDS'and b['core239_each'];assert set(b['variants'])=={'B','D1','D2','D2_assert'}
  if bs is not None:assert bs['status']==b['status']and bs['core_cleanup_errors']==[]
  else:out['build_status_collection_note']='build-r1/status.json not in selected329; build cleanup was required by actual frozen common.checked_build before the passing qualification. No independent live cleanup claim from absent metadata.'
  assert b['source_plan_sha256']==s['source_plan_sha256']==sha(HERE/'build-source/SOURCE.json')=='882122bce7ebbfd93f218e978ccc6dde510449d09796230b119eac331638615b'
  assert s['status']=='PASS_D2_ORDINARY_SQL_AND_VALID_DECODER'and s['remaining_owned']==s['timing_samples']==0 and s['cleanup_errors']==[];assert s['build_receipt_sha256']==sha(bdir/'build-receipt.json')
  for name in ['BUILD-INPUTS-D2-r1.json','QUALIFICATION-INPUTS-D2-r1.json','TIMING-INPUTS-D2-r1.json']:
   for n,x in load(HERE/name)['files'].items():assert(HERE/n).stat().st_size==x['bytes']and sha(HERE/n)==x['sha256'],n
  for n,x in load(q/'frozen-inputs.json').items():assert sha(HERE/'qualification'/n)==x['sha256']
  ref=load(HERE/'qualification/reference-B.json');cases=load(HERE/'qualification/inputs/queries.json')['cases']+load(HERE/'qualification/inputs/queries-holdout.json')['cases'];answers=load(HERE/'qualification/inputs/answers.json');assert len(cases)==25 and len(ref['rows'])==47
  audit_spec=importlib.util.spec_from_file_location('own_math',HERE/'timing-prep-r1/audit-independent-r1.py');own=importlib.util.module_from_spec(audit_spec);audit_spec.loader.exec_module(own)
  expected_decoder=[]
  for name,n,shift,seg,first,loops in own.DECODE:
   v=own.decoder_expected(n,shift,seg,first,loops);expected_decoder.append(dict(name=name,items=n,bytes=v['compressed_bytes'],segments=v['segments'],checksum=v['checksum']))
  assert sum(c['items']for c in expected_decoder)==13152
  native_expected=dict(status='PASS_VALID_DECODER',timing_samples=0,cases=expected_decoder,checked_items=13152);assert native_expected==ref['decoder']
  base_objects=load(bdir/'B-backend-objects.json');base_headers=load(bdir/'B-headers.json');roles={};ordered=lifecycle=decoder_count=decoder_items=0
  for role in ['B','D1','D2','D2_assert']:
   label='D2'if role=='D2_assert'else role;v=b['variants'][role];assert v['commit']==spec['variants'][label]['commit']and v['assertions']==role.endswith('_assert')
   want=dict(baseline);want.update(spec['variants'][label]['source_files']);source=load(bdir/(role+'-source-inventory.json'));assert len(source)==7726 and source==want;assert v['source_manifest_sha256']==sha(bdir/(role+'-source-inventory.json'));assert v['source_edited_files']==spec['variants'][label]['source_files'];assert v['expected_files_unchanged']and v['core239']and v['postinglist_check']
   for what in ['core239','postinglist-check']:assert load(bdir/(role+'-'+what+'.log.command.json'))['returncode']==0
   headers=load(bdir/(role+'-headers.json'));assert len(headers)==907 and headers==v['headers']and sha(bdir/(role+'-headers.json'))==v['headers_sha256']
   objects=load(bdir/(role+'-backend-objects.json'));assert sha(bdir/(role+'-backend-objects.json'))==v['backend_objects_sha256']
   changed=None if role=='D2_assert' else []
   if role!='D2_assert':
    assert headers==base_headers and objects.keys()==base_objects.keys();changed=[n for n in objects if objects[n]!=base_objects[n]];assert set(changed)<={'access/gin/ginpostinglist.o'}and changed==v['changed_backend_objects_from_B']
    for unit,value in v['normal_objects'].items():assert sha(bdir/pathlib.Path(value['asm']).name)==value['asm_sha256']and objects['access/gin/'+unit+'.o']['sha256']==value['object_sha256']
   x=load(q/role/'result.json');assert x['status']=='PASS'and x['timing_samples']==0 and sha(q/role/'result.json')==s['variants'][role]['sha256'];assert x['source_commit']==v['commit']and x['postgres_sha256']==v['postgres_sha256']and x['headers_sha256']==v['headers_sha256']and x['module_source_sha256']==sha(HERE/'qualification/decoder-native.c')
   assert x['production_flags']==shlex.split(v['cflags'])+shlex.split(v['cppflags'])
   assert x['decoder']==load(q/role/'decoder-raw.txt')==native_expected;decoder_count+=18;decoder_items+=13152
   assert len(x['cases'])==25 and len(x['extra_cases'])==15 and len(x['prepared'])==7
   for c in cases:
    n=c['name'];value=x['cases'][n];proof=load(q/(role+'-'+n+'.json'));assert value['literal']==answers[n]and value['multiset']==ref['rows'][n]==proof['actual']==proof['reference'];ordered+=1
    indexes=[node['Index Name']for node in nodes(value['plan'])if'Index Name'in node];assert c['index']in indexes if c['index']else not indexes
   for n,value in x['extra_cases'].items():assert value['actual']==value['reference']==ref['rows'][n]and int(value['count'])==value['actual']['rows'];ordered+=1
   for query,value in x['prepared'].items():assert value['actual']==value['reference']==value['repeated']==ref['rows']['prepared-'+query];ordered+=1
   assert x['lifecycle']==ref['lifecycle']
   for phase,values in x['lifecycle'].items():
    for query,value in values.items():
     name='writes-'+phase+'-'+query.replace(' ','').replace('&','and').replace('|','or');proof=load(q/(role+'-'+name+'.json'));assert proof['actual']==proof['reference']==value;lifecycle+=1
   roles[role]=dict(commit=v['commit'],postgres_sha256=v['postgres_sha256'],headers=907,source_files=7726,changed_backend_objects_vs_B=changed,backend_object_comparison_scope='not_applicable_assert_build'if role=='D2_assert'else'release_objects_compared_with_B',decoder_cases=18,decoder_items=13152,module_sha256=x['module_sha256'])
  assert ordered==188 and lifecycle==48 and decoder_count==72 and decoder_items==52608
  assert len(s['clusters'])==5
  for cluster in s['clusters']:assert cluster['stopped']and cluster['stop_proof']==dict(pg_ctl_status_rc=3,cluster_state='shut down',pidfile_absent=True)
  out.update(status='PASS_INDEPENDENT_D2_BUILD_AND_ORDINARY_QUALIFICATION_RECOUNT',selected_text_files=329,selected_text_bytes=collection['bytes'],roles=roles,core239_builds=4,postinglist_builds=4,source_expected_unchanged=True,decoder_cases=decoder_count,decoder_item_checks=decoder_items,ordered_SQL_prepared_hash_comparisons=ordered,lifecycle_comparisons=lifecycle,stopped_runtime_clusters=5,build_receipt_sha256=sha(bdir/'build-receipt.json'),qualification_status_sha256=sha(q/'status.json'),source_plan_sha256=b['source_plan_sha256'],scope='Local recount of root-collected exact text proofs; no new live process/prefix inspection or execution.',finished_ns=time.time_ns())
 except BaseException as exc:out.update(status='FAILED_PRESERVED',error=repr(exc));raise
 finally:a.output.write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps(out))
if __name__=='__main__':main()
