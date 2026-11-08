BEGIN READ ONLY;
SET LOCAL statement_timeout='30s';
SELECT id,topic_id,created_at,subject,message_id FROM messages WHERE reply_to_id IN (SELECT id FROM messages WHERE topic_id=53025) AND topic_id<>53025 ORDER BY created_at DESC LIMIT 60;
SELECT id,title,last_message_at,message_count,merged_into_topic_id FROM topics WHERE title ILIKE '%pg_trgm%' AND (title ILIKE '%collat%' OR title ILIKE '%sort%' OR title ILIKE '%dedup%') ORDER BY last_message_at DESC LIMIT 40;
SELECT id,topic_id,created_at,subject,message_id FROM messages WHERE body_tsv @@ (plainto_tsquery('simple','ginExtractEntries') || plainto_tsquery('english','ginExtractEntries')) AND topic_id<>53025 ORDER BY created_at DESC LIMIT 25;
COMMIT;
