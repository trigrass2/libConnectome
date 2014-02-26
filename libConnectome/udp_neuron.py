import socket,sys, struct
from datetime import datetime
import time

def ip2long(ip):
    """
    Convert IP string to long
    """
    return struct.unpack("!L", socket.inet_aton(ip))[0]


def long2ip(ip):
    """
    Convert long to IP
    """
    return socket.inet_ntoa(struct.pack('!L', ip))


class Neuron:

    connections = []
    chost = "localhost"
    cport = 10000
    accumulator = 0
    paused = False
    threshold = 15
    neuron_id = 0
    socket_timeout = 0.2
    s = None
    sc = None
    parsed = None
    test_num = 0

    def __init__(self, arg):
        'args: 1 = id, 2. weight, 3. threshold, 4. connections (ip:port), 5. controller ip, 6: controller port'
        # anything between -1000 and +values is considered a weight
        # -99999 shutdown neuron
        # -99998 pause/unpause neuron. XXX is id of the neuron.
        # -95000 reset accumulator to 0
        # -94000 fire immidiatelly
        # -93XXX add/remove connection to id XXX
        # -92XXX.XX change threshold to XXX,XX
        # -91XXX get status of (TBD)
        # -90XXX set timeout to XXX (s)

        self.neuron_id = int(arg[1])
        self.threshold = float(arg[2])
        self.paused = False

        for c in arg[3].split(','):
            self.connections.append(c.split(':')[::-1])

#        self.chost = arg[4]  # controller host
        self.cport = int(arg[5])  # controller port
        self.lport = 10000 + self.neuron_id  # set port

        #init controller connection
        import socket

        self.sc = socket.socket(socket.AF_INET, # Internet
                         socket.SOCK_DGRAM) # UDP

    def setup_listener(self):
        self.s = socket.socket(socket.AF_INET,  socket.SOCK_DGRAM)   # Create a socket object
        self.s.bind(('localhost', self.lport))        # Bind to the port.
        self.s.settimeout(self.socket_timeout)        # Set timeout of 200ms
        self.call_controller("Online")

    def fire(self):
        try:
            for c in self.connections:
                self.s.sendto(str(c[0]), (c[2], int(c[1])))
                self.accumulator = 0
                self.call_controller("Firing to NID: " + str(int(c[1])) + ". Weight: " + str(c[0]))
                time.sleep(0.05)
        except:
            e = sys.exc_info()[0]
            self.call_controller("Error %s" % e)

    def call_controller(self,msg,type=0):
        if type == 1:
            msg = str(datetime.now()) + " - Error - NID: " + str(self.neuron_id) + ". " + msg
        if type == 0:
            msg = str(datetime.now()) + " - Notice - NID: " + str(self.neuron_id) + ". " + msg
        self.sc.sendto(msg, (self.chost, self.cport))

    def process(self):
        try:
            data, addr = self.s.recvfrom(1024)  # buffer size is 1024 bytes
            self.parsed = float(data)
            print self.parsed
            if self.parsed < -1000:
                if self.parsed == -99999:
                    self.accumulator = -1000000  # return 1M to quit
                if self.parsed == -99998:
                    self.paused = not self.paused
                    if self.paused:
                        self.call_controller("Paused", 0)
                    else:
                        self.call_controller("Resumed", 0)
                if self.parsed == -95000:
                    self.accumulator = 0
                if self.parsed == -94000:
                    self.fire()
                if self.parsed < -90000 and self.parsed > -91000:
                    self.s.settimeout(float(data[3:]))
                    self.socket_timeout = float(data[3:])
                if self.parsed < -92000 and self.parsed > -93000:
                    self.weight = float(data[3:])
                if self.parsed < -93000 and self.parsed > -94000:
                    try:
                        port = str(int(data[3:6]) + 10000)
                        host = long2ip(long(data[7:]))
                    except ValueError:
                        self.call_controller("port.host format invalid", 1)
                    try:
                        if not any(port == x[0] for x in self.connections):
                            self.connections.append([port,host])
                            self.call_controller("Connection to " + str(host) + ":" + str(port)+" added")
                        else:
                            self.connections.remove([port,host])
                            self.call_controller("Connection to " + str(host) + ":" + str(port)+" removed")
                    except ValueError:
                        self.call_controller("Connection removed")
            else:
                if not self.paused:
                    self.accumulator += self.parsed
                    if self.accumulator >= self.threshold:
                        self.fire()
                    return self.accumulator
                else:
                    self.call_controller("Paused. Ignoring non control data", 0)

        except ValueError:
                self.call_controller("Invalid data. Ignoring", 1)

        except socket.timeout:
            #timeout. reset accumulator to 0
            self.accumulator = 0



n = Neuron(sys.argv)
n.setup_listener()

try:
    while n.accumulator > -99999:
            n.process()
except KeyboardInterrupt:
    print "Ctrl+C detected. Shutting down"
    try:
        n.s.sendto( "Unexpected error:", sys.exc_info()[0],('localhost','10000'))
    except: 
        print "Neuron offline. Unable to notify the controller"
except:
    e = sys.exc_info()[0]
    n.s.sendto(e)
