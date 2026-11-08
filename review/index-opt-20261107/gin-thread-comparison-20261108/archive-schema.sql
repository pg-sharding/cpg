BEGIN READ ONLY;
SET LOCAL statement_timeout='30s';
SELECT table_name,column_name,data_type FROM information_schema.columns WHERE table_schema='public' AND table_name IN ('messages','attachments','topics','commits','message_commits') ORDER BY table_name,ordinal_position LIMIT 160;
COMMIT;
