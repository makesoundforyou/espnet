#!/usr/bin/env bash
#
# Copyright  2020  University of Stuttgart (Author: Pavel Denisov)
# Apache 2.0

# Begin configuration section.
# End configuration section
. ./utils/parse_options.sh  # accept options

. ./path.sh

echo >&2 "$0" "$@"
if [ $# -ne 1 ] ; then
  echo >&2 "$0" "$@"
  echo >&2 "$0: Error: wrong number of arguments"
  echo -e >&2 "Usage:\n  $0 <asr-dir>"
  echo -e >&2 "eg:\n  $0 download/asr_librispeech"
  exit 1
fi

asr_dir=$1

set -e -o pipefail

mkdir -p ${asr_dir}

download_from_google_drive.sh \
	"https://drive.google.com/open?id=17cOOSHHMKI82e1MXj4r2ig8gpGCRmG2p" \
	${asr_dir}  ".tar.gz"
