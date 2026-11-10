#!/usr/bin/env python3
"""Render every already-audited screen group; no measurements or inferred claims."""
import argparse
import hashlib
import itertools
import json
import pathlib

ROLES=['B','T','S1','D1','C9']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def f(value):return format(value,'.6f')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-root',type=pathlib.Path,required=True)
    p.add_argument('--analysis0',type=pathlib.Path,required=True)
    p.add_argument('--analysis1',type=pathlib.Path,required=True)
    p.add_argument('--audit',type=pathlib.Path,required=True)
    p.add_argument('--out-new',type=pathlib.Path,required=True)
    a=p.parse_args();assert not a.out_new.exists()
    audit=json.loads(a.audit.read_text());assert audit['status']=='PASS_INDEPENDENT_COMPLETE_RECOUNT'
    assert (audit['raw'],audit['retained'],audit['warm'])==(4920,4100,820)
    freeze=json.loads((a.run_root/'freeze.json').read_text())
    assert audit['freeze_sha256']==sha(a.run_root/'freeze.json')
    cases=freeze['protocol']['cases'];assert len(cases)==41
    lines=['# S1 startup / D1 decoder fixed shared-load diagnostic','',
           'This completed screen contains 4920 raw observations: 4100 retained and 820 warm. '
           'Both fresh cohorts are shown separately. VM84 was under foreign shared load; '
           'guest server/client CPU labels do not establish independent physical resources. '
           'The exact-executable B/T control and all negative cases are retained. '
           'There is no pooling, trimming, control normalization, significance or causal attribution.','',
           'All timings are milliseconds for the complete fixed work unit, without per-item or per-loop normalization. '
           'SQL executor time, whole-command backend CPU/client wall, actual-AM inner CPU/wall, and decoder '
           'allocation/materialization/free CPU have separate boundaries. The literal answer ran separately '
           'before every measured command and provided identical extra warming. All observations were persisted '
           'before parsing/acceptance. Full raw values and same-round pairs remain in the bound analysis files.','',
           'S1 and D1 are independent source alternatives over fixed B, with the identical opaque supplied '
           'prerequisite. C9 is the existing lazy/gallop/exact-count comparison. This matrix contains no D1+C9 '
           'combination and establishes no decoder benefit on C9. CF7352 output sizing is not included.','',
           '- Raw B72: `72b9498df9a369e747f8d96efb5a6cd33c2451e2`.',
           '- Fixed B: `8a8c475037bfde101da23cc9b0364c9c020eca93`.',
           '- Canonical S1: `832af7d60b9d4c69a5f922dd1522a917bf337761` (same source tree as historical built commit).',
           '- Canonical D1: `c2b5dd6f9012cc4a27628c9d6c507ac467795ac5` (same source tree as historical built commit).',
           '- C9: `0ab3bd65c8957ea5e25f9ef8981401f0616d99de`.',
           '', 'The original build/source identity receipts remain unchanged. Canonical root-authored commits '
           'were published afterwards with identical source trees; that identity correction was not a rebuild.','',
           'Pair percentages are `100 * (right / left - 1)` on each same-round retained pair. '
           'A negative percentage means the right role had a lower observed metric. Absolute and percentage '
           'ranges are minima and maxima over ten retained rounds; stdev is the sample standard deviation.','']
    for cohort,analysis in enumerate([a.analysis0,a.analysis1]):
        binding=audit['bindings'][str(cohort)]
        assert binding['absolute_sha256']==sha(analysis/'absolute.json')
        assert binding['pairs_sha256']==sha(analysis/'pairs.json')
        status=json.loads((analysis/'status.json').read_text())
        assert status['status']=='PASS' and status['cohort']==cohort
        absolute={(x['case'],x['role'],x['metric']):x for x in json.loads((analysis/'absolute.json').read_text())}
        pairs={(x['case'],x['left'],x['right'],x['metric']):x for x in json.loads((analysis/'pairs.json').read_text())}
        lines += [f'## Cohort {cohort}','',f'2460 raw / 2050 retained / 410 warm. Raw SHA256 `{binding["raw_sha256"]}`. '
                  f'Literal SHA256 `{binding["literal_sha256"]}`.','',
                  'Retained command diagnostics: `'+json.dumps(audit['cohorts'][cohort]['retained_diagnostics'],sort_keys=True)+'`. '
                  'Queue/fault/I/O observations describe this shared-load run; they do not explain candidate differences.','']
        for case in cases:
            name=case['name'];kind=case['kind']
            metrics=list(dict.fromkeys(k[2] for k in absolute if k[0]==name))
            assert len(metrics)==(4 if kind=='am' else 3)
            unit='SQL command' if kind=='sql' else ('actual AM loop command' if kind=='am' else 'decoder loop command')
            lines += [f'### {name} ({kind})','',f'Fixed work unit: {unit}. '+(f'Loops: {case["loops"]}.' if 'loops' in case else f'Index/Seq probes: {case["probes"]}.'),'']
            for metric in metrics:
                lines += [f'**{metric} (ms)**','', '| Role | n | min | median | max | sample stdev | MAD |', '|---|---:|---:|---:|---:|---:|---:|']
                for role in ROLES:
                    x=absolute[name,role,metric];assert x['n']==10
                    lines.append('| '+role+' | 10 | '+' | '.join(f(x[k]) for k in ['min','median','max','stdev','MAD'])+' |')
                lines += ['', '| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |', '|---|---:|---:|---:|---:|---:|---:|']
                for left,right in itertools.combinations(ROLES,2):
                    pair=pairs[name,left,right,metric];x=pair['percent'];assert x['n']==10
                    lines.append('| '+right+'/'+left+' | '+' | '.join(f(x[k]) for k in ['median','min','max','stdev','MAD'])+' | '+f(pair['difference']['median'])+' |')
                lines.append('')
    lines += ['## Reproduction and limits','',
              'Use the accompanying exact build/source manifests, untouched SQL fixture/answers, runtime '
              'scripts, SCREEN-REPRODUCE.md and cleanup/source-install receipts. Rebuild and qualify in a new '
              'owned namespace on another host; do not relabel new ELFs as these observations. The full '
              'analyzer can be replayed locally after restoring raw/literal chunks and preserving relative '
              'input paths. All six original builds and correctness gates passed before timing; the main '
              'screen stopped all ten accepted clusters, and the separate smoke stopped its five clusters. '
              'Root final live inventory/PID proofs provide the external state check.','',
              'Startup pays an extra metadata lookup on positive cases; short/inline/OR/NOT and Seq controls '
              'remain visible above. Decoder long deltas, tiny lists, segment growth and scalar tails remain '
              'visible even if a targeted one-byte case improves. No result here establishes a clean-host '
              'speedup, cross-variant causality or production recommendation.','',
              'Prior art: [CF7352 output sizing](https://commitfest.postgresql.org/patch/7352/) and '
              '[Heikki 2014](https://www.postgresql.org/message-id/52F373CC.4050800%40vmware.com). '
              'The retained archive evidence pins these references; no new novelty search is claimed.','']
    a.out_new.write_text('\n'.join(lines))
    receipt=dict(status='RENDERED_ALL_AUDITED_GROUPS',output=str(a.out_new),sha256=sha(a.out_new),bytes=a.out_new.stat().st_size,
                 audit_sha256=sha(a.audit),cohorts=2,cases_per_cohort=41,absolute_groups=1300,pair_groups=2600,
                 units='milliseconds for fixed command/inner work units; percent direct ratios',timing_observations_created=0)
    a.out_new.with_suffix(a.out_new.suffix+'.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))

if __name__=='__main__':main()
