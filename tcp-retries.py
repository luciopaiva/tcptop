#!/usr/bin/env python2.7
#
# tcp-retries.py
# by Lucio Paiva
# 2020 01 25
#
# This script shows your top clients wrt TCP retransmission problems. It probes the `ss` command to obtain the data.
#
# Reference for the ss field descriptions: http://man7.org/linux/man-pages/man8/ss.8.html
#

import argparse
import operator
import subprocess
import sys
from collections import namedtuple, defaultdict
from names import string_to_name

# how many sockets to show in the result list
TOP = 15

selected_state = ''
ss_params = ['ss', '-minto']

SocketParam = namedtuple("SocketParam", "index name format_str format_fn header_name")
socket_param_by_index = dict()
socket_param_by_name = dict()
next_param_index = 0


def setup_socket_param(name, format_str, header_name):
    global next_param_index
    socket_param = SocketParam(next_param_index, name, "%-{}s".format(format_str), str, header_name)
    socket_param_by_index[next_param_index] = socket_param
    socket_param_by_name[socket_param.name] = socket_param
    next_param_index += 1


setup_socket_param("local_port", "10",        "LocalPort")
setup_socket_param("local_addr", "21",        "LocalAddr")
setup_socket_param("remote_addr", "21",       "RemoteAddr")
setup_socket_param("state", "12",             "State")
setup_socket_param("backoff", "7",            "Backoff")
setup_socket_param("rto", "9",                "RTO")
setup_socket_param("timer", "9",              "Timer")
setup_socket_param("send_queue", "9",         "SendQ")
setup_socket_param("recv_queue", "9",         "RecvQ")
setup_socket_param("bytes_recv", "9",         "BytesRecv")
setup_socket_param("unacked", "7",            "UnACKed")
setup_socket_param("retrans_cur", "7",        "RetrCur")
setup_socket_param("retrans_total", "9",      "RetrTotal")
setup_socket_param("mss", "6",                "MSS")
setup_socket_param("ssthresh", "8",           "SSThresh")
setup_socket_param("segs_in", "8",            "SegsIn")
setup_socket_param("segs_out", "8",           "SegsOut")
setup_socket_param("send_window_scale", "10", "SendWndScl")
setup_socket_param("recv_window_scale", "10", "RecvWndScl")
setup_socket_param("congestion_window", "10", "CongWnd")
setup_socket_param("lastack", "10",           "LastAck")
setup_socket_param("tx", "10",                "Tx")
setup_socket_param("tx_buffer", "10",         "TxBuffer")
setup_socket_param("alias", "11",             "Alias")
setup_socket_param("last_ack_human", "10",    "LastAck")

param_names = " ".join([param.name for param in socket_param_by_index.values()])
Socket = namedtuple("Socket", param_names)

sockets = []

selected_columns = ["local_port", "remote_addr", "alias", "state", "backoff", "rto", "timer", "send_queue",
                    "recv_queue", "bytes_recv", "unacked", "retrans_cur", "retrans_total", "mss", "ssthresh", "segs_in",
                    "segs_out", "last_ack_human"]


def run_ss():
    output = subprocess.check_output(ss_params)
    lines = output.splitlines()
    lines = lines[1:]  # remove header

    if len(lines) % 2 != 0:
        raise Exception("Must have even number of lines to continue")

    return lines


def process_socket_line(socket_line):
    fields = socket_line.split()

    if fields[0].isdigit():
        state = selected_state
        field_delta = -1
    else:
        state = fields[0]
        field_delta = 0

    recv_queue = fields[1 + field_delta]
    send_queue = fields[2 + field_delta]
    local_addr = fields[3 + field_delta]
    local_port = local_addr.split(":")[1]
    remote_addr = fields[4 + field_delta]

    retrans_cur, retrans_total = 0, 0
    send_window_scale, recv_window_scale = 0, 0
    congestion_window = 0
    bytes_recv = 0
    lastack = 0
    backoff = 0
    timer = 0
    unacked = 0
    rto = 0
    mss = 0
    ssthresh = 0
    segs_out = 0
    segs_in = 0
    tx = 0
    tx_buffer = 0

    for field in fields:
        if field.startswith('retrans:'):
            retrans_cur, retrans_total = parse_retrans(field)
        elif field.startswith('wscale:'):
            send_window_scale, recv_window_scale = parse_wscale(field)
        elif field.startswith('cwnd:'):
            congestion_window = parse_cwnd(field)
        elif field.startswith('bytes_received:'):
            bytes_recv = parse_bytes_recv(field)
        elif field.startswith('lastack:'):
            lastack = parse_lastack(field)
        elif field.startswith('backoff:'):
            backoff = parse_backoff(field)
        elif field.startswith('timer:'):
            timer = parse_timer(field)
        elif field.startswith('unacked:'):
            unacked = parse_unacked(field)
        elif field.startswith('rto:'):
            rto = parse_rto(field)
        elif field.startswith('mss:'):
            mss = parse_mss(field)
        elif field.startswith('ssthresh:'):
            ssthresh = parse_ssthresh(field)
        elif field.startswith('segs_out:'):
            segs_out = parse_segs_out(field)
        elif field.startswith('segs_in:'):
            segs_in = parse_segs_in(field)
        elif field.startswith('skmem:'):
            tx, tx_buffer = parse_skmem(field)

    socket = Socket(state=state, local_addr=local_addr, remote_addr=remote_addr, recv_queue=recv_queue,
                    send_queue=send_queue, retrans_cur=retrans_cur, retrans_total=retrans_total,
                    send_window_scale=send_window_scale, recv_window_scale=recv_window_scale,
                    congestion_window=congestion_window, bytes_recv=bytes_recv, lastack=lastack, timer=timer,
                    backoff=backoff, local_port=local_port, unacked=unacked, rto=rto, mss=mss, ssthresh=ssthresh,
                    segs_out=segs_out, segs_in=segs_in, tx=tx, tx_buffer=tx_buffer, alias="", last_ack_human="")
    sockets.append(socket)


