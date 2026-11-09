/* Fixture-only hash functions. No search implementation or timing wrapper. */
#include "postgres.h"
#include "fmgr.h"
PG_MODULE_MAGIC;
PG_FUNCTION_INFO_V1(h1_identity_hash);
Datum h1_identity_hash(PG_FUNCTION_ARGS)
{
	PG_RETURN_INT32((uint32) PG_GETARG_INT64(0));
}
PG_FUNCTION_INFO_V1(h1_zero_hash);
Datum h1_zero_hash(PG_FUNCTION_ARGS)
{
	PG_RETURN_INT32(0);
}
PG_FUNCTION_INFO_V1(h1_max_hash);
Datum h1_max_hash(PG_FUNCTION_ARGS)
{
	PG_RETURN_INT32(-1);
}
