#!/bin/bash
source /mochi/opt/app-env/blogofilepy26/bin/activate
blogofile build && rsync -a ./_site/ etrepum@pythonmac.org:pythonmac.org/bob-blogofile/
