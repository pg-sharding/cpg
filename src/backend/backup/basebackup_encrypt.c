/*-------------------------------------------------------------------------
 *
 * basebackup_encrypt.c
 *	  Basebackup sink implementing encryption of backup data.
 *
 * Portions Copyright (c) 2026, PostgreSQL Global Development Group
 *
 * IDENTIFICATION
 *	  src/backend/backup/basebackup_encrypt.c
 *
 *-------------------------------------------------------------------------
 */
#include "postgres.h"

#include "backup/basebackup_sink.h"
#include "encrypt/encrypt_module.h"

typedef struct bbsink_encrypt
{
	/* Common information for all types of sink. */
	bbsink		base;

	/* Number of bytes staged in output buffer. */
	size_t		bytes_written;
} bbsink_encrypt;

static void bbsink_encrypt_begin_backup(bbsink *sink);
static void bbsink_encrypt_begin_archive(bbsink *sink, const char *archive_name);
static void bbsink_encrypt_archive_contents(bbsink *sink, size_t len);
static void bbsink_encrypt_manifest_contents(bbsink *sink, size_t len);
static void bbsink_encrypt_end_archive(bbsink *sink);
static void bbsink_encrypt_cleanup(bbsink *sink);

static const bbsink_ops bbsink_encrypt_ops = {
	.begin_backup = bbsink_encrypt_begin_backup,
	.begin_archive = bbsink_encrypt_begin_archive,
	.archive_contents = bbsink_encrypt_archive_contents,
	.end_archive = bbsink_encrypt_end_archive,
	.begin_manifest = bbsink_forward_begin_manifest,
	.manifest_contents = bbsink_encrypt_manifest_contents,
	.end_manifest = bbsink_forward_end_manifest,
	.end_backup = bbsink_forward_end_backup,
	.cleanup = bbsink_encrypt_cleanup
};

/*
 * Create a new basebackup sink that encrypts backup data.
 */
bbsink *
bbsink_encrypt_new(bbsink *next)
{
	bbsink_encrypt *sink;

	Assert(next != NULL);

	sink = palloc0_object(bbsink_encrypt);
	*((const bbsink_ops **) &sink->base.bbs_ops) = &bbsink_encrypt_ops;
	sink->base.bbs_next = next;

	return &sink->base;
}

/*
 * Begin backup.  We need our own buffer because the encrypted data may
 * differ in length from the input (in general; for XOR it's the same, but
 * we follow the transform-sink pattern for generality).
 */
static void
bbsink_encrypt_begin_backup(bbsink *sink)
{
	sink->bbs_buffer = palloc(sink->bbs_buffer_length);
	bbsink_begin_backup(sink->bbs_next, sink->bbs_state,
						sink->bbs_buffer_length);
}

/*
 * Prepare to encrypt the next archive.
 */
static void
bbsink_encrypt_begin_archive(bbsink *sink, const char *archive_name)
{
	Assert(sink->bbs_next != NULL);
	bbsink_begin_archive(sink->bbs_next, archive_name);
}

/*
 * Encrypt the input data from our buffer into the next sink's buffer and
 * forward it.  XOR encryption preserves length, so the output size equals
 * the input size.
 */
static void
bbsink_encrypt_archive_contents(bbsink *sink, size_t len)
{
	const EncryptModuleCallbacks *cb = GetEncryptCallbacks();
	EncryptModuleState *state = GetEncryptModuleState();

	if (cb == NULL || cb->encrypt_buffer_cb == NULL)
		ereport(ERROR,
				(errcode(ERRCODE_OBJECT_NOT_IN_PREREQUISITE_STATE),
				 errmsg("encryption module not loaded for base backup encryption")));

	/*
	 * Encrypt in place in our own buffer, then copy to the next sink's
	 * buffer and forward.
	 */
	cb->encrypt_buffer_cb(state, sink->bbs_buffer, len);

	memcpy(sink->bbs_next->bbs_buffer, sink->bbs_buffer, len);
	bbsink_archive_contents(sink->bbs_next, len);
}

/*
 * End of the current archive — flush any remaining data.
 */
static void
bbsink_encrypt_end_archive(bbsink *sink)
{
	bbsink_forward_end_archive(sink);
}

/*
 * Encrypt manifest contents the same way as archive contents.
 */
static void
bbsink_encrypt_manifest_contents(bbsink *sink, size_t len)
{
	const EncryptModuleCallbacks *cb = GetEncryptCallbacks();
	EncryptModuleState *state = GetEncryptModuleState();

	if (cb == NULL || cb->encrypt_buffer_cb == NULL)
		ereport(ERROR,
				(errcode(ERRCODE_OBJECT_NOT_IN_PREREQUISITE_STATE),
				 errmsg("encryption module not loaded for base backup encryption")));

	cb->encrypt_buffer_cb(state, sink->bbs_buffer, len);
	memcpy(sink->bbs_next->bbs_buffer, sink->bbs_buffer, len);
	bbsink_manifest_contents(sink->bbs_next, len);
}

/*
 * Cleanup.
 */
static void
bbsink_encrypt_cleanup(bbsink *sink)
{
	/* Nothing to free beyond what bbsink_cleanup handles */
}
