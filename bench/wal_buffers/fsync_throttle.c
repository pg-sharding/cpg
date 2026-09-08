/*
 * fsync_throttle.c — LD_PRELOAD library to simulate slow fsync/fdatasync.
 *
 * Build:  gcc -shared -fPIC -o fsync_throttle.so fsync_throttle.c -ldl
 * Usage:  LD_PRELOAD=./fsync_throttle.so THROTTLE_MS=20 pg_ctl -D data start
 *
 * THROTTLE_MS environment variable controls the artificial delay after
 * each fsync/fdatasync call (in milliseconds). Default 0 = no delay.
 */

#define _GNU_SOURCE
#include <unistd.h>
#include <dlfcn.h>
#include <time.h>
#include <stdlib.h>
#include <string.h>

static int (*real_fsync)(int) = NULL;
static int (*real_fdatasync)(int) = NULL;

static void delay_ms(int ms)
{
    if (ms <= 0)
        return;
    struct timespec ts;
    ts.tv_sec = ms / 1000;
    ts.tv_nsec = (ms % 1000) * 1000000L;
    nanosleep(&ts, NULL);
}

static int get_throttle_ms(void)
{
    const char *env = getenv("THROTTLE_MS");
    return env ? atoi(env) : 0;
}

int fsync(int fd)
{
    if (!real_fsync)
        real_fsync = dlsym(RTLD_NEXT, "fsync");
    int r = real_fsync(fd);
    delay_ms(get_throttle_ms());
    return r;
}

int fdatasync(int fd)
{
    if (!real_fdatasync)
        real_fdatasync = dlsym(RTLD_NEXT, "fdatasync");
    int r = real_fdatasync(fd);
    delay_ms(get_throttle_ms());
    return r;
}
