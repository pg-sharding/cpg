\set ON_ERROR_STOP on
SET enable_seqscan=off;
SET jit=off;
SET plan_cache_mode=force_generic_plan;
PREPARE s2_rescan(box) AS SELECT count(*),md5(coalesce(string_agg(id::text,',' ORDER BY id),'')) FROM s2.boxes WHERE b && $1;
EXECUTE s2_rescan('((100,100),(101,101))');
EXECUTE s2_rescan('((0,0),(0,0))');
EXECUTE s2_rescan('((1000,1000),(2000,2000))');
EXECUTE s2_rescan('((NaN,0),(NaN,0))');
EXECUTE s2_rescan(NULL);
EXECUTE s2_rescan('((0,0),(100,100))');
EXECUTE s2_rescan('((100,100),(101,101))');
EXECUTE s2_rescan('((Infinity,Infinity),(-Infinity,-Infinity))');
EXECUTE s2_rescan('((1000,1000),(2000,2000))');
EXECUTE s2_rescan('((NaN,0),(NaN,0))');
EXECUTE s2_rescan(NULL);
EXECUTE s2_rescan('((0,0),(0,0))');
DEALLOCATE s2_rescan;