def parse_retrans(field):
    """ retrans:1/2
        the first number tells the current number of retries of an in flight packet missing an ack
        the second number tells how many retransmissions have occurred since the connection was established
    """
    try:
        cur, total = field[8:].split('/')
        return int(cur), int(total)
    except:
        print field
        exit(1)


def parse_wscale(field):
    """ wscale:1,2
        the first number is the send scale factor
        the second number is the recv scale factor
        this is an extension to the original TCP protocol allowing for windows larger than than 64kB
    """
    send, recv = field[7:].split(',')
    return int(send), int(recv)


def parse_cwnd(field):
    """ cwnd:10 
        not clear in the manual, but apparently this is measured in multiples of maximum segment size (MSS)
        (according to this article: https://packetbomb.com/understanding-throughput-and-tcp-windows/)
    """
    return int(field[5:])


def parse_bytes_recv(field):
    """ bytes_received:1
        how many bytes were received by this socket since the connection was established
    """
    return int(field[15:])


def parse_lastack(field):
    """ lastack:123
        how long ago did we receive the last ack from this client, in milliseconds
    """
    return int(field[8:])


def parse_timer(field):
    """ timer:(on,1min2sec,14)
        shows if socket currently has a retransmission running
        the third argument is the current retry count (Linux by default retries a packet 15 before giving up)
        BUT sometimes the third argument is something else! not sure what, though
        the second argument shows how long until this retry ends with a retransmission timeout
    """
    _, timer, backoff = field[7:-1].split(',')
    return timer


def parse_backoff(field):
    """ backoff:2
        the current retry count (Linux by default retries a packet 15 before giving up)
    """
    return int(field[8:])


def parse_unacked(field):
    """ unacked:3
        how many segments are in-flight, still not ACKed by the remote peer
    """
    return int(field[8:])


def parse_rto(field):
    """ rto:120000
        the timeout for the current retransmission round, in millis (it does not update as the timer goes - check
        parse_timer() if you're looking for that)
    """
    return int(field[4:])


def parse_mss(field):
    """ mss:1500
        maximum segment size, in bytes
    """
    return int(field[4:])


def parse_ssthresh(field):
    """ ssthresh:2
        slow start threshold
    """
    return int(field[9:])


def parse_segs_out(field):
    """ segs_out:10
        segments sent
    """
    return int(field[9:])


def parse_segs_in(field):
    """ segs_in:10
        segments received
    """
    return int(field[8:])


def parse_skmem(field):
    """ skmem:(r0,rb233880,t0,tb46080,f1792,w2304,o0,bl0)
        socket memory parameters
    """
    sub_fields = field[7:-1].split(",")
    tx = 0
    tx_buffer = 0
    for sub_field in sub_fields:
        if sub_field.startswith("tb"):
            tx_buffer = int(sub_field[2:])
        elif sub_field.startswith("t"):
            tx = int(sub_field[1:])
    return tx, tx_buffer


def print_counts_by_state():
    counts_by_state = defaultdict(int)
    for socket in sockets:
        counts_by_state[socket.state] += 1
    print('Clients by state:')
    for state, count in sorted(counts_by_state.items(), key=operator.itemgetter(0)):
        print('- %s: %d' % (state, count))


def time_to_human(time):
    time_in_secs = time // 1000
    minutes = time_in_secs // 60
    seconds = time_in_secs % 60
    return "%dmin%dsec" % (minutes, seconds)


def main():
    lines = run_ss()
    # run ss and obtain raw data from it

    for line1, line2 in zip(lines[::2], lines[1::2]):  # each socket occupies two lines in the output
        process_socket_line(line1 + ' ' + line2)

    line_format = []
    header_names = []
    for name in selected_columns:
        sparam = socket_param_by_name[name]
        line_format.append(sparam.format_str)
        header_names.append(sparam.header_name)
    line_format = " ".join(line_format)
    print(line_format % tuple(header_names))

    for socket in sorted(sockets, key=lambda sock: sock.lastack, reverse=True)[:TOP]:
        alias = string_to_name(socket.remote_addr)
        last_ack_human = time_to_human(socket.lastack)
        values = []
        for name in selected_columns:
            if name is "alias":
                values.append(alias)
            elif name is "last_ack_human":
                values.append(last_ack_human)
            else:
                sparam = socket_param_by_name[name]
                values.append(socket[sparam.index])
        print(line_format % tuple(values))

    print('')
    print('Total clients: %d' % len(sockets))
    print('')
    print_counts_by_state()


if len(sys.argv) > 2:
    selected_state = sys.argv[2]
    ss_params.extend(['state', selected_state])
else:
    ss_params.extend(['state', 'connected'])

if len(sys.argv) > 1:
    ss_params.append('( sport = :' + sys.argv[1] + ' )')

main()
