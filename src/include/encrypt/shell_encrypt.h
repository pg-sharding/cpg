/*-------------------------------------------------------------------------
 *
 * shell_encrypt.h
 *		Exports for the shell-based encryption method.
 *
 * Copyright (c) 2026, PostgreSQL Global Development Group
 *
 * src/include/encrypt/shell_encrypt.h
 *
 *-------------------------------------------------------------------------
 */
#ifndef _SHELL_ENCRYPT_H
#define _SHELL_ENCRYPT_H

extern const EncryptModuleCallbacks *shell_encrypt_init(void);

#endif							/* _SHELL_ENCRYPT_H */
