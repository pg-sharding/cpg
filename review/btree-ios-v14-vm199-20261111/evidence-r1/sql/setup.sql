\set ON_ERROR_STOP on
SET client_min_messages=warning;
CREATE EXTENSION amcheck; CREATE EXTENSION pageinspect; CREATE EXTENSION pg_visibility;
CREATE TABLE f2_p2 AS SELECT (k+0)::int AS a1,(k+1)::int AS a2 FROM(SELECT g%500000 AS k,g FROM generate_series(1,1000000)g)s;
CREATE INDEX f2_p2_idx ON f2_p2(a1,a2);
VACUUM(FREEZE,ANALYZE)f2_p2;
CREATE TABLE f3_p2 AS SELECT (k+0)::int AS a1,(k+1)::int AS a2,(k+2)::int AS a3 FROM(SELECT g%500000 AS k,g FROM generate_series(1,1000000)g)s;
CREATE INDEX f3_p2_idx ON f3_p2(a1,a2,a3);
VACUUM(FREEZE,ANALYZE)f3_p2;
CREATE TABLE f4_p2 AS SELECT (k+0)::int AS a1,(k+1)::int AS a2,(k+2)::int AS a3,(k+3)::int AS a4 FROM(SELECT g%500000 AS k,g FROM generate_series(1,1000000)g)s;
CREATE INDEX f4_p2_idx ON f4_p2(a1,a2,a3,a4);
VACUUM(FREEZE,ANALYZE)f4_p2;
CREATE TABLE f4_long AS SELECT (k+0)::int AS a1,(k+1)::int AS a2,(k+2)::int AS a3,(k+3)::int AS a4 FROM(SELECT g%10000 AS k,g FROM generate_series(1,1000000)g)s;
CREATE INDEX f4_long_idx ON f4_long(a1,a2,a3,a4);
VACUUM(FREEZE,ANALYZE)f4_long;
CREATE TABLE heap_f4 AS SELECT (k+0)::int AS a1,(k+1)::int AS a2,(k+2)::int AS a3,(k+3)::int AS a4 FROM(SELECT g%10000 AS k,g FROM generate_series(1,1000000)g)s;
CREATE INDEX heap_f4_idx ON heap_f4(a1,a2,a3,a4);
VACUUM(FREEZE,ANALYZE)heap_f4;
CREATE TABLE w8_long AS SELECT (lpad(k::text,7,'0')||repeat(chr(97),20+k%16))COLLATE"C" AS a1,(lpad(k::text,7,'0')||repeat(chr(98),20+k%16))COLLATE"C" AS a2,(lpad(k::text,7,'0')||repeat(chr(99),20+k%16))COLLATE"C" AS a3,(lpad(k::text,7,'0')||repeat(chr(100),20+k%16))COLLATE"C" AS a4,(lpad(k::text,7,'0')||repeat(chr(101),20+k%16))COLLATE"C" AS a5,(lpad(k::text,7,'0')||repeat(chr(102),20+k%16))COLLATE"C" AS a6,(lpad(k::text,7,'0')||repeat(chr(103),20+k%16))COLLATE"C" AS a7,(lpad(k::text,7,'0')||repeat(chr(104),20+k%16))COLLATE"C" AS a8 FROM(SELECT g%10000 AS k,g FROM generate_series(1,1000000)g)s;
CREATE INDEX w8_long_idx ON w8_long(a1,a2,a3,a4,a5,a6,a7,a8);
VACUUM(FREEZE,ANALYZE)w8_long;
CREATE TABLE f32_long AS SELECT (k+0)::int AS a1,(k+1)::int AS a2,(k+2)::int AS a3,(k+3)::int AS a4,(k+4)::int AS a5,(k+5)::int AS a6,(k+6)::int AS a7,(k+7)::int AS a8,(k+8)::int AS a9,(k+9)::int AS a10,(k+10)::int AS a11,(k+11)::int AS a12,(k+12)::int AS a13,(k+13)::int AS a14,(k+14)::int AS a15,(k+15)::int AS a16,(k+16)::int AS a17,(k+17)::int AS a18,(k+18)::int AS a19,(k+19)::int AS a20,(k+20)::int AS a21,(k+21)::int AS a22,(k+22)::int AS a23,(k+23)::int AS a24,(k+24)::int AS a25,(k+25)::int AS a26,(k+26)::int AS a27,(k+27)::int AS a28,(k+28)::int AS a29,(k+29)::int AS a30,(k+30)::int AS a31,(k+31)::int AS a32 FROM(SELECT g%2000 AS k,g FROM generate_series(1,200000)g)s;
CREATE INDEX f32_long_idx ON f32_long(a1,a2,a3,a4,a5,a6,a7,a8,a9,a10,a11,a12,a13,a14,a15,a16,a17,a18,a19,a20,a21,a22,a23,a24,a25,a26,a27,a28,a29,a30,a31,a32);
VACUUM(FREEZE,ANALYZE)f32_long;
CREATE TABLE w32_long AS SELECT (lpad(k::text,7,'0')||repeat(chr(97),4+k%8))COLLATE"C" AS a1,(lpad(k::text,7,'0')||repeat(chr(98),4+k%8))COLLATE"C" AS a2,(lpad(k::text,7,'0')||repeat(chr(99),4+k%8))COLLATE"C" AS a3,(lpad(k::text,7,'0')||repeat(chr(100),4+k%8))COLLATE"C" AS a4,(lpad(k::text,7,'0')||repeat(chr(101),4+k%8))COLLATE"C" AS a5,(lpad(k::text,7,'0')||repeat(chr(102),4+k%8))COLLATE"C" AS a6,(lpad(k::text,7,'0')||repeat(chr(103),4+k%8))COLLATE"C" AS a7,(lpad(k::text,7,'0')||repeat(chr(104),4+k%8))COLLATE"C" AS a8,(lpad(k::text,7,'0')||repeat(chr(105),4+k%8))COLLATE"C" AS a9,(lpad(k::text,7,'0')||repeat(chr(106),4+k%8))COLLATE"C" AS a10,(lpad(k::text,7,'0')||repeat(chr(107),4+k%8))COLLATE"C" AS a11,(lpad(k::text,7,'0')||repeat(chr(108),4+k%8))COLLATE"C" AS a12,(lpad(k::text,7,'0')||repeat(chr(109),4+k%8))COLLATE"C" AS a13,(lpad(k::text,7,'0')||repeat(chr(110),4+k%8))COLLATE"C" AS a14,(lpad(k::text,7,'0')||repeat(chr(111),4+k%8))COLLATE"C" AS a15,(lpad(k::text,7,'0')||repeat(chr(112),4+k%8))COLLATE"C" AS a16,(lpad(k::text,7,'0')||repeat(chr(113),4+k%8))COLLATE"C" AS a17,(lpad(k::text,7,'0')||repeat(chr(114),4+k%8))COLLATE"C" AS a18,(lpad(k::text,7,'0')||repeat(chr(115),4+k%8))COLLATE"C" AS a19,(lpad(k::text,7,'0')||repeat(chr(116),4+k%8))COLLATE"C" AS a20,(lpad(k::text,7,'0')||repeat(chr(117),4+k%8))COLLATE"C" AS a21,(lpad(k::text,7,'0')||repeat(chr(118),4+k%8))COLLATE"C" AS a22,(lpad(k::text,7,'0')||repeat(chr(119),4+k%8))COLLATE"C" AS a23,(lpad(k::text,7,'0')||repeat(chr(120),4+k%8))COLLATE"C" AS a24,(lpad(k::text,7,'0')||repeat(chr(121),4+k%8))COLLATE"C" AS a25,(lpad(k::text,7,'0')||repeat(chr(122),4+k%8))COLLATE"C" AS a26,(lpad(k::text,7,'0')||repeat(chr(97),4+k%8))COLLATE"C" AS a27,(lpad(k::text,7,'0')||repeat(chr(98),4+k%8))COLLATE"C" AS a28,(lpad(k::text,7,'0')||repeat(chr(99),4+k%8))COLLATE"C" AS a29,(lpad(k::text,7,'0')||repeat(chr(100),4+k%8))COLLATE"C" AS a30,(lpad(k::text,7,'0')||repeat(chr(101),4+k%8))COLLATE"C" AS a31,(lpad(k::text,7,'0')||repeat(chr(102),4+k%8))COLLATE"C" AS a32 FROM(SELECT g%2000 AS k,g FROM generate_series(1,200000)g)s;
CREATE INDEX w32_long_idx ON w32_long(a1,a2,a3,a4,a5,a6,a7,a8,a9,a10,a11,a12,a13,a14,a15,a16,a17,a18,a19,a20,a21,a22,a23,a24,a25,a26,a27,a28,a29,a30,a31,a32);
VACUUM(FREEZE,ANALYZE)w32_long;
CREATE TABLE one_bigint_long AS SELECT k::bigint AS a1 FROM(SELECT g%10000 AS k,g FROM generate_series(1,1000000)g)s;
CREATE INDEX one_bigint_long_idx ON one_bigint_long(a1);
VACUUM(FREEZE,ANALYZE)one_bigint_long;
CREATE TABLE one_bigint_singleton AS SELECT k::bigint AS a1 FROM(SELECT g%1000000 AS k,g FROM generate_series(1,1000000)g)s;
CREATE INDEX one_bigint_singleton_idx ON one_bigint_singleton(a1);
VACUUM(FREEZE,ANALYZE)one_bigint_singleton;
CREATE TABLE incl AS SELECT k::int AS a1,(k+7)::int AS a2,(g%139)::int AS a3 FROM(SELECT g%10000 AS k,g FROM generate_series(1,1000000)g)s;
CREATE INDEX incl_idx ON incl(a1) INCLUDE(a2);
VACUUM(FREEZE,ANALYZE)incl;
CREATE TABLE seq_control AS SELECT g::int a FROM generate_series(1,1000000)g;
VACUUM(FREEZE,ANALYZE)seq_control;
CHECKPOINT;

\set ON_ERROR_STOP on
CREATE TABLE mixed2 AS SELECT g AS a1,g*3 AS a2 FROM generate_series(1,500000)g
UNION ALL SELECT g,g*3 FROM generate_series(1,500000)g WHERE g%64=0;
CREATE INDEX mixed2_idx ON mixed2(a1,a2);
VACUUM(FREEZE,ANALYZE)mixed2;
CREATE TABLE mixed64 AS SELECT g AS a1,g*3 AS a2 FROM generate_series(1,500000)g
UNION ALL SELECT g,g*3 FROM generate_series(1,500000)g CROSS JOIN generate_series(1,63)d WHERE g%128=0;
CREATE INDEX mixed64_idx ON mixed64(a1,a2);
VACUUM(FREEZE,ANALYZE)mixed64;
CHECKPOINT;
