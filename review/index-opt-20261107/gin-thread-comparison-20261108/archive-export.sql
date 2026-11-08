BEGIN READ ONLY;
SET LOCAL statement_timeout='30s';
SELECT json_build_object('kind','message','id',id,'topic_id',topic_id,'created_at',created_at,'subject',subject,'message_id',message_id,'reply_to_id',reply_to_id,'reply_to_message_id',reply_to_message_id,'body',body) FROM messages WHERE topic_id=53025 ORDER BY created_at,id LIMIT 150;
SELECT json_build_object('kind','attachment','id',a.id,'message_id',a.message_id,'file_name',a.file_name,'content_type',a.content_type,'created_at',a.created_at,'body',a.body) FROM attachments a JOIN messages m ON m.id=a.message_id WHERE m.topic_id=53025 ORDER BY m.created_at,a.id LIMIT 250;
COMMIT;
