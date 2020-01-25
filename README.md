
# tcp-retries

Python script to list TCP clients having retransmission problems. The scripts probes the `ss` command to obtain the data and then sorts connections by last ACK time, oldest first.

This script needs Python 2.7.

How to run:

    watch -n1 ./tcp-socket-stats.py

Optionally, you may pass your server's listening port to filter client sockets:

    watch -n1 ./tcp-socket-stats.py 8080

You can also filter sockets by state:

    watch -n1 ./tcp-socket-stats.py 8080 established

Refer to `man ss` for valid state strings. If you want to filter by state but not by port, pass `0` as the port.

## Acknowledgements

I am using a list of names taken from [this project](https://github.com/treyhunner/names) (license [here](https://github.com/treyhunner/names/blob/master/LICENSE.txt)).
