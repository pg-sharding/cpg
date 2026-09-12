/*-------------------------------------------------------------------------
 *
 * shell_encrypt.c
 *
 * This encryption function uses a user-specified shell command (the
 * encrypt_command GUC) to encrypt files.  It is used as the default, but
 * other modules may define their own custom encryption logic.
 *
 * Copyright (c) 2026, PostgreSQL Global Development Group
 *
 * IDENTIFICATION
 *	  src/backend/encrypt/shell_encrypt.c
 *
 *-------------------------------------------------------------------------
 */
#include "postgres.h"

#include <sys/wait.h>

#include "access/xlog.h"
#include "common/percentrepl.h"
#include "encrypt/encrypt_module.h"
#include "encrypt/shell_encrypt.h"
#include "pgstat.h"
#include "utils/wait_event.h"

static bool shell_encrypt_configured(EncryptModuleState *state);
static bool shell_encrypt_file(EncryptModuleState *state, const char *file,
							   const char *path);
static bool shell_decrypt_file(EncryptModuleState *state, const char *file,
							   const char *path);
static void shell_encrypt_shutdown(EncryptModuleState *state);

static const EncryptModuleCallbacks shell_encrypt_callbacks = {
	.startup_cb = NULL,
	.check_configured_cb = shell_encrypt_configured,
	.encrypt_file_cb = shell_encrypt_file,
	.decrypt_file_cb = shell_decrypt_file,
	.shutdown_cb = shell_encrypt_shutdown
};

const EncryptModuleCallbacks *
shell_encrypt_init(void)
{
	return &shell_encrypt_callbacks;
}

static bool
shell_encrypt_configured(EncryptModuleState *state)
{
	if (EncryptCommand[0] != '\0')
		return true;

	enc_module_check_errdetail("\"%s\" is not set.",
								"encrypt_command");
	return false;
}

static bool
shell_encrypt_file(EncryptModuleState *state, const char *file,
				   const char *path)
{
	char	   *encryptcmd;
	char	   *nativePath = NULL;
	int			rc;

	if (path)
	{
		nativePath = pstrdup(path);
		make_native_path(nativePath);
	}

	encryptcmd = replace_percent_placeholders(EncryptCommand,
											   "encrypt_command", "fp",
											   file, nativePath);

	ereport(DEBUG3,
			(errmsg_internal("executing encrypt command \"%s\"",
							 encryptcmd)));

	fflush(NULL);
	pgstat_report_wait_start(WAIT_EVENT_ENCRYPT_COMMAND);
	rc = system(encryptcmd);
	pgstat_report_wait_end();

	if (rc != 0)
	{
		int			lev = wait_result_is_any_signal(rc, true) ? FATAL : LOG;

		if (WIFEXITED(rc))
		{
			ereport(lev,
					(errmsg("encrypt command failed with exit code %d",
							WEXITSTATUS(rc)),
					 errdetail("The failed encrypt command was: %s",
							   encryptcmd)));
		}
		else if (WIFSIGNALED(rc))
		{
#if defined(WIN32)
			ereport(lev,
					(errmsg("encrypt command was terminated by exception 0x%X",
							WTERMSIG(rc)),
					 errhint("See C include file \"ntstatus.h\" for a description of the hexadecimal value."),
					 errdetail("The failed encrypt command was: %s",
							   encryptcmd)));
#else
			ereport(lev,
					(errmsg("encrypt command was terminated by signal %d: %s",
							WTERMSIG(rc), pg_strsignal(WTERMSIG(rc))),
					 errdetail("The failed encrypt command was: %s",
							   encryptcmd)));
#endif
		}
		else
		{
			ereport(lev,
					(errmsg("encrypt command exited with unrecognized status %d",
							rc),
					 errdetail("The failed encrypt command was: %s",
							   encryptcmd)));
		}
		pfree(encryptcmd);

		return false;
	}
	pfree(encryptcmd);

	elog(DEBUG1, "encrypted file \"%s\"", file);
	return true;
}

static bool
shell_decrypt_file(EncryptModuleState *state, const char *file,
				   const char *path)
{
	char	   *decryptcmd;
	char	   *nativePath = NULL;
	int			rc;

	if (path)
	{
		nativePath = pstrdup(path);
		make_native_path(nativePath);
	}

	decryptcmd = replace_percent_placeholders(DecryptCommand,
											   "decrypt_command", "fp",
											   file, nativePath);

	ereport(DEBUG3,
			(errmsg_internal("executing decrypt command \"%s\"",
							 decryptcmd)));

	fflush(NULL);
	pgstat_report_wait_start(WAIT_EVENT_DECRYPT_COMMAND);
	rc = system(decryptcmd);
	pgstat_report_wait_end();

	if (rc != 0)
	{
		int			lev = wait_result_is_any_signal(rc, true) ? FATAL : LOG;

		if (WIFEXITED(rc))
		{
			ereport(lev,
					(errmsg("decrypt command failed with exit code %d",
							WEXITSTATUS(rc)),
					 errdetail("The failed decrypt command was: %s",
							   decryptcmd)));
		}
		else if (WIFSIGNALED(rc))
		{
#if defined(WIN32)
			ereport(lev,
					(errmsg("decrypt command was terminated by exception 0x%X",
							WTERMSIG(rc)),
					 errhint("See C include file \"ntstatus.h\" for a description of the hexadecimal value."),
					 errdetail("The failed decrypt command was: %s",
							   decryptcmd)));
#else
			ereport(lev,
					(errmsg("decrypt command was terminated by signal %d: %s",
							WTERMSIG(rc), pg_strsignal(WTERMSIG(rc))),
					 errdetail("The failed decrypt command was: %s",
							   decryptcmd)));
#endif
		}
		else
		{
			ereport(lev,
					(errmsg("decrypt command exited with unrecognized status %d",
							rc),
					 errdetail("The failed decrypt command was: %s",
							   decryptcmd)));
		}
		pfree(decryptcmd);

		return false;
	}
	pfree(decryptcmd);

	elog(DEBUG1, "decrypted file \"%s\"", file);
	return true;
}

static void
shell_encrypt_shutdown(EncryptModuleState *state)
{
	elog(DEBUG1, "encryption module shutting down");
}
