/*
 * contrib/intarray/_int_tool.c
 */
#include "postgres.h"

#include <limits.h>

#include "_int.h"
#include "catalog/pg_type.h"
#include "common/int.h"
#include "lib/qunique.h"

/* arguments are assumed sorted & unique-ified */
bool
inner_int_contains(ArrayType *a, ArrayType *b)
{
	int			na,
				nb;
	int			i,
				j,
				n;
	int		   *da,
			   *db;

	na = ARRNELEMS(a);
	nb = ARRNELEMS(b);
	da = ARRPTR(a);
	db = ARRPTR(b);

	i = j = n = 0;
	while (i < na && j < nb)
	{
		if (da[i] < db[j])
			i++;
		else if (da[i] == db[j])
		{
			n++;
			i++;
			j++;
		}
		else
			break;				/* db[j] is not in da */
	}

	return (n == nb);
}

/* arguments are assumed sorted */
bool
inner_int_overlap(ArrayType *a, ArrayType *b)
{
	int			na,
				nb;
	int			i,
				j;
	int		   *da,
			   *db;

	na = ARRNELEMS(a);
	nb = ARRNELEMS(b);
	da = ARRPTR(a);
	db = ARRPTR(b);

	i = j = 0;
	while (i < na && j < nb)
	{
		if (da[i] < db[j])
			i++;
		else if (da[i] == db[j])
			return true;
		else
			j++;
	}

	return false;
}

ArrayType *
inner_int_union(ArrayType *a, ArrayType *b)
{
	ArrayType  *r = NULL;

	CHECKARRVALID(a);
	CHECKARRVALID(b);

	if (ARRISEMPTY(a) && ARRISEMPTY(b))
		return new_intArrayType(0);
	if (ARRISEMPTY(a))
		r = copy_intArrayType(b);
	if (ARRISEMPTY(b))
		r = copy_intArrayType(a);

	if (!r)
	{
		int			na = ARRNELEMS(a),
					nb = ARRNELEMS(b);
		int		   *da = ARRPTR(a),
				   *db = ARRPTR(b);
		int			i,
					j,
				   *dr;

		r = new_intArrayType(na + nb);
		dr = ARRPTR(r);

		/* union */
		i = j = 0;
		while (i < na && j < nb)
		{
			if (da[i] == db[j])
			{
				*dr++ = da[i++];
				j++;
			}
			else if (da[i] < db[j])
				*dr++ = da[i++];
			else
				*dr++ = db[j++];
		}

		while (i < na)
			*dr++ = da[i++];
		while (j < nb)
			*dr++ = db[j++];

		r = resize_intArrayType(r, dr - ARRPTR(r));
	}

	if (ARRNELEMS(r) > 1)
		r = _int_unique(r);

	return r;
}

ArrayType *
inner_int_inter(ArrayType *a, ArrayType *b)
{
	ArrayType  *r;
	int			na,
				nb;
	int		   *da,
			   *db,
			   *dr;
	int			i,
				j,
				k;

	if (ARRISEMPTY(a) || ARRISEMPTY(b))
		return new_intArrayType(0);

	na = ARRNELEMS(a);
	nb = ARRNELEMS(b);
	da = ARRPTR(a);
	db = ARRPTR(b);
	r = new_intArrayType(Min(na, nb));
	dr = ARRPTR(r);

	i = j = k = 0;
	while (i < na && j < nb)
	{
		if (da[i] < db[j])
			i++;
		else if (da[i] == db[j])
		{
			if (k == 0 || dr[k - 1] != db[j])
				dr[k++] = db[j];
			i++;
			j++;
		}
		else
			j++;
	}

	if (k == 0)
	{
		pfree(r);
		return new_intArrayType(0);
	}
	else
		return resize_intArrayType(r, k);
}

void
rt__int_size(ArrayType *a, float *size)
{
	*size = (float) ARRNELEMS(a);
}

