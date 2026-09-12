/*-------------------------------------------------------------------------
 *
 * encrypt_module.h
 *		Exports for encryption modules.
 *
 * Copyright (c) 2026, PostgreSQL Global Development Group
 *
 * src/include/encrypt/encrypt_module.h
 *
 *-------------------------------------------------------------------------
 */
#ifndef _ENCRYPT_MODULE_H
#define _ENCRYPT_MODULE_H

/*
 * The values of the encrypt_library, encrypt_command, and decrypt_command
 * GUCs.
 */
extern PGDLLIMPORT char *EncryptLibrary;
extern PGDLLIMPORT char *EncryptCommand;
extern PGDLLIMPORT char *DecryptCommand;

typedef struct EncryptModuleState
{
	/*
	 * Private data pointer for use by an encryption module.  This can be used
	 * to store state for the module that will be passed to each of its
	 * callbacks.
	 */
	void	   *private_data;
} EncryptModuleState;

/*
 * Encryption module callbacks
 *
 * These callback functions should be defined by encryption libraries and
 * returned via _PG_encrypt_module_init().  The encrypt callback is the only
 * required callback.  For more information about the purpose of each
 * callback, refer to the encryption modules documentation.
 */
typedef void (*EncryptStartupCB) (EncryptModuleState *state);
typedef bool (*EncryptCheckConfiguredCB) (EncryptModuleState *state);
typedef bool (*EncryptFileCB) (EncryptModuleState *state, const char *file,
							   const char *path);
typedef bool (*DecryptFileCB) (EncryptModuleState *state, const char *file,
							   const char *path);
typedef void (*EncryptShutdownCB) (EncryptModuleState *state);

typedef struct EncryptModuleCallbacks
{
	EncryptStartupCB startup_cb;
	EncryptCheckConfiguredCB check_configured_cb;
	EncryptFileCB encrypt_file_cb;
	DecryptFileCB decrypt_file_cb;
	EncryptShutdownCB shutdown_cb;
} EncryptModuleCallbacks;

/*
 * Type of the shared library symbol _PG_encrypt_module_init that is looked
 * up when loading an encryption library.
 */
typedef const EncryptModuleCallbacks *(*EncryptModuleInit) (void);

extern PGDLLEXPORT const EncryptModuleCallbacks *_PG_encrypt_module_init(void);

/* Support for messages reported from encryption module callbacks. */

extern PGDLLIMPORT char *enc_module_check_errdetail_string;

#define enc_module_check_errdetail \
	pre_format_elog_string(errno, TEXTDOMAIN), \
	enc_module_check_errdetail_string = format_elog_string

/* Routines for loading and unloading encryption modules. */
extern void LoadEncryptLibrary(void);
extern void UnloadEncryptLibrary(void);
extern const EncryptModuleCallbacks *GetEncryptCallbacks(void);
extern EncryptModuleState *GetEncryptModuleState(void);

#endif							/* _ENCRYPT_MODULE_H */
