import json
import pathlib
HERE = pathlib.Path(__file__).resolve().parent

def micro_cases():
    rows = [('am_inline', 'inline_d_gin', 'common & token17', 10000, 4),
            ('am_absent', 'docs_d_gin', 'common & missing', 5000, 0),
            ('am_skew1000', 'docs_d_gin', 'common & rare0', 100, 200),
            ('am_full', 'docs_d_gin', 'common', 10, 200000),
            ('am_or', 'docs_d_gin', 'common | rare0', 10, 200000),
            ('am_dense', 'docs_d_gin', 'dense2 & dense3', 10, 33333),
            ('am_rare', 'docs_d_gin', 'rare0', 1000, 200),
            ('am_prefix_sparse', 'docs_d_gin', 'group1:* & rare0', 10, 53),
            ('am_prefix_full', 'docs_d_gin', 'group:*', 2, 200000)]
    return [dict(name=name, kind='am', settings='', index=index, query=query,
                 loops=loops, tids_per_scan=tids,
                 sql=f"SELECT public.gin_am_micro('g1.{index}'::regclass, '{query}'::tsquery, {loops})")
            for name,index,query,loops,tids in rows]

def plan(mode):
    assert mode == 'qualify'
    return dict(mode=mode,roles=['B','T','Bitmap'],retained_rounds=0,warmups=0,
                cases=[],orders=[],cohorts=0,raw=0,retained=0,warm=0,
                timing='Correctness only; qualification-internal clocks are not accepted benchmark observations.')
