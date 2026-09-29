CREATE EXTENSION pg_backend_msg;

-- old signatures keep working
SELECT pg_cancel_backend(999999999);
SELECT pg_terminate_backend(999999999, 0);

-- same names, with a message
SELECT pg_cancel_backend(999999999, 'no such backend');
SELECT pg_terminate_backend(999999999, 0, 'no such backend');

-- named arguments
SELECT pg_cancel_backend(pid => 999999999, message => 'no such backend');
SELECT pg_terminate_backend(pid => 999999999, timeout => 0, message => 'no such backend');

-- NULL message is not passed to the function (STRICT)
SELECT pg_cancel_backend(999999999, NULL);
