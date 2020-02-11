#!/usr/bin/env bash

PORT=""
if [ $# -eq 1 ]; then
    PORT="-p $1"
fi

COLUMNS="local_port,remote_addr,alias,state,send_queue,recv_queue,segs_in,segs_out,tx,tx_buffer"

watch -n1 "./tcptop -o tx_buffer -c ${COLUMNS} ${PORT}"
