#!/usr/bin/env python
# Small utility to upload a file to an embedded Linux system that provides a
# shell via its serial port.

import time
import argparse
import traceback


class SerialFTP(object):

    def __init__(self, port, baudrate=115200, io_time=0.01, quiet=False,
                 bytes_per_line=20):
        self.bytes_per_line = bytes_per_line or 20
        self.quiet = quiet
        self.io_time = io_time
        self.port = port
        self.baudrate = baudrate
        self._socket = None

    @property
    def socket(self):
        if self._socket is None:
            self._socket = serial.Serial(port=self.port, baudrate=self.baudrate)
        return self._socket

    def put(self, source, destination):
        data = open(source, 'rb').read()
        data_size = len(data)
        i = 0

        # Create/zero the file
        self.write('\necho -ne > %s\n' % destination)

        # Loop through all the bytes in the source file and append them to
        # the destination file bytes_per_line bytes at a time
        while i < data_size:
            j = 0
            dpart = ''

            while j < self.bytes_per_line and i < data_size:
                dpart += '\\x%.2X' % int(ord(data[i]))
                j += 1
                i += 1

            self.write('\necho -ne "%s" >> %s\n' % (dpart, destination))

            # Show upload status
            if not self.quiet:
                print("%d / %d" % (i, data_size))

        return i

    def write(self, data):
        self.socket.write(data)
        if data.endswith('\n'):
            # Have to give the target system time for disk/flash I/O
            time.sleep(self.io_time)

    def close(self):
        self.socket.close()


class TelnetFTP(SerialFTP):

    def __init__(self, host, login, passwd, *args, **kwargs):
        super(TelnetFTP, self).__init__(*args, **kwargs)
        self.host = host
        self.login = login
        self.passwd = passwd

    @property
    def socket(self):
        if self._socket is None:
            self._socket = telnetlib.Telnet(self.host, self.port, timeout=10)
            # We're not interested in matching input, just interested
            # in consuming it, until it stops
            DONT_MATCH = "\xff\xff\xff"
            if self.login:
                print(self.socket.read_until(DONT_MATCH, 0.5))
                self.socket.write(self.login + "\n")
                print(self.socket.read_until(DONT_MATCH, 0.5))
                self.socket.write(self.passwd + "\n")
            # Skip shell banner
            print(self.socket.read_until(DONT_MATCH, self.io_time))
        return self._socket


def main():
    parser = argparse.ArgumentParser(
        description='Upload file via serial or Telnet connection')
    parser.add_argument('-s', '--source', help='Path to local file')
    parser.add_argument('-d', '--destination', help='Path to remote file')
    parser.add_argument(
        '-p', '--port',
        help='Serial port to use [/dev/ttyUSB0] or telnet port [23]'
    )
    parser.add_argument(
        '-b', '--baudrate', default=115200, type=int,
        help='Serial port baud rate'
    )
    parser.add_argument(
        '-t', '--wait-time', default=0.01, type=float,
        help='Time to wait between echo commands'
    )
    parser.add_argument(
        '-q', '--quiet', action='store_true',
        help='Reduce verbosity'
    )
    parser.add_argument(
        '--bytes-per-line', default=20, type=int,
        help='Number of bytes to send per echo command'
    )
    parser.add_argument('--telnet', help='Upload via telnet instead of serial')
    parser.add_argument('--host', help='Host for telnet connection')
    parser.add_argument('--login', help='Login name for telnet')
    parser.add_argument('--passwd', help='Password name for telnet')
    args = parser.parse_args()

    try:
        if args.host:
            global telnetlib
            import telnetlib
            port = int(args.port) or 23
            print(args.host, port, args.wait_time, args.quiet)
            sftp = TelnetFTP(args.host, port, login=args.login,
                             passwd=args.passwd, io_time=args.wait_time,
                             quiet=args.quiet,
                             bytes_per_line=args.bytes_per_line)
        else:
            global serial
            import serial
            port = args.port or '/dev/ttyUSB0'
            sftp = SerialFTP(port, baudrate=args.baudrate,
                             io_time=args.wait_time, quiet=args.quiet,
                             bytes_per_line=args.bytes_per_line)
        size = sftp.put(args.source, args.destination)
        sftp.close()

        print('Uploaded %d bytes from %s to %s' %
              (size, args.source, args.destination))
    except:
        traceback.print_exc()


if __name__ == '__main__':
    main()
