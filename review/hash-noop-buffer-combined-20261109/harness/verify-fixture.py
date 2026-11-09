#!/usr/bin/env python3
"""Untimed ordinary SQL Seq/hash EXCEPT ALL and literal-answer checks."""
import argparse,json,pathlib,subprocess
from common import HERE,sha,save
from schedule import CASES
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--psql',required=True);p.add_argument('--dsn',action='append',required=True,help='label=owned local DSN');p.add_argument('--output',required=True,type=pathlib.Path);a=p.parse_args();assert not a.output.exists()
 answers=json.loads((HERE/'inputs/confirmation-answers.json').read_text());records=[]
 for item in a.dsn:
  role,dsn=item.split('=',1)
  for c in CASES:
   sql="BEGIN ISOLATION LEVEL REPEATABLE READ;SET LOCAL search_path=h1,public,pg_catalog;SET LOCAL work_mem='64MB';SET LOCAL statement_timeout='180s';SET LOCAL lock_timeout='10s';SET LOCAL enable_seqscan=on;SET LOCAL enable_indexscan=off;SET LOCAL enable_bitmapscan=off;CREATE TEMP TABLE replay_ref ON COMMIT DROP AS "+c['rows_sql']+";SET LOCAL enable_seqscan=off;SET LOCAL enable_indexscan=on;SET LOCAL enable_bitmapscan=on;CREATE TEMP TABLE replay_got ON COMMIT DROP AS "+c.get('rows_index_sql',c['rows_sql'])+";SELECT json_build_object('ref_count',(SELECT count(*)FROM replay_ref),'got_count',(SELECT count(*)FROM replay_got),'difference',(SELECT count(*)FROM((TABLE replay_ref EXCEPT ALL TABLE replay_got)UNION ALL(TABLE replay_got EXCEPT ALL TABLE replay_ref))d),'ref_md5',(SELECT md5(coalesce(string_agg(id::text,','ORDER BY id),''))FROM replay_ref),'got_md5',(SELECT md5(coalesce(string_agg(id::text,','ORDER BY id),''))FROM replay_got));COMMIT;"
   result=json.loads(subprocess.check_output([a.psql,'-XAtq','-v','ON_ERROR_STOP=1','-d',dsn,'-c',sql],text=True,timeout=210));assert result['difference']==0 and result['ref_count']==result['got_count'] and result['ref_md5']==result['got_md5']
   sql="SET search_path=h1,public,pg_catalog;SET jit=off;SET max_parallel_workers_per_gather=0;SET statement_timeout='180s';"+c['settings']+';'+c['sql']+';'
   answer=subprocess.check_output([a.psql,'-XAtq','-v','ON_ERROR_STOP=1','-d',dsn,'-c',sql],text=True,timeout=210).strip();assert answer==answers[c['name']]['answer']
   records.append(dict(role=role,case=c['name'],aggregate_answer=answer,**result))
 for case in CASES:
  rows=[r for r in records if r['case']==case['name']];assert len({(r['ref_count'],r['ref_md5']) for r in rows})==1
 save(a.output,dict(status='PASS_NEW_FIXTURE_FULL_MULTISETS',cases_per_DSN=19,results=records,input_sha256={n:sha(HERE/'inputs'/n) for n in ['cases.json','confirmation-answers.json']},scope='Finite ordinary static-data preparation only; no performance or concurrency claim.'))
if __name__=='__main__':main()