/* comparison function for isort() and _int_unique() */
static inline int
isort_cmp(const void *a, const void *b, void *arg)
{
	int32		aval = *((const int32 *) a);
	int32		bval = *((const int32 *) b);

	if (*((bool *) arg))
	{
		/* compare for ascending order */
		if (aval < bval)
			return -1;
		if (aval > bval)
			return 1;
	}
	else
	{
		if (aval > bval)
			return -1;
		if (aval < bval)
			return 1;
	}
	return 0;
}

#define ST_SORT intarray_qsort
#define ST_ELEMENT_TYPE int32
#define ST_COMPARE(a, b, ascending) isort_cmp(a, b, ascending)
#define ST_COMPARE_ARG_TYPE void
#define ST_SCOPE static
#define ST_DEFINE
#define ST_DECLARE
#include "lib/sort_template.h"

/* Keep duplicates for isort callers; PREPAREARR requests compaction. */
static size_t
intarray_sort(int32 *array, size_t n, bool ascending, bool unique)
{
	uint32		freqs[4][256];
	uint32		first,
				different = 0;
	uint32		order_mask = ascending ? 0x80000000U : 0x7fffffffU;
	int32	   *buffer,
			   *from = array,
			   *to;

	if (n <= 256)
	{
		intarray_qsort(array, n, &ascending);
		return unique ? qunique_arg(array, n, sizeof(int32), isort_cmp,
									   &ascending) : n;
	}

	/* Preserve the existing comparison sort's fast path for ordered input. */
	{
		size_t		j;

		for (j = 1; j < n; j++)
			if (ascending ? array[j - 1] > array[j] : array[j - 1] < array[j])
				break;
		if (j == n)
			return unique ? qunique_arg(array, n, sizeof(int32), isort_cmp,
										   &ascending) : n;
	}

	memset(freqs, 0, sizeof(freqs));
	first = (uint32) array[0];
	for (size_t j = 0; j < n; j++)
	{
		uint32		key = (uint32) array[j];

		different |= key ^ first;
		/* Array allocations cannot contain UINT32_MAX int4 elements. */
		freqs[0][key & 255]++;
		freqs[1][(key >> 8) & 255]++;
		freqs[2][(key >> 16) & 255]++;
		freqs[3][key >> 24]++;
	}
	if (different == 0)
		return unique ? 1 : n;

	buffer = palloc_array(int32, n);
	to = buffer;
	for (unsigned int byte = 0; byte < 4; byte++)
	{
		int32	   *starts[256],
				   *next = to,
				   *swap;
		unsigned int shift = byte * 8;
		unsigned int mask = (order_mask >> shift) & 255;

		if ((different & ((uint32) 255 << shift)) == 0)
			continue;
		for (unsigned int k = 0; k < 256; k++)
		{
			starts[k ^ mask] = next;
			next += freqs[byte][k ^ mask];
		}
		for (size_t j = 0; j < n; j++)
			*starts[((uint32) from[j] >> shift) & 255]++ = from[j];
		swap = from;
		from = to;
		to = swap;
	}

	if (unique)
	{
		size_t		count = 1;

		array[0] = from[0];
		for (size_t j = 1; j < n; j++)
			if (from[j] != array[count - 1])
				array[count++] = from[j];
		n = count;
	}
	else if (from != array)
		memcpy(array, from, n * sizeof(int32));
	pfree(buffer);
	return n;
}

void
isort(int32 *a, size_t len, void *arg)
{
	(void) intarray_sort(a, len, *((bool *) arg), false);
}

ArrayType *
intarray_sort_and_unique(ArrayType *a)
{
	return resize_intArrayType(a,
							   intarray_sort(ARRPTR(a), ARRNELEMS(a), true, true));
}

/* Create a new int array with room for "num" elements */
ArrayType *
new_intArrayType(int num)
{
	ArrayType  *r;
	int			nbytes;

	/* if no elements, return a zero-dimensional array */
	if (num <= 0)
	{
		Assert(num == 0);
		r = construct_empty_array(INT4OID);
		return r;
	}

	nbytes = ARR_OVERHEAD_NONULLS(1) + sizeof(int) * num;

	r = (ArrayType *) palloc0(nbytes);

	SET_VARSIZE(r, nbytes);
	ARR_NDIM(r) = 1;
	r->dataoffset = 0;			/* marker for no null bitmap */
	ARR_ELEMTYPE(r) = INT4OID;
	ARR_DIMS(r)[0] = num;
	ARR_LBOUND(r)[0] = 1;

	return r;
}

