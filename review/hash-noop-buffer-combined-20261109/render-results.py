#!/usr/bin/env python3
"""Render complete collected hash composition results; never runs a benchmark."""
import argparse,hashlib,itertools,json,math,os,pathlib,statistics
HERE=pathlib.Path(__file__).resolve().parent
ROLES=['B','T','N','H','C']
COMMITS={'B':'72b9498df9a369e747f8d96efb5a6cd33c2451e2','N':'3fc5ad43e3f932374ad4eb1fa7e2da041e5ffc3b','H':'989ba16d4557d01e9d0cf71dcf2ffe729b750f37','C':'909e76d48524f5f2c9bfed09c01f25195fb1798a'}
METRICS={'sql_explain_execution_ms':'SQL EXPLAIN Execution Time','whole_command_backend_cpu_ms':'Whole-command backend CPU','whole_command_client_wall_ms':'Whole-command client wall'}
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(pathlib.Path(path).read_text())
def close(a,b):return math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12)
def check_spread(s):
 values=s['values'];assert s['n']==len(values)==10 and all(isinstance(x,(int,float)) and math.isfinite(x) for x in values)
 median=statistics.median(values)
 expected=dict(min=min(values),median=median,max=max(values),mean=statistics.mean(values),stdev=statistics.stdev(values),MAD=statistics.median(abs(x-median) for x in values))
 assert all(close(s[k],v) for k,v in expected.items()),(s,expected)
def cell(s,percent=False):
 # Six decimal places for ms; three for same-round percentages. JSON/CSV retain
 # full values. A rounded zero percentage is displayed without a negative sign.
 precision=3 if percent else 6
 def number(value):
  if round(value,precision)==0:value=0.0
  return f'{value:+.{precision}f}' if percent else f'{value:.{precision}f}'
 return f"{number(s['median'])} [{number(s['min'])}, {number(s['max'])}]"
def link(path,output):
 target=os.path.relpath(pathlib.Path(path).resolve(),output.parent.resolve())
 return '<'+target+'>' if ' ' in target else target
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--analysis',required=True,type=pathlib.Path)
 p.add_argument('--runtime',required=True,type=pathlib.Path)
 p.add_argument('--build-receipt',required=True,type=pathlib.Path)
 p.add_argument('--fixture-receipt',required=True,type=pathlib.Path)
 p.add_argument('--gate-receipt',required=True,type=pathlib.Path)
 p.add_argument('--controller-status',required=True,type=pathlib.Path)
 p.add_argument('--controller-freeze',required=True,type=pathlib.Path)
 p.add_argument('--cases',type=pathlib.Path,default=HERE/'harness/inputs/cases.json')
 p.add_argument('--output',required=True,type=pathlib.Path,help='new BENCHMARKS.md; existing file is never overwritten')
 a=p.parse_args();assert not a.output.exists() and a.output.parent.is_dir()
 status=read(a.analysis/'status.json');absolute=read(a.analysis/'absolute.json');pairs=read(a.analysis/'pairs.json')
 assert status['status']=='PASS_COMPLETE_TWO_COHORT_RECOUNT' and status['roles']==ROLES
 assert all(status[k]==v for k,v in {'raw':2280,'retained':1900,'warm':380,'cases':19,'absolute_groups':570,'pair_groups':1140,'direct_pairs':11400}.items())
 assert status['all_plans_literals_loops_and_input_hashes_checked'] is True
 assert len(status['inputs'])==2 and {x['cohort'] for x in status['inputs']}=={0,1}
 cases=read(a.cases)['cases'];names=[c['name'] for c in cases];assert len(names)==len(set(names))==19
 runtime=read(a.runtime);build=read(a.build_receipt);fixture=read(a.fixture_receipt);gate=read(a.gate_receipt);outer=read(a.controller_status);freeze=read(a.controller_freeze)
 assert runtime['status']=='APPROVED' and runtime['base_commit']==COMMITS['B'] and list(runtime['variants'])==['B','N','H','C']
 assert runtime['build_receipt']['sha256']==sha(a.build_receipt) and runtime['fixture_receipt']['sha256']==sha(a.fixture_receipt) and runtime['correctness']['sha256']==sha(a.gate_receipt)
 assert runtime['correctness']['approved_for_timing'] is True
 for role,commit in COMMITS.items():assert runtime['variants'][role]['source_commit']==commit
 assert build['status']=='PASS_NEW_MATCHED_HASH_BUILDS' and build['base']==COMMITS['B'] and build['core239_each'] is True
 assert set(build['variants'])=={'B','N','H','C','C_assert'} and build['role_to_variant']=={'B':'B','T':'B','N':'N','H':'H','C':'C'}
 for role,v in build['variants'].items():
  assert v['commit']==COMMITS['C' if role=='C_assert' else role] and v['core239'] is True and v['expected_files_unchanged'] is True
  assert len(v['headers'])==907 and all(flag in v['cflags'].split() for flag in ['-O2','-g','-fno-lto']) and '-flto' not in v['cflags'] and '-fno-lto' in v['ldflags']
  assert v['assertions']==(role=='C_assert')
  if role!='C_assert':assert runtime['variants'][role]['postgres_sha256']==v['postgres_sha256']
 assert fixture['status']=='PASS_NEW_SEED_AND_TEN_COPIES' and fixture['build_receipt_sha256']==sha(a.build_receipt)
 assert fixture['cases_sha256']==sha(a.cases) and len(fixture['copies'])==10 and fixture['roles_assigned'] is False
 assert max(x['hash_fsync_end_ns'] for x in fixture['copies'])<=fixture['all_copy_fsync_done_ns']
 assert gate['status']=='PASS_MATCHED5_UNTIMED_GATES' and not gate['cleanup_errors'] and gate['measurement_copies_unused'] is True
 assert gate['accepted_samples']==gate['timing_samples']==0 and gate['build_receipt_sha256']==sha(a.build_receipt) and gate['fixture_receipt_sha256']==sha(a.fixture_receipt)
 assert set(gate['roles'])=={'B','N','H','C','C_assert'}
 for role,g in gate['roles'].items():
  assert g['status']=='PASS' and g['source_commit']==build['variants'][role]['commit'] and g['postgres_sha256']==build['variants'][role]['postgres_sha256']
  assert g['full19_multisets']==19 and g['historical_multisets']==18 and g['lifecycle_cases']==126 and g['cursor_cases']==21
  assert len(g['page_oracles'])==2 and all(x['status']=='PASS' and x['page_cases']==886272 and x['complete_TU'] and x['timing'] is False for x in g['page_oracles'])
 assert outer['status']=='PASS_TWO_COHORTS' and outer['samples']==2280 and outer['accepted_timing_samples']==1900 and not outer['cleanup_errors'] and not outer['remaining_owned_clusters'] and outer['all_owned_pids_absent'] is True
 assert len(outer['final_cluster_states'])==16 and all(x['pg_ctl_status_rc']==3 and x['cluster_state']=='shut down' and x['pidfile_absent'] for x in outer['final_cluster_states'])
 assert outer['final_runtime']['status']=='PASS_SOURCE_PREFIX_SEED_FROZEN_INPUTS'
 assert len(outer['births'])==10 and fixture['all_copy_fsync_done_ns']<min(x['start_ns'] for x in outer['births'])
 assert freeze['runtime_sha256']==sha(a.runtime) and freeze['fixture_sha256']==sha(a.fixture_receipt) and freeze['build_sha256']==sha(a.build_receipt) and freeze['correctness_sha256']==sha(a.gate_receipt)
 assert all(x['runtime_sha256']==sha(a.runtime) and x['fixture_sha256']==sha(a.fixture_receipt) for x in status['inputs'])
 for cohort in [0,1]:
  born=[x for x in outer['births'] if x['cohort']==cohort];assert [x['slot'] for x in born]==list(range(5)) and [x['role'] for x in born]==(ROLES if cohort==0 else list(reversed(ROLES)))
  assert all(x['nice']==10 and x['postmaster_affinity']==freeze['controller_and_background_allowed_affinity'] for x in born)
 abs_by={};pair_by={}
 for row in absolute:
  key=(row['cohort'],row['case'],row['role'],row['metric']);assert key not in abs_by;check_spread(row);assert all(x>0 for x in row['values']);abs_by[key]=row
 expected_abs=set(itertools.product([0,1],names,ROLES,METRICS));assert set(abs_by)==expected_abs and len(absolute)==570
 pair_names=list(itertools.combinations(ROLES,2));count_direct=0
 for row in pairs:
  key=(row['cohort'],row['case'],row['left'],row['right'],row['metric']);assert key not in pair_by
  check_spread(row['difference']);check_spread(row['percent']);direct=row['direct'];assert [x['round'] for x in direct]==list(range(2,12))
  left=abs_by[row['cohort'],row['case'],row['left'],row['metric']]['values'];right=abs_by[row['cohort'],row['case'],row['right'],row['metric']]['values']
  for i,x in enumerate(direct):
   assert close(x['left'],left[i]) and close(x['right'],right[i])
   assert close(row['difference']['values'][i],x['right']-x['left']) and close(row['percent']['values'][i],100*(x['right']/x['left']-1))
  pair_by[key]=row;count_direct+=len(direct)
 expected_pairs={(c,n,l,r,m) for c,n,(l,r),m in itertools.product([0,1],names,pair_names,METRICS)}
 assert set(pair_by)==expected_pairs and len(pairs)==1140 and count_direct==11400
 lines=['# Hash no-op / recent-buffer composition: complete SQL results','',
 'This is a finite warmed SQL screen on shared VM158. Each cohort is reported separately. Every case, warm observation and negative control remains in raw data; no pooling, trimming, control normalization or timing-driven repetition is used. The tables describe these fixed processes and placements, without significance, physical-host isolation or causal/additive-effect claims.','',
 '2280 raw observations = 1900 retained + 380 warm. Each of 19 cases has two warm and ten retained rounds for B/T/N/H/C in each of two fresh cohorts. The ten Williams orders give each role every position twice and every ordered adjacent pair twice. Cohort1 reverses cases and numeric role births. B and T use one exact install/ELF on separate postmasters.','',
 '| Role | Exact source commit | Backend ELF SHA256 |','|---|---|---|']
 for role in ROLES:
  actual='B' if role=='T' else role;lines.append(f"| {role} | `{COMMITS[actual]}` | `{runtime['variants'][actual]['postgres_sha256']}` |")
 lines+=['',
 'N removes the two no-op qualification predicates. H is the existing advisory recent-buffer hint. C is the exact no-op cherry-pick onto H. Rank, inline-key access, prefetch and new thresholds are absent. This new composition is measured directly against both parents; percentages from older independent campaigns are not added.','',
 'All five common-path fullclean builds (four release plus C assertions) passed the unchanged239core tests. Actual flags include `-O2 -g -fno-lto`, `LDFLAGS=-fno-lto`; compiler/configuration/header/ELF receipts are retained. Every role passed the finite ordinary page normal/UBSan,19full-multiset,18historical,126lifecycle and21cursor checks before timing. These finite checks are not a general merge, concurrency or crash-safety proof. Final source/prefix/support/seed/freeze checks passed; all16seed/smoke/accepted clusters were cleanly stopped and recorded own processes absent.','',
 'The fixture retains the original18cells and appends old H2 varying-residual rescans, with Memoize enabled and3000actual index loops. Its frozen answer is `3000|1545|190739520`. Ordinary hot/Memoize (one index loop/2999hits), disabled-Memoize3000rescans, random/absent, engineered overflow, zero/MAX collisions, tiny natural/forced and sequential off-path controls are retained. Collision present probes preserve64index loops and4999heap rechecks per probe. The19cells do not repeat the earlier H2 TEMP/unlogged timing submatrix.','',
 'Every EXPLAIN follows an identical literal-answer SELECT outside measurement: deliberate extra warming. Retained plans have zero shared reads. Shared buffers512MB, work_mem64MB, JIT/autovacuum/parallel query off, system timing clock and nice10 were fixed. No cold-I/O, native-kernel, CREATE INDEX, connection-latency or throughput-concurrency conclusion follows.','',
 'Metric boundaries: SQL is complete EXPLAIN ANALYZE Execution Time with per-node TIMING OFF; backend CPU is the whole EXPLAIN command schedstat delta, including planning/JSON/protocol; client wall is the whole persistent-psql conversation. Client JSON parsing and /proc observations are outside its wall interval. These three millisecond values are not interchangeable.','',
 'Absolute cells below are **median [min, max] milliseconds**, ten retained observations. Pair percentages are medians [min,max] of ten direct same-round `100*(right/left-1)` values; negative means the right role used less time. Pair differences are the corresponding direct `right-left` milliseconds. They are not differences/quotients of displayed medians. JSON/CSV retain full precision, all ten values, arithmetic mean, sample stdev and MAD. Printed precision does not assert clock accuracy.','']
 topo=freeze['topology'];server=freeze['server_cpus'];client=freeze['client_cpus']
 def same_core(cpus):return len(set(cpus))==2 and len({(topo[str(c)]['physical_package_id'],topo[str(c)]['core_id']) for c in cpus})==1
 lines+=['## Recorded placement','',f"Measured backend/client guest CPUs: cohort0 **{server[0]}/{client[0]}**, cohort1 **{server[1]}/{client[1]}**. Server pair {server} shares one guest core: **{str(same_core(server)).lower()}**; client pair {client} shares one guest core: **{str(same_core(client)).lower()}**. These guest sibling/core records do not establish physical-host placement or isolation.",'',f"Controller/postmasters/background launch allowed mask: `{freeze['controller_and_background_allowed_affinity']}`. Measured clients/backends are pinned by runner; background placement is not claimed pinned. Foreign workloads were left untouched. Per-command runqueue/fault/I/O and whole plans remain raw; shared-load movement is not normalized away.",'']
 for cohort in [0,1]:
  ordered=names if cohort==0 else list(reversed(names))
  for metric,label in METRICS.items():
   lines += [f'## Cohort {cohort}: {label} (ms)','', '| Case | '+' | '.join(r+' median [min,max] ms' for r in ROLES)+' |','|---|'+'---:|'*5]
   for name in ordered:lines.append('| '+name+' | '+' | '.join(cell(abs_by[cohort,name,r,metric]) for r in ROLES)+' |')
   for summary,label2 in [('percent','Direct paired percent: right/left minus1'),('difference','Direct paired difference: right minus left (ms)')]:
    lines+=['',f'### {label2}','', '| Case | '+' | '.join(r+'/'+l+(' %' if summary=='percent' else ' ms') for l,r in pair_names)+' |','|---|'+'---:|'*10]
    for name in ordered:lines.append('| '+name+' | '+' | '.join(cell(pair_by[cohort,name,l,r,metric][summary],summary=='percent') for l,r in pair_names)+' |')
   lines.append('')
 lines+=['## Evidence and limits','',
 'The formatter verified the complete570absolute/1140pair groups and11400direct observations, checked each displayed spread against all ten values, and checked every direct pair against its role values. This formats existing collected results; it runs no query or benchmark. Root owns the final interpretation. Repeated rounds on these fixed processes are not independent hardware replicates. Neither a positive nor negative median alone establishes a causal mechanism or a general performance guarantee.','']
 receipts=[('analysis status',a.analysis/'status.json'),('all absolute values',a.analysis/'absolute.json'),('all direct pairs',a.analysis/'pairs.json'),('runtime',a.runtime),('build receipt',a.build_receipt),('fixture receipt',a.fixture_receipt),('finite gate receipt',a.gate_receipt),('controller final status',a.controller_status),('controller freeze',a.controller_freeze),('case definitions',a.cases)]
 for label,path in receipts:lines.append(f'- [{label}]({link(path,a.output)}), SHA256 `{sha(path)}`.')
 with a.output.open('x') as out:out.write('\n'.join(lines)+'\n')
 print(json.dumps(dict(status='PASS_FORMATTED_EXISTING_RESULTS',output=str(a.output),sha256=sha(a.output),raw=2280,absolute_groups=570,pair_groups=1140,direct_pairs=11400,cohort_metric_blocks=6,case_table_rows=342,source_commits=COMMITS)))
if __name__=='__main__':main()
