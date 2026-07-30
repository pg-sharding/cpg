-- Test pushdown of quals into subqueries.

create table smalltab (i int4, j int4);
create table bigtab (i int4, j int4);

insert into smalltab values (1, 1), (5, 50), (100000, 100000);
insert into bigtab select g,g from generate_series(1, 100000) g;

analyze smalltab, bigtab;

create index bigtab_i on bigtab (i);

-- Keep the plans in this test stable and easy to read.
set enable_memoize = off;
set max_parallel_workers_per_gather = 0;

-- Push down restriction quals.
explain (costs off)
select * from smalltab,
(
  select bigtab.i, avg(bigtab.j)
  from bigtab
  group by bigtab.i
) as subq(i, avg)
where smalltab.i = subq.i and smalltab.i = 123;

-- Push down join quals.
explain (costs off)
select * from smalltab,
(
  select bigtab.i, avg(bigtab.j)
  from bigtab
  group by bigtab.i
) as subq(i, avg)
where smalltab.i = subq.i;

-- Subquery is LATERAL, and already references the other relation. The join
-- qual is always pushed down in that case, as the plan is "parameterized"
-- in respect to the other relation even if it was not pushed down.
explain (costs off)
select * from smalltab,
lateral (
  select bigtab.i, avg(bigtab.j)
  from bigtab
  where bigtab.j = smalltab.j
  group by bigtab.i
) as subq(i, avg)
where smalltab.i < subq.i;

-- Multiple join clauses constructed from equivalence classes
explain (costs off)
select * from smalltab,
lateral (
  select bigtab.i, bigtab.j, avg(bigtab.j)
  from bigtab
  where bigtab.j/2 = smalltab.j / 2
  group by bigtab.i, bigtab.j
) as subq(i, j, avg)
where smalltab.i = subq.i and smalltab.j = subq.j;

-- The enable_join_predicate_pushdown GUC turns the optimization on and off.
-- With it disabled, the join qual is not pushed into the LATERAL subquery,
-- so it must be re-checked above the SubqueryScan (as a Filter / join cond).
set enable_join_predicate_pushdown = off;
explain (costs off)
select * from smalltab,
lateral (
  select bigtab.i, avg(bigtab.j)
  from bigtab
  where bigtab.j = smalltab.j
  group by bigtab.i
) as subq(i, avg)
where smalltab.i < subq.i;
reset enable_join_predicate_pushdown;

-- The GUC only gates join-qual pushdown; plain restriction quals are still
-- pushed down even when it is disabled.
set enable_join_predicate_pushdown = off;
explain (costs off)
select * from smalltab,
(
  select bigtab.i, avg(bigtab.j)
  from bigtab
  group by bigtab.i
) as subq(i, avg)
where smalltab.i = subq.i and smalltab.i = 123;
reset enable_join_predicate_pushdown;

-- Results must be identical whether or not the optimization is enabled.
-- First, show the actual rows (with the optimization on).
set enable_join_predicate_pushdown = on;
select smalltab.i, smalltab.j, subq.i, subq.avg from smalltab,
lateral (
  select bigtab.i, avg(bigtab.j)
  from bigtab
  where bigtab.j = smalltab.j
  group by bigtab.i
) as subq(i, avg)
where smalltab.i < subq.i
order by 1, 2, 3;

-- Now assert that turning the optimization off yields exactly the same rows.
-- SET can't appear inside a subquery, so materialize both variants into temp
-- tables and compare them with a symmetric EXCEPT ALL.
set enable_join_predicate_pushdown = on;
create temp table res_on as
select smalltab.i as si, smalltab.j as sj, subq.i as qi, subq.avg as qavg
from smalltab,
lateral (
  select bigtab.i, avg(bigtab.j)
  from bigtab
  where bigtab.j = smalltab.j
  group by bigtab.i
) as subq(i, avg)
where smalltab.i < subq.i;

set enable_join_predicate_pushdown = off;
create temp table res_off as
select smalltab.i as si, smalltab.j as sj, subq.i as qi, subq.avg as qavg
from smalltab,
lateral (
  select bigtab.i, avg(bigtab.j)
  from bigtab
  where bigtab.j = smalltab.j
  group by bigtab.i
) as subq(i, avg)
where smalltab.i < subq.i;
reset enable_join_predicate_pushdown;

-- Both directions of the difference must be empty if the results agree.
select 'on minus off' as diff, * from (table res_on except all table res_off) d
union all
select 'off minus on', * from (table res_off except all table res_on) d;

drop table res_on, res_off;
