#!/usr/bin/python

import threading, requests, sys, json, os, socket
from optparse import OptionParser

class terminal_colors:
    red = '\033[31m'
    green = '\033[32m'
    yellow = '\033[33m'
    blue = '\033[34m'
    cyan = '\033[36m'
    bright_red = '\033[91m'
    bright_green = '\033[92m'

    bold = '\033[1m'
    faint = '\033[2m'

    end = '\033[0m'

def parse_arguments():
    """ returns a tuple (options, app_path) """
    parser = OptionParser(usage="usage: %prog [options] app_path")

    parser.add_option('', '--follow',
        dest='follow', action='store_true',
        help='output the opened app\'s output until it exits', default=False)

    parser.add_option('', '--raw',
        dest='raw', action='store_true',
        help='when following output raw JSON objects, rather than parsing the log output', default=False)

    options, args = parser.parse_args()

    if len(args) != 1:
        parser.print_help()
        sys.exit(1)

    return options, args[0]


def follow(app_path, raw):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('127.0.0.1', 10452))

    fd = sock.makefile('r')

    messages_iterator = (json.loads(line) for line in fd)

    # wait for the start of the process
    for message in messages_iterator:
        if 'started' in message and message['path'] == app_path:
            if raw:
                sys.stdout.write(json.dumps(message) + '\n')
            else:
                print 'tbopen: App started as PID %i' % message['started']
            break

    # echo all the logs until the ended message
    for message in messages_iterator:
        if raw:
            sys.stdout.write(json.dumps(message) + '\n')
        else:
            if 'stdout' in message:
                sys.stdout.write(message['stdout'])
                sys.stdout.flush()
            if 'stderr' in message:
                sys.stdout.write(terminal_colors.red + message['stderr'] + terminal_colors.end)
                sys.stdout.flush()
        if 'ended' in message:
            break


def main():
    options, app_path = parse_arguments()

    if options.follow:
        tail_thread = threading.Thread(target=follow, kwargs={
            'app_path': app_path,
            'raw': options.raw,
        })
        tail_thread.daemon = True
        tail_thread.start()

    r = requests.post('http://127.0.0.1:10451/run', data=app_path)
    r.raise_for_status()

    if options.follow:
        tail_thread.join()

if __name__ == '__main__':
    main()
