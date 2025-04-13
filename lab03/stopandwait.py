from enum import IntEnum
import struct

from defs import Event
import checksums

# This is an implementation of a stop-and-wait data link protocol with piggybacking.
# It is based on Tanenbaum's `protocol 4', 2nd edition, p227.
# This protocol employs data frames with piggybacked acknowledgments.

nodeinfo = None
linkinfo = []


def enable_application(nodenumber=None):
    pass


def disable_application(nodenumber=None):
    pass


def start_timer(event, usecs, data=None):
    return 0  # returns a timerid


def stop_timer(timerid):
    pass


def timer_data(timerid):
    pass


def set_handler(event, callback):
    pass


def write_physical(linknum, framebytes):
    return True  # iff write successful (link existed)


def write_application(message):
    return True  # iff message accepted


# Protocol-specific code

class FrameType(IntEnum):
    DLL_DATA = 0
    DLL_ACK = 1
    DLL_NACK = 2


class Frame:
    def __init__(self):
        self.kind = FrameType.DLL_DATA
        self.len = 0  # the length of the msg field only
        self.checksum = 0  # checksum of the whole frame
        self.seq = 0  # only ever 0 or 1
        self.ack = 0  # acknowledgment for received frame
        self.msg = bytes()

    # Updated to include ACK field
    def pack(self):
        return struct.pack('!HHiHH{}s'.format(len(self.msg)),
                           self.kind, self.len, self.checksum,
                           self.seq, self.ack, self.msg)

    def unpack(self, bytes):
        maxbytelen = len(bytes) - struct.calcsize('!HHiHH')
        self.kind, self.len, self.checksum, self.seq, self.ack, self.msg = struct.unpack_from(
            '!HHiHH{}s'.format(maxbytelen), bytes)


class Node:
    def __init__(self):
        self.lastmsg = None
        self.data_timer = None  # Timer for data retransmission
        self.ack_timer = None  # Timer for delayed ACKs
        self.ackexpected = 0  # Sequence number expected to be acknowledged
        self.nextframetosend = 0  # Sequence number of next outgoing frame
        self.frameexpected = 0  # Sequence number of next expected incoming frame
        self.ack_pending = False  # Is there an acknowledgment waiting to be sent?
        self.pending_ack_seq = 0  # Sequence number of the pending acknowledgment
        self.printspaces = '\t' * (nodeinfo.nodenumber * 4)

    # Modified to include ACK information
    def transmit_frame(self, msg: bytes, kind: FrameType, seqno: int):
        f = Frame()
        f.kind = kind
        f.seq = seqno
        f.checksum = 0
        f.len = len(msg)
        f.msg = msg

        # Include acknowledgment info if available
        if self.ack_pending and kind == FrameType.DLL_DATA:
            f.ack = self.pending_ack_seq
            self.ack_pending = False
            if self.ack_timer:
                stop_timer(self.ack_timer)
                self.ack_timer = None
            print('{}Piggybacking ACK, seq={}'.format(self.printspaces, self.pending_ack_seq))
        else:
            # For explicit ACK frames, use the ack field to carry the sequence number
            if kind == FrameType.DLL_ACK:
                f.ack = seqno
            else:
                f.ack = 0  # No ACK information

        packed = f.pack()
        f.checksum = checksums.checksum_ccitt(packed)
        packed = f.pack()

        link = 1
        write_physical(link, packed)

        if kind == FrameType.DLL_ACK:
            print('{}ACK transmitted, seq={}'.format(self.printspaces, seqno))
        elif kind == FrameType.DLL_DATA:
            print('{}DATA transmitted, seq={}'.format(self.printspaces, seqno))

            # Calculate timeout based on frame size and link properties
            timeout = (len(packed) * (8000000 // linkinfo[link].bandwidth)
                       + linkinfo[link].propagationdelay)

            self.data_timer = start_timer(Event.TIMER1, 3 * timeout, None)

    # Handler for when application has data to send
    def application_ready(self, destination: int, message: bytes):
        self.lastmsg = message
        disable_application()

        print('{}Down from application, seq={}'.format(self.printspaces, self.nextframetosend))

        self.transmit_frame(self.lastmsg, FrameType.DLL_DATA, self.nextframetosend)
        self.nextframetosend = 1 - self.nextframetosend

    # Handler for when physical layer has data
    def physical_ready(self, linkno: int, framebytes: bytes):
        f = Frame()
        f.unpack(framebytes)

        checksum = f.checksum
        f.checksum = 0

        if (checksum != checksums.checksum_ccitt(f.pack())):
            print('{}BAD checksum - frame ignored'.format(self.printspaces))
            return

        # Process piggybacked ACK if present in a data frame
        if f.kind == FrameType.DLL_DATA:
            # Check for piggybacked ACK
            if f.ack == self.ackexpected:
                print('{}Received piggybacked ACK, seq={}'.format(self.printspaces, f.ack))
                stop_timer(self.data_timer)
                self.ackexpected = 1 - self.ackexpected
                enable_application()

            # Process data portion
            if f.seq == self.frameexpected:
                write_application(f.msg)
                self.frameexpected = 1 - self.frameexpected
                result = 'up to application'

                # Set pending ACK for piggybacking
                self.ack_pending = True
                self.pending_ack_seq = f.seq

                # Start timer for delayed ACK (1 second = 1,000,000 microseconds)
                if self.ack_timer:
                    stop_timer(self.ack_timer)
                self.ack_timer = start_timer(Event.TIMER2, 1000000, f.seq)

            else:
                result = 'ignored'

            print('{}DATA received, seq={}, {}'.format(self.printspaces, f.seq, result))

        # Process explicit ACK frame
        elif f.kind == FrameType.DLL_ACK:
            if f.ack == self.ackexpected:
                print('{}ACK received, seq={}'.format(self.printspaces, f.ack))
                stop_timer(self.data_timer)
                self.ackexpected = 1 - self.ackexpected
                enable_application()

    # Handler for data frame transmission timeouts
    def data_timeout(self):
        print('{}Data timeout, retransmitting seq={}'.format(self.printspaces, self.ackexpected))
        self.transmit_frame(self.lastmsg, FrameType.DLL_DATA, self.ackexpected)

    # Handler for delayed ACK timeouts
    def ack_timeout(self, timerid):
        # Get the sequence number from the timer data
        seq = timer_data(timerid)
        print('{}ACK timeout, sending explicit ACK for seq={}'.format(self.printspaces, seq))
        self.ack_pending = False
        self.transmit_frame(bytes(), FrameType.DLL_ACK, seq)

    # Node initialization
    def reboot_node(self):
        if (nodeinfo.nodenumber > 1):
            print('This is not a 2-node network!')
            exit(1)

        set_handler(Event.APPLICATIONREADY, self.application_ready)
        set_handler(Event.PHYSICALREADY, self.physical_ready)
        set_handler(Event.TIMER1, self.data_timeout)
        set_handler(Event.TIMER2, self.ack_timeout)  # New handler for delayed ACKs

        # Enable application on both nodes to allow bidirectional traffic
        enable_application()