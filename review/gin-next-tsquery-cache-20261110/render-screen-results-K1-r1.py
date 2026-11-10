#!/usr/bin/env python3
"""Render all completed K1 groups only after the independent audit has passed."""
import argparse
import hashlib
import itertools
import json
import pathlib
ROLES=['B','T','K1']
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def f(x):return format(x,'.6f')
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--run-root',type=pathlib.Path,required=True)
 p.add_argument('--analysis0',type=pathlib.Path,required=True)
 p.add_argument('--analysis1',type=pathlib.Path,required=True)
 p.add_argument('--audit',type=pathlib.Path,required=True)
 p.add_argument('--out-new',type=pathlib.Path,required=True)
 a=p.parse_args();assert not a.out_new.exists()
 audit=json.loads(a.audit.read_text());assert audit['status']=='PASS_INDEPENDENT_COMPLETE_RECOUNT'
 assert (audit['raw'],audit['retained'],audit['warm'])==(1104,828,276)
 freeze=json.loads((a.run_root/'freeze.json').read_text());assert audit['freeze_sha256']==sha(a.run_root/'freeze.json')
 assert freeze['protocol']['roles']==ROLES and len(freeze['protocol']['cases'])==23
 lines=['# K1 builtin-tsquery consistent memo: complete fixed screen','',
 '1104 raw /828 retained /276 warm, two fresh cohorts, every23 SQL/actual-AM cell and all three role pairs retained. '
 'The source alternative is exact builtin-only K1 9e0d6e84c5bd538e58a534c99cb39ca669c567b7 over fixed B '
 '8a8c475037bfde101da23cc9b0364c9c020eca93, with the identical supplied prerequisite. B/T use the same executable. '
 'No decoder metric, D1 combination, generic-opclass cache, significance or causal additive claim is made.','',
 'Environmental label: `'+audit['environment_label']+'`. Guest CPU labels do not establish independent physical resources. '
 'Cohorts remain separate; all warm/retained observations were validated. There is no trim, pooling, twin normalization '
 'or outcome-dependent case choice. Whole-command backend CPU, client wall, SQL executor time, and actual-AM inner '
 'CPU/wall have separate boundaries. A literal command executes separately before each measurement as extra warming.','',
 'All values are milliseconds for each complete fixed work unit. Pair percentages are 100*(right/left-1) per retained '
 'same-round pair; negative values mean a lower observed right metric. The ratio median need not equal the ratio of '
 'the two absolute medians. Stdev is sample stdev, with six retained values per group. Raw values/ranges/direct pairs '
 'and all controls remain in the bound analysis JSON.','']
 for cohort,folder in enumerate([a.analysis0,a.analysis1]):
  binding=audit['bindings'][str(cohort)]
  assert binding['absolute_sha256']==sha(folder/'absolute.json') and binding['pairs_sha256']==sha(folder/'pairs.json')
  absolute={(v['case'],v['role'],v['metric']):v for v in json.loads((folder/'absolute.json').read_text())}
  pairs={(v['case'],v['left'],v['right'],v['metric']):v for v in json.loads((folder/'pairs.json').read_text())}
  assert len(absolute)==228 and len(pairs)==228
  lines += [f'## Cohort {cohort}','',f'552 raw /414 retained /138 warm. Raw SHA256 `{binding["raw_sha256"]}`. '
            f'Literal SHA256 `{binding["literal_sha256"]}`.','',
            'Retained command diagnostics: `'+json.dumps(audit['cohorts'][cohort]['retained_diagnostics'],sort_keys=True)+'`. '
            'These observations do not establish the cause of any difference.','']
  for case in freeze['protocol']['cases']:
   name=case['name'];metrics=list(dict.fromkeys(k[2]for k in absolute if k[0]==name))
   assert len(metrics)==(4 if case['kind']=='am' else 3)
   work='AM loops: '+str(case['loops']) if case['kind']=='am' else 'SQL probes: '+str(case['probes'])
   lines += ['### '+name+' ('+case['kind']+')','',work+'.','']
   for metric in metrics:
    lines += ['**'+metric+' (ms)**','', '| Role | n | min | median | max | sample stdev | MAD |','|---|---:|---:|---:|---:|---:|---:|']
    for role in ROLES:
     value=absolute[name,role,metric];assert value['n']==6
     lines.append('| '+role+' | 6 | '+' | '.join(f(value[k])for k in ['min','median','max','stdev','MAD'])+' |')
    lines += ['', '| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |','|---|---:|---:|---:|---:|---:|---:|']
    for left,right in itertools.combinations(ROLES,2):
     pair=pairs[name,left,right,metric];value=pair['percent'];assert value['n']==6
     lines.append('| '+right+'/'+left+' | '+' | '.join(f(value[k])for k in ['median','min','max','stdev','MAD'])+' | '+f(pair['difference']['median'])+' |')
    lines.append('')
 lines += ['## Scope and prior work','',
 'Full B/K1/K1_assert source/header/production-compiler/core/native-dispatch and ordinary SQL/generic-fallback '
 'qualification must precede this screen. The source only opts into exact known builtin support OIDs and function '
 'addresses; arbitrary opclasses and shim paths retain their callbacks. It stores a single bounded ternary vector '
 'and complete FALSE/TRUE/MAYBE result for one scan-key lifetime, preserving native tri recheck state. '
 'The untimed repetition probe motivated full-read/OR targets and zero-reuse dense negatives; it was not latency evidence.','',
 'Consistent-result caching was already proposed in [Heikki 2014](https://www.postgresql.org/message-id/52F373CC.4050800%40vmware.com). '
 'This bounded prototype makes no novelty claim for that idea. Complete build/cleanup/source-freeze receipts and raw '
 'reproduction scripts must accompany the final artifact. This renderer itself creates no performance observation.','']
 a.out_new.write_text('\n'.join(lines))
 receipt=dict(status='RENDERED_ALL_AUDITED_K1_GROUPS',sha256=sha(a.out_new),bytes=a.out_new.stat().st_size,
              audit_sha256=sha(a.audit),absolute_groups=456,pair_groups=456,direct_pairs=2736,new_timing_samples=0)
 a.out_new.with_suffix(a.out_new.suffix+'.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
