#!/bin/bash
# Vercel build script — vercel.json's buildCommand has a 256-character limit,
# too short for the full Flutter clone + build one-liner, so it lives here
# instead and vercel.json just calls "bash build.sh".
set -e
git clone https://github.com/flutter/flutter.git -b stable --depth 1 /tmp/flutter
/tmp/flutter/bin/flutter config --enable-web
/tmp/flutter/bin/flutter pub get
/tmp/flutter/bin/flutter build web --release \
  --dart-define=API_BASE_URL=https://smartgrid-backend-ibcs.onrender.com
