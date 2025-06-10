#!/bin/bash
npx nativefier --inject link-fix-inject.js --icon aws-cloud9_512x512.png -n "AWS Cloud9 Dev Desktop" --hide-window-frame --disable-context-menu --single-instance --internal-urls .*amazon.com.* http://jdray.aka.amazon.com:8181/ide.html dist
