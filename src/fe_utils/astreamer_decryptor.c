/*-------------------------------------------------------------------------
 *
 * astreamer_decryptor.c
 *	  Frontend astreamer that decrypts data using XOR.
 *
 * Portions Copyright (c) 2026, PostgreSQL Global Development Group
 *
 * IDENTIFICATION
 *	  src/fe_utils/astreamer_decryptor.c
 *
 *-------------------------------------------------------------------------
 */
#include "postgres_fe.h"
#include "common/logging.h"
#include "common/string.h"
#include "fe_utils/astreamer.h"

typedef struct astreamer_decryptor
{
	astreamer	base;
	char	   *key;
	size_t		key_len;
} astreamer_decryptor;

static void astreamer_decryptor_content(astreamer *streamer,
										astreamer_member *member,
										const char *data, int len,
										astreamer_archive_context context);
static void astreamer_decryptor_finalize(astreamer *streamer);
static void astreamer_decryptor_free(astreamer *streamer);

static const astreamer_ops astreamer_decryptor_ops = {
	.content = astreamer_decryptor_content,
	.finalize = astreamer_decryptor_finalize,
	.free = astreamer_decryptor_free
};

/*
 * Create a new astreamer that decrypts data using XOR with the given key.
 * The key is provided as a hex string.  XOR is symmetric, so this is used
 * for both encryption and decryption.
 */
astreamer *
astreamer_decryptor_new(astreamer *next, const char *key_hex)
{
	astreamer_decryptor *streamer;
	size_t		hexlen;
	size_t		klen;
	char	   *key;
	size_t		i;
	static const int8 hexlookup[256] = {
		-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
		-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
		-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
		 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,-1,-1,-1,-1,-1,-1,
		-1,10,11,12,13,14,15,-1,-1,-1,-1,-1,-1,-1,-1,-1,
		-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
		-1,10,11,12,13,14,15,-1,-1,-1,-1,-1,-1,-1,-1,-1,
		-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
		-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
		-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
		-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
		-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
		-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
		-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
		-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
		-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
	};

	Assert(next != NULL);

	hexlen = strlen(key_hex);
	klen = hexlen / 2;
	key = pg_malloc(klen);

	for (i = 0; i < klen; i++)
	{
		int			hi = hexlookup[(unsigned char) key_hex[i * 2]];
		int			lo = hexlookup[(unsigned char) key_hex[i * 2 + 1]];

		if (hi < 0 || lo < 0)
			pg_fatal("invalid hex key for decryption");
		key[i] = (hi << 4) | lo;
	}

	streamer = palloc0_object(astreamer_decryptor);
	*((const astreamer_ops **) &streamer->base.bbs_ops) =
		&astreamer_decryptor_ops;
	streamer->base.bbs_next = next;
	initStringInfo(&streamer->base.bbs_buffer);
	streamer->key = key;
	streamer->key_len = klen;

	return &streamer->base;
}

static void
astreamer_decryptor_content(astreamer *streamer, astreamer_member *member,
							const char *data, int len,
							astreamer_archive_context context)
{
	astreamer_decryptor *mystreamer = (astreamer_decryptor *) streamer;
	char	   *buf;
	int			i;

	/*
	 * Make a writable copy and XOR-decrypt in place.  XOR is symmetric,
	 * so decryption is the same operation as encryption.
	 */
	buf = pg_malloc(len);
	memcpy(buf, data, len);
	for (i = 0; i < len; i++)
		buf[i] ^= mystreamer->key[i % mystreamer->key_len];

	astreamer_content(mystreamer->base.bbs_next, member, buf, len, context);
	pg_free(buf);
}

static void
astreamer_decryptor_finalize(astreamer *streamer)
{
	astreamer_decryptor *mystreamer = (astreamer_decryptor *) streamer;
	astreamer_finalize(mystreamer->base.bbs_next);
}

static void
astreamer_decryptor_free(astreamer *streamer)
{
	astreamer_decryptor *mystreamer = (astreamer_decryptor *) streamer;

	astreamer_free(mystreamer->base.bbs_next);
	pg_free(mystreamer->key);
	pfree(mystreamer->base.bbs_buffer.data);
	pfree(streamer);
}
