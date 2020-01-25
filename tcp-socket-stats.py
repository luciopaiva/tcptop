#!/usr/bin/env python2.7
#
# tcp-sockets.py
# by Lucio Paiva
# 2020 01 25
#
# This script can be used to shed some light into what is happening with your clients' connections. It parses and 
# digests the output of the `ss` command.
#
# Reference for the ss field descriptions: http://man7.org/linux/man-pages/man8/ss.8.html
#

import sys
import subprocess
import operator
from collections import namedtuple, defaultdict
from names import string_to_name

# how many sockets to show in the result list
TOP = 15

selected_state = ''
ss_params = ['ss', '-minto']

Socket = namedtuple("Socket", "state local_addr remote_addr send_queue recv_queue retrans_cur retrans_total " + \
    "send_window_scale recv_window_scale congestion_window bytes_received lastack backoff timer local_port unacked " + \
    "rto")

sockets = []


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
    bytes_received = 0
    lastack = 0
    backoff = 0
    timer = 0
    unacked = 0
    rto = 0

    for field in fields:
        if field.startswith('retrans:'):
            retrans_cur, retrans_total = parse_retrans(field)
        elif field.startswith('wscale:'):
            send_window_scale, recv_window_scale = parse_wscale(field)
        elif field.startswith('cwnd:'):
            congestion_window = parse_cwnd(field)
        elif field.startswith('bytes_received:'):
            bytes_received = parse_bytes_received(field)
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

    socket = Socket(state=state, local_addr=local_addr, remote_addr=remote_addr, recv_queue=recv_queue, \
        send_queue=send_queue, retrans_cur=retrans_cur, retrans_total=retrans_total, \
        send_window_scale=send_window_scale, recv_window_scale=recv_window_scale, \
        congestion_window=congestion_window, bytes_received=bytes_received, lastack=lastack, timer=timer, \
        backoff=backoff, local_port=local_port, unacked=unacked, rto=rto)
    sockets.append(socket)


def parse_retrans(field):
    """ retrans:1/2
        the first number tells the current number of retries of an in flight packet missing an ack
        the second number tells how many retransmissions have occurred since the connection was established
    """
    try:
        cur, total = field[8:].split('/')
    except:
        print field
        exit(1)
    return int(cur), int(total)

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

def parse_bytes_received(field):
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
    _,timer,backoff = field[7:-1].split(',')
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

    print("%-9s  %-21s  %-11s  %-12s  %-7s  %-9s  %-9s  %-9s  %-9s  %-9s  %-7s  %-5s  %-7s  %-10s" % \
        ("LocalPort", "Client", "Alias", "State", "Backoff", "RTO", "Timer", "SendQueue", "RecvQueue", "BytesRecv", \
        "Unacked", "RTCur", "RTTotal", "LastACK"))

    for socket in sorted(sockets, key=lambda socket: socket.lastack, reverse=True)[:TOP]:
        alias = string_to_name(socket.remote_addr)
        last_ack_human = time_to_human(socket.lastack)
        print("%-9s  %-21s  %-11s  %-12s  %-7s  %-9s  %-9s  %-9s  %-9s  %-9s  %-7d  %-5d  %-7d  %-10s" % \
            (socket.local_port, socket.remote_addr, alias, socket.state, str(socket.backoff), socket.rto, \
            socket.timer, str(socket.send_queue), str(socket.recv_queue), str(socket.bytes_received), socket.unacked, \
            socket.retrans_cur, socket.retrans_total, last_ack_human))

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
