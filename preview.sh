#!/bin/bash
source /mochi/opt/app-env/blogofilepy26/bin/activate
blogofile build
sh -c 'sleep 2; open http://127.0.0.1:8000/' &
(cd _site; python -mSimpleHTTPServer)
