#!/usr/bin/env bash

URL="https://github.com/luciopaiva/tcptop/archive/v0.1.0.tar.gz"

cd ~
mkdir -p bin
cd bin
curl ${URL} -L -o tcptop.tar.gz
tar -zxvf tcptop.tar.gz
rm tcptop.tar.gz
