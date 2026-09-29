/* contrib/pg_backend_msg/pg_backend_msg--1.0.sql */

-- complain if script is sourced in psql, rather than via CREATE EXTENSION
\echo Use "CREATE EXTENSION pg_backend_msg" to load this file. \quit

/*
 * Overloads of pg_cancel_backend() and pg_terminate_backend() accepting an
 * extra message, which the target backend includes in the error it reports
 * to its client.
 *
 * The underlying C functions are the same built-in ones (no changes to the
 * system catalogs are involved); they simply read the message argument
 * when the caller passes it.
 *
 * Note: the message argument is required rather than having a DEFAULT,
 * because a defaulted message would make calls with the old, shorter
 * argument lists ambiguous between the built-in functions and these
 * overloads.
 */
CREATE FUNCTION pg_catalog.pg_cancel_backend(pid int4, message text)
RETURNS bool
STRICT VOLATILE PARALLEL SAFE
LANGUAGE internal AS 'pg_cancel_backend';

CREATE FUNCTION pg_catalog.pg_terminate_backend(pid int4, timeout int8, message text)
RETURNS bool
STRICT VOLATILE PARALLEL SAFE
LANGUAGE internal AS 'pg_terminate_backend';
