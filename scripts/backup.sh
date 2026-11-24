#!/bin/sh

set -eu
umask 077

cd "$(dirname "$0")/.."

. ./scripts/_backup_common.sh

sauvegarder online
