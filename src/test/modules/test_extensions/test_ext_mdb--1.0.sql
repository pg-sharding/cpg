/* src/test/modules/test_extensions/test_ext9--1.0.sql */

-- complain if script is sourced in psql, rather than via CREATE EXTENSION
\echo Use "CREATE EXTENSION test_ext9" to load this file. \quit

-- create some random data type
create domain posint as int check (value > 0);

-- use it in regular and temporary tables and functions

create table ext9_table1 (f1 posint);

create function ext9_even (posint) returns bool as
  'select ($1 % 2) = 0' language sql;

