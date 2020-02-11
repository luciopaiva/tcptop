#!/usr/bin/env bash

PORT=""
if [ $# -eq 1 ]; then
    PORT="-p $1"
fi

COLUMNS="local_port,remote_addr,alias,state,backoff,rto,timer,send_queue,recv_queue,bytes_recv,unacked"
COLUMNS="${COLUMNS},retrans_cur,retrans_total,mss,ssthresh,segs_in,segs_out,last_ack_human"

watch -n1 "./tcptop -s established -o lastack -c ${COLUMNS} ${PORT}"
