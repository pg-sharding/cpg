#!/usr/bin/env python3
"""Engineered absent-full-hash holdout; never alters existing index contents."""
import argparse,hashlib,json,pathlib,subprocess,time
p=argparse.ArgumentParser();p.add_argument('--psql',required=True);p.add_argument('--dsn',required=True);p.add_argument('--output-dir',type=pathlib.Path,required=True);a=p.parse_args()
a.output_dir.mkdir(exist_ok=True)
def sql(s):
 return subprocess.check_output([a.psql,'-XAtq','-d',a.dsn,'-v','ON_ERROR_STOP=1','-c',"SET search_path=h1,public,pg_catalog;SET statement_timeout='30s';SET work_mem='64MB';"+s],text=True).strip()
meta=json.loads(sql("SELECT row_to_json(m) FROM hash_metapage_info(get_raw_page('h1.skew_hash',0))m;"))
pages=json.loads(sql("""WITH pages AS MATERIALIZED (
 SELECT g blk,get_raw_page('h1.skew_hash',g) raw FROM generate_series(1,pg_relation_size('h1.skew_hash')/8192-1)g
), kinds AS MATERIALIZED (SELECT *,hash_page_type(raw) kind FROM pages)
SELECT json_agg(row_to_json(s)) FROM (
 SELECT blk,kind,st.hasho_bucket bucket,st.hasho_nextblkno next,st.hasho_prevblkno previous,
  x.n,x.distinct_hashes,x.min_hash,x.max_hash
 FROM kinds CROSS JOIN LATERAL hash_page_stats(CASE WHEN kind IN ('bucket','overflow') THEN raw ELSE NULL END)st
 CROSS JOIN LATERAL (SELECT count(*) n,count(DISTINCT data) distinct_hashes,min(data) min_hash,max(data) max_hash FROM hash_page_items(CASE WHEN kind IN ('bucket','overflow') THEN raw ELSE NULL END))x
 WHERE kind IN ('bucket','overflow')
)s;"""))
over=[x for x in pages if x['kind']=='overflow' and x['n']>8]
assert over,'existing skew index has no suitable overflow page'
# The deterministic discovery rule predates timing: narrowest relative spread,
# then largest page, then lowest block. This is an adversarial engineered case.
chosen=min(over,key=lambda x:((x['max_hash']-x['min_hash'])/max(x['n'],1),-x['n'],x['blk']))
bucket=chosen['bucket'];byblock={x['blk']:x for x in pages}
primary=[x for x in pages if x['kind']=='bucket' and x['bucket']==bucket]
assert len(primary)==1
chain=[];page=primary[0]
while True:
 assert page['bucket']==bucket and page['blk'] not in [x['blk'] for x in chain]
 chain.append(page)
 if page['next']==4294967295:break
 page=byblock[page['next']]
assert len(chain)>=2
high,low,maxbucket=meta['highmask'],meta['lowmask'],meta['maxbucket']
def bucket_expr(h):return f'CASE WHEN ({h}&{high})>{maxbucket} THEN ({h}&{low}) ELSE ({h}&{high}) END'
stored=json.loads(sql(f"SELECT json_agg(row_to_json(s)) FROM (SELECT DISTINCT k,(hashint8(k)::bigint&4294967295) hash FROM h1.skew_keys WHERE {bucket_expr('(hashint8(k)::bigint&4294967295)')}={bucket} ORDER BY k)s;"))
stored_hashes={x['hash'] for x in stored};assert stored_hashes
probe=[];start=1000000000;batches=[]
while len(probe)<3000:
 end=start+99999
 query=f"SELECT coalesce(json_agg(row_to_json(s)),'[]'::json) FROM (SELECT g k,(hashint8(g)::bigint&4294967295) hash FROM generate_series({start}::bigint,{end}::bigint)g WHERE {bucket_expr('(hashint8(g)::bigint&4294967295)')}={bucket} AND (hashint8(g)::bigint&4294967295) NOT IN ({','.join(map(str,sorted(stored_hashes)))}) ORDER BY g LIMIT {3000-len(probe)})s;"
 got=json.loads(sql(query));probe.extend(got);batches.append(dict(start=start,end=end,accepted=len(got)))
 start=end+1;assert len(batches)<=100
assert len({x['k'] for x in probe})==3000 and all(x['hash'] not in stored_hashes for x in probe)
for x in probe:
 b=x['hash']&high
 if b>maxbucket:b&=low
 assert b==bucket
values=','.join(f"({i+1},{x['k']},{x['hash']})" for i,x in enumerate(probe))
sql("CREATE TABLE h1.probes_skew_holdout(id integer,k bigint,full_hash bigint);INSERT INTO h1.probes_skew_holdout VALUES "+values+";ANALYZE h1.probes_skew_holdout;")
absent=int(sql("SELECT count(*) FROM h1.probes_skew_holdout p JOIN h1.skew_keys h ON h.k=p.k;"));assert absent==0
receipt=dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),purpose='ENGINEERED adversarial holdout, not a representative workload claim',meta=meta,selected_overflow=chosen,primary_chain=chain,hot_key=stored[0],stored_keys_and_full_hashes=stored,probe_count=len(probe),distinct_keys=len({x['k'] for x in probe}),probe_full_hash_range=[min(x['hash'] for x in probe),max(x['hash'] for x in probe)],same_actual_bucket=bucket,different_from_every_stored_full_hash=True,absent_join_matches=absent,search_batches=batches,discovery_rule='Among overflow pages n>8, min((max_hash-min_hash)/n), then max(n), then min(block). Use that actual bucket.',generation_script_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest())
(a.output_dir/'holdout-discovery.json').write_text(json.dumps(receipt,indent=2)+'\n')
(a.output_dir/'holdout-probes.json').write_text(json.dumps(probe,indent=2)+'\n')
(a.output_dir/'holdout-insert.sql').write_text("-- Exact frozen probe values; run only in a fresh owned fixture.\nCREATE TABLE h1.probes_skew_holdout(id integer,k bigint,full_hash bigint);\nINSERT INTO h1.probes_skew_holdout VALUES "+values+";\nANALYZE h1.probes_skew_holdout;\n")
print(json.dumps(dict(status='PASS',bucket=bucket,chain_pages=len(chain),selected_overflow=chosen,probes=len(probe))))
