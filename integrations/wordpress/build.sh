#!/bin/sh
# Builds the plugin zip the Website screen offers for download.
# Run from anywhere: integrations/wordpress/build.sh
set -eu
here=$(cd "$(dirname "$0")" && pwd)
out="$here/../../web/public/downloads"
mkdir -p "$out"
rm -f "$out/ppcway-wordpress.zip"
cd "$here"
zip -q -r -X "$out/ppcway-wordpress.zip" ppcway -x '*.DS_Store'
echo "wrote $out/ppcway-wordpress.zip"
