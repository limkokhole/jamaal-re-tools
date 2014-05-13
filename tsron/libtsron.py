import argparse
from argparse import RawTextHelpFormatter
import itertools, collections
from dpkt.ethernet import *
from dpkt.ip import *
from dpkt.tcp import *
from dpkt.pcap import *
from pcap import *
import dpkt
import pcap
import sys
import socket
import textwrap
import os


     #//def __init__(self, *args, **kwargs):
class Tsron(object):	
    '''TCP stream reassembler output normalizer - Rebuilds ordered TCP steams along with dumping UDP streams from pcaps'''
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        # // string normalize 
        self.pckNum = 0   
        self.streamCounter = 1
        self.streamCounterIndex = []
        self.streamDict = {}
        try:
    	   self.pcap = dpkt.pcap.Reader(open(self.srcpcap,'rb'))
        except ValueError:
            excepterr = str(sys.exc_info()[1])
            if excepterr == "invalid tcpdump header":
                fileName, fileExtension  = os.path.splitext(self.srcpcap.name)
                print "\nThe input pcap is most likely pcap-ng.  Convert it to libpcap using the following:\
                \n$ editcap -F libpcap " + self.srcpcap.name + " " + fileName+"_libpcap"+fileExtension + "\n"
                sys.exit(2)
        #self.getPacketDict()


    # // used to return packet type 
    def __ipProto(self,ip):
        '''Returns protocal tcp or udp data object based upon the type stream specified''' 
        if self.typestream == "TCP":
            if ip.p == IP_PROTO_TCP:
                tcp = ip.data
                if len(tcp.data) > 0:
                	return tcp
        if self.typestream == "GRE":
            if ip.p == IP_PROTO_GRE:
                gre = ip.gre
                tcp = gre.ip.data
                if tcp.ack >= 0 and tcp.seq >= 0:
                    if len(tcp.data) > 0:
                        return tcp
        if self.typestream == "UDP":
            if  ip.p == IP_PROTO_UDP:
                udp = ip.udp
                if  len(udp.data) > 0:
                    return udp

    def __iPpacketRules(self,ip,tcp,pckNum):
        '''Reorders TCP streams into dictionaries for sorting and processing'''
        if len(tcp.data) > 1:
            # // make one key regardless of source and dst by sorting them.  
            streamStr = [str(socket.inet_ntoa(ip.src))+"_"+str(tcp.sport),str(socket.inet_ntoa(ip.dst))+"_"+str(tcp.dport)]
            streamStr.sort()
            # // build the file string ip.src,sport,ip.dst,dspot seprated by "_"
            streamStr =''.join(str(e)+"_" for e in streamStr)
            streamStr = streamStr[:-1]
            if streamStr not in self.streamDict:
                self.streamDict[streamStr] = []
                self.streamDict[streamStr].append([tcp.seq + tcp.ack,pckNum,len(tcp.data)])
            else:
                if streamStr in self.streamDict:
                    self.streamDict[streamStr].append([tcp.seq + tcp.ack,pckNum,len(tcp.data)])


    def __UDPpacketRules(self,ip,udp,pckNum):
        '''Orders UDP streams based simple upon packet number as UDP is unordered'''
        if len(udp.data) > 1:
            # // make one key regardless of source and dst by sorting them.  
            streamStr = [str(socket.inet_ntoa(ip.src))+"_"+str(udp.sport),str(socket.inet_ntoa(ip.dst))+"_"+str(udp.dport)]
            streamStr.sort()
            # // build the file string ip.src,sport,ip.dst,dspot seprated by "_"
            streamStr =''.join(str(e)+"_" for e in streamStr)
            streamStr = streamStr[:-1]
            if streamStr not in self.streamDict:
                self.streamDict[streamStr] = []
                self.streamDict[streamStr].append([pckNum,pckNum,len(udp.data)])
            else:
                if streamStr in self.streamDict:
                    self.streamDict[streamStr].append([pckNum,pckNum,len(udp.data)])


    def __writeStream(self):
        '''Returns TCP/GRE/UDP stream to caller or writes streams to the filesystem in specified location'''
        # // allows us to access the entire packet for quick writing 
        streampkts = self.pcap.readpkts()
        if self.streamnum == 0:
            for key, value in self.streamDict.iteritems():
                if self.outdir:
                    if os.path.exists(self.outdir):
                        filestring = self.outdir + "//" + self.typestream + "_" + key
                        if os.path.exists(filestring):
                            os.remove(filestring)
                        f = open(self.outdir + "//" + self.typestream + "_" + key, 'ab')
                else:
                    f = open("tsron.stream.tmp", 'ab')

                # // http://stackoverflow.com/questions/2213923/python-removing-duplicates-from-a-list-of-lists
                # // Retransmissions are just that, packets with the same Seq, Ack and tcp.data lenght.
                # // The below sort and groupby will remove duplicates from a nested list 
                value.sort()
                value = list(value for value,_ in itertools.groupby(value))
                # // Sort the nested list by the first value in each list (Syn + Ack)
                for streamList in sorted(value):
                    pktWriteNumber = streamList[1]
                    # // We access the pcap this way to put unorded packets back in order 
                    eth = dpkt.ethernet.Ethernet(streampkts[pktWriteNumber-1][1])
                    ip = eth.data
                    tcp = self.__ipProto(ip)
                    if len(tcp.data) == 0:
                        print "ERROR for packet", tcp.seq, streamList
                    if self.outdir:
                        f.write(self.header + tcp.data)
                    else:
                        f.write(self.header + tcp.data)
                if self.outdir:
                    f.close()
            if self.outdir:
                return True
            else:
                f = open("tsron.stream.tmp", 'rb')
                return f.read()

        else:
            # // verify is our streams are in the dictionary 
            # // by finding the max number and comparing it to the lenght 
            # // of the dictionary.
            maxStreamNum = max(self.streamnum)
            if maxStreamNum <= len(self.streamDict):
                #for key, value in self.streamDict.iteritems():
                for streamIndex in self.streamnum:
                    key, value = self.streamDict.items()[streamIndex]
                    if self.outdir:
                        if os.path.exists(self.outdir):
                            filestring = self.outdir + "//" + self.typestream + "_" + key
                            if os.path.exists(filestring):
                                os.remove(filestring)
                            f = open(self.outdir + "//" + self.typestream + "_" + key, 'ab')
                    value.sort()
                    value = list(value for value,_ in itertools.groupby(value))
                    # // Sort the nested list by the first value in each list (Syn + Ack)
                    for streamList in sorted(value):
                        pktWriteNumber = streamList[1]
                        # // We access the pcap this way to put unorded packets back in order 
                        #print "help", help(self.pcap)
                        eth = dpkt.ethernet.Ethernet(streampkts[pktWriteNumber-1][1])
                        ip = eth.data
                        tcp = self.__ipProto(ip)
                        if len(tcp.data) == 0:
                            print "ERROR for packet", tcp.seq, streamList
                        if self.outdir:
                            f.write(self.header + tcp.data)
                        else:
                            f.write(self.header + tcp.data)
                    if self.outdir:
                        f.close()
                if self.outdir:
                    return True
                else:
                    f = open("tsron.stream.tmp", 'rb')
                    return f.read()


            else:
                #print "The highest stream number for this pcap is %d while the highest stream number specified to dump is %d " % (len(self.streamDict),maxStreamNum)
                print "\n--> %d is larger than the highest stream found (%d) " % (maxStreamNum,len(self.streamDict))
                print "--> Please specify a stream number no higher than %d for the -s option and try again..." % len(self.streamDict)
                print "exiting...\n"
                sys.exit()


    def __displayStream(self):
        '''Used to display stats associated with assembled streams'''
        for key, value in self.streamDict.iteritems(): 
            pckCnt = 0
            dlen = 0 
            dispkey = key.split("_")
            dispkey = str(dispkey[0])+(":")+str(dispkey[1])+" <--> "+str(dispkey[2])+(":")+str(dispkey[3])
            value.sort()
            value = list(value for value,_ in itertools.groupby(value))
            for streamList in sorted(value):
                pckCnt += 1 
                dlen += streamList[2]
            print str(self.streamCounter) + " " + dispkey + " | packets: " + str(pckCnt) + " data size: " + str(dlen)
            self.streamCounter += 1 
        return True 


    def TCP(self): 
        '''Returns TCP stream from pcap'''

        fcounter = 0 
        pckNum = 0
        print "Building streams......."
        for ts, buf in self.pcap:
            pckNum += 1
            eth = dpkt.ethernet.Ethernet(buf)
            try:
                if eth.type == ETH_TYPE_IP:
                    ip = eth.data
                    tcp = self.__ipProto(ip)
                    self.__iPpacketRules(ip,tcp,pckNum)
            except:
                fcounter += 1
                pass
        if self.display:
            self.__displayStream()
            sys.exit()
        else:
            self.__displayStream()
        return self.__writeStream()

    def GRE(self): 
        '''Returns GRE stream from pcap'''
        fcounter = 0 
        pckNum = 0
        print "Building streams......."
        for ts, buf in self.pcap:
            pckNum += 1
            eth = dpkt.ethernet.Ethernet(buf)
            try:
                if eth.type == ETH_TYPE_IP:
                    ip = eth.data
                    gre = self.__ipProto(ip)
                    self.__iPpacketRules(ip,gre,pckNum)
            except:
                fcounter += 1
                pass
        if self.display:
            self.__displayStream()
            sys.exit()
        else:
            self.__displayStream()
        return self.__writeStream()

    def UDP(self): 
        '''Returns UDP stream from PCAP'''
        fcounter = 0 
        pckNum = 0
        print "Building streams......."
        for ts, buf in self.pcap:
            pckNum += 1
            eth = dpkt.ethernet.Ethernet(buf)
            try:
                if eth.type == ETH_TYPE_IP:
                    ip = eth.data
                    udp = self.__ipProto(ip)
                    self.__UDPpacketRules(ip,udp,pckNum)
            except:
                fcounter += 1
                pass
        if self.display:    
            self.__displayStream()
            sys.exit()
        else:
            self.__displayStream()
        return self.__writeStream()
	
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Rebuild TCP/GRE/UDP streams',formatter_class=RawTextHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    parser.add_argument('--pcap','-p', dest='srcpcap', action='store', \
        help='Input pcap file to use.  Example: -p libpcap.pcap',required=True)
    group.add_argument('--dir', '-d',dest='outdir', action='store', help='output stream directory',default=None)
    parser.add_argument('--type','-T', dest='typestream', action='store', choices=['TCP','UDP','GRE'], default='TCP', \
        help='Type of stream to rip (TCP,UDP,GRE)')
    group.add_argument('-D', dest='display', action='store_true', help='Display stream table')
    parser.add_argument('-s', '--streams', dest='streamnum' ,nargs="+", type=int, action='store', \
        default=0, help='Extract only the specified streams:\nExample: -s 1 10 15')
    parser.add_argument('--header', dest='header', action='store', default="")


    if len(sys.argv) <= 1: 
        parser.print_help()
        sys.exit(1) 

    else:
        args = parser.parse_args()
        streamObj=Tsron(**vars(args))
        if args.typestream == "TCP":
            datastream = streamObj.TCP()
        if args.typestream == "GRE":
            datastream = streamObj.GRE()
        if args.typestream == "UDP":
            datastream = streamObj.UDP()

    #// calling libtsronV2 directly  
    #tvar = {'typestream': 'GRE', 'header': '__TSRONHEADER__', 'srcpcap': 'out_libpcap.pcap', 'streamnum': 0, 'display': True, 'outdir': None}
    #streamObj=Tsron(**tvar)

