CREATE EXTENSION sa_mon;

-- Nothing was reported by a primary on a non-standby server.
SELECT mdb_get_sa_info() IS NULL AS no_report;

DROP EXTENSION sa_mon;