ArrayType *
resize_intArrayType(ArrayType *a, int num)
{
	int			nbytes;
	int			i;

	/* if no elements, return a zero-dimensional array */
	if (num <= 0)
	{
		Assert(num == 0);
		a = construct_empty_array(INT4OID);
		return a;
	}

	if (num == ARRNELEMS(a))
		return a;

	nbytes = ARR_DATA_OFFSET(a) + sizeof(int) * num;

	a = (ArrayType *) repalloc(a, nbytes);

	SET_VARSIZE(a, nbytes);
	/* usually the array should be 1-D already, but just in case ... */
	for (i = 0; i < ARR_NDIM(a); i++)
	{
		ARR_DIMS(a)[i] = num;
		num = 1;
	}
	return a;
}

ArrayType *
copy_intArrayType(ArrayType *a)
{
	ArrayType  *r;
	int			n = ARRNELEMS(a);

	r = new_intArrayType(n);
	memcpy(ARRPTR(r), ARRPTR(a), n * sizeof(int32));
	return r;
}

/* num for compressed key */
int
internal_size(int *a, int len)
{
	int			i;
	int64		size = 0;

	for (i = 0; i < len; i += 2)
	{
		if (!i || a[i] != a[i - 1]) /* do not count repeated range */
			size += (int64) (a[i + 1]) - (int64) (a[i]) + 1;
	}

	if (size > (int64) INT_MAX || size < (int64) INT_MIN)
		return -1;				/* overflow */
	return (int) size;
}

/* unique-ify elements of r in-place ... r must be sorted already */
ArrayType *
_int_unique(ArrayType *r)
{
	int			num = ARRNELEMS(r);
	bool		ascending = true;

	num = qunique_arg(ARRPTR(r), num, sizeof(int), isort_cmp,
					  &ascending);

	return resize_intArrayType(r, num);
}

void
gensign(BITVECP sign, int *a, int len, int siglen)
{
	int			i;

	/* we assume that the sign vector is previously zeroed */
	for (i = 0; i < len; i++)
	{
		HASH(sign, *a, siglen);
		a++;
	}
}

int32
intarray_match_first(ArrayType *a, int32 elem)
{
	int32	   *aa,
				c,
				i;

	CHECKARRVALID(a);
	c = ARRNELEMS(a);
	aa = ARRPTR(a);
	for (i = 0; i < c; i++)
		if (aa[i] == elem)
			return (i + 1);
	return 0;
}

ArrayType *
intarray_add_elem(ArrayType *a, int32 elem)
{
	ArrayType  *result;
	int32	   *r;
	int32		c;

	CHECKARRVALID(a);
	c = ARRNELEMS(a);
	result = new_intArrayType(c + 1);
	r = ARRPTR(result);
	if (c > 0)
		memcpy(r, ARRPTR(a), c * sizeof(int32));
	r[c] = elem;
	return result;
}

ArrayType *
intarray_concat_arrays(ArrayType *a, ArrayType *b)
{
	ArrayType  *result;
	int32		ac = ARRNELEMS(a);
	int32		bc = ARRNELEMS(b);

	CHECKARRVALID(a);
	CHECKARRVALID(b);
	result = new_intArrayType(ac + bc);
	if (ac)
		memcpy(ARRPTR(result), ARRPTR(a), ac * sizeof(int32));
	if (bc)
		memcpy(ARRPTR(result) + ac, ARRPTR(b), bc * sizeof(int32));
	return result;
}

ArrayType *
int_to_intset(int32 elem)
{
	ArrayType  *result;
	int32	   *aa;

	result = new_intArrayType(1);
	aa = ARRPTR(result);
	aa[0] = elem;
	return result;
}
