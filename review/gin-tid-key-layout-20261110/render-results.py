#!/usr/bin/env python3
"""Export every absolute group and direct pair, without changing observations."""
import argparse,csv,json,pathlib
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('analysis',type=pathlib.Path);p.add_argument('out_new',type=pathlib.Path)
a=p.parse_args();a.out_new.mkdir()
absrows=json.loads((a.analysis/'absolute.json').read_text())
pairs=json.loads((a.analysis/'pairs.json').read_text())
with (a.out_new/'absolute.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['case','role','metric','n','min_ms','median_ms','max_ms','mean_ms','stdev_ms','MAD_ms'])
 for x in absrows:w.writerow([x[k] for k in ['case','role','metric','n','min','median','max','mean','stdev','MAD']])
with (a.out_new/'pairs.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['case','left','right','metric','n','min_percent','median_percent','max_percent','stdev_percent','MAD_percent','median_delta_ms'])
 for x in pairs:w.writerow([x[k] for k in ['case','left','right','metric']]+[x['percent'][k] for k in ['n','min','median','max','stdev','MAD']]+[x['difference']['median']])
lines=['# All absolute observations and paired changes','', 'Each group is one cohort and one metric. Negative paired changes mean less time. Medians of paired percentages are not ratios of aggregate medians. No trimming, pooling or baseline-twin normalization. Full per-round values remain in the analysis JSON and raw observations.','', '| Case | Role | Metric | n | Min ms | Median ms | Max ms | SD ms | MAD ms |','|---|---|---|---:|---:|---:|---:|---:|---:|']
for x in absrows:lines.append('| '+ ' | '.join([x['case'],x['role'],x['metric'],str(x['n'])]+[format(x[k],'.6f') for k in ['min','median','max','stdev','MAD']])+' |')
lines+=['','| Case | Right/left | Metric | n | Min % | Median % | Max % | SD % | MAD % | Median delta ms |','|---|---|---|---:|---:|---:|---:|---:|---:|---:|']
for x in pairs:lines.append('| '+' | '.join([x['case'],x['right']+'/'+x['left'],x['metric'],str(x['percent']['n'])]+[format(x['percent'][k],'.4f') for k in ['min','median','max','stdev','MAD']]+[format(x['difference']['median'],'.6f')])+' |')
(a.out_new/'ALL-RESULTS.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(dict(absolute_groups=len(absrows),direct_pair_groups=len(pairs))))
