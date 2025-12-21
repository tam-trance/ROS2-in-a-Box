#!/bin/bash
set -e

echo "=== WRAPPER DEBUG 2 ==="
echo "Script path: $0"
echo "PWD: $(pwd)"
echo "EXT_BUILD_ROOT: $EXT_BUILD_ROOT"
ls -F $EXT_BUILD_ROOT
echo "Listing directories in EXT_BUILD_ROOT:"
find $EXT_BUILD_ROOT -maxdepth 2 -type d
echo "=== END WRAPPER DEBUG 2 ==="

# Create local_lib and symlinks
mkdir -p local_lib
ln -sf $EXT_BUILD_DEPS/lib/* local_lib/
ln -sf $EXT_BUILD_DEPS/lib/libcrypto_internal.a local_lib/libcrypto.a
ln -sf $EXT_BUILD_DEPS/lib/libssl_internal.a local_lib/libssl.a
ln -sf $EXT_BUILD_DEPS/lib/libzlib.a local_lib/libz.a

export LDFLAGS="-L$(pwd)/local_lib $LDFLAGS"
export AR=ar
export RANLIB=ranlib

# Try to find configure again, looking at EXT_BUILD_ROOT
CONFIGURE_SCRIPT=$(find $EXT_BUILD_ROOT -name configure -print -quit)

if [ -z "$CONFIGURE_SCRIPT" ]; then
    echo "ERROR: configure script not found in EXT_BUILD_ROOT!"
    exit 1
fi

echo "Found configure at: $CONFIGURE_SCRIPT"
# We might need to run configure from the directory containing it, or pass full path
CONFIGURE_DIR=$(dirname "$CONFIGURE_SCRIPT")

# If we need to run from source dir:
# cd "$CONFIGURE_DIR"
# But we usually build out-of-source or in-source?
# configure_make usually supports out-of-source.
# So calling it with full path is fine.

$CONFIGURE_SCRIPT "$@" || {
    echo "=== CONFIG.LOG START ==="
    if [ -f config.log ]; then
        cat config.log
    elif [ -f "$CONFIGURE_DIR/config.log" ]; then
        cat "$CONFIGURE_DIR/config.log"
    else
        echo "config.log not found"
    fi
    echo "=== CONFIG.LOG END ==="
    exit 1
}