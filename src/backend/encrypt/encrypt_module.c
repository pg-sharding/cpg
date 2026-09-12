/*-------------------------------------------------------------------------
 *
 * encrypt_module.c
 *
 * Provides infrastructure for loading encryption modules.  This is roughly
 * analogous to the archive module infrastructure.
 *
 * Copyright (c) 2026, PostgreSQL Global Development Group
 *
 * IDENTIFICATION
 *	  src/backend/encrypt/encrypt_module.c
 *
 *-------------------------------------------------------------------------
 */
#include "postgres.h"

#include "encrypt/encrypt_module.h"
#include "encrypt/shell_encrypt.h"
#include "miscadmin.h"
#include "storage/fd.h"
#include "utils/guc.h"

/* GUC variables */
char	   *EncryptLibrary = "";
char	   *EncryptCommand = NULL;
char	   *DecryptCommand = NULL;
char	   *enc_module_check_errdetail_string;

/* Cached callbacks and state for the loaded module */
static const EncryptModuleCallbacks *EncryptCallbacks = NULL;
static EncryptModuleState *encrypt_module_state = NULL;
static bool encrypt_module_loaded = false;

/*
 * LoadEncryptLibrary
 *
 * Loads the encryption callbacks.  If encrypt_library is empty, the built-in
 * shell-based encryption is used.
 */
void
LoadEncryptLibrary(void)
{
	EncryptModuleInit encrypt_init;

	if (EncryptLibrary[0] != '\0' && EncryptCommand[0] != '\0')
		ereport(ERROR,
				(errcode(ERRCODE_INVALID_PARAMETER_VALUE),
				 errmsg("both \"encrypt_command\" and \"encrypt_library\" set"),
				 errdetail("Only one of \"encrypt_command\", \"encrypt_library\" may be set.")));

	/*
	 * If shell encryption is enabled, use our special initialization function.
	 * Otherwise, load the library and call its _PG_encrypt_module_init().
	 */
	if (EncryptLibrary[0] == '\0')
		encrypt_init = shell_encrypt_init;
	else
		encrypt_init = (EncryptModuleInit)
			load_external_function(EncryptLibrary,
								   "_PG_encrypt_module_init", false, NULL);

	if (encrypt_init == NULL)
		ereport(ERROR,
				(errmsg("encryption modules have to define the symbol %s",
						 "_PG_encrypt_module_init")));

	EncryptCallbacks = (*encrypt_init) ();

	if (EncryptCallbacks->encrypt_file_cb == NULL)
		ereport(ERROR,
				(errmsg("encryption modules must register an encrypt callback")));

	encrypt_module_state = palloc0_object(EncryptModuleState);
	if (EncryptCallbacks->startup_cb != NULL)
		EncryptCallbacks->startup_cb(encrypt_module_state);

	encrypt_module_loaded = true;
}

/*
 * UnloadEncryptLibrary
 *
 * Calls the shutdown callback of the loaded encryption module, if defined.
 */
void
UnloadEncryptLibrary(void)
{
	if (encrypt_module_loaded && EncryptCallbacks != NULL &&
		EncryptCallbacks->shutdown_cb != NULL)
		EncryptCallbacks->shutdown_cb(encrypt_module_state);

	encrypt_module_loaded = false;
	EncryptCallbacks = NULL;
	encrypt_module_state = NULL;
}

/*
 * GetEncryptCallbacks
 *
 * Returns the loaded encryption module callbacks, or NULL if no module has
 * been loaded.
 */
const EncryptModuleCallbacks *
GetEncryptCallbacks(void)
{
	return EncryptCallbacks;
}

/*
 * GetEncryptModuleState
 *
 * Returns the encryption module state, or NULL if no module has been loaded.
 */
EncryptModuleState *
GetEncryptModuleState(void)
{
	return encrypt_module_state;
}
