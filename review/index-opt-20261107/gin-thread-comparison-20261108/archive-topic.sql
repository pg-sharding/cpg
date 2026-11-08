BEGIN READ ONLY;
SET LOCAL statement_timeout='30s';
SELECT id,topic_id,created_at,subject,message_id FROM messages WHERE message_id='5d366878-2007-4d31-861e-19294b7a583b@gmail.com' LIMIT 5;
SELECT id,title,created_at,last_message_at,message_count,merged_into_topic_id FROM topics WHERE title ILIKE '%Reduce build times of pg_trgm GIN%' ORDER BY id LIMIT 30;
COMMIT;
