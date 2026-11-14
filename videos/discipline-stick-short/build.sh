#!/bin/bash
# Render every variant: build.sh [indices...]   (default: 0 1 2 3 4)
cd "$(dirname "$0")"
names=(discipline obsession talent ego discipline-obsession)
for i in ${@:-0 1 2 3 4}; do
  sed -i "s/^const VI = [0-9];/const VI = $i;/" index.html
  npx hyperframes render -o "renders/v$((i+1))-${names[$i]}-wins.mp4" 2>&1 | grep -E "MB|rror"
done
sed -i "s/^const VI = [0-9];/const VI = 0;/" index.html
