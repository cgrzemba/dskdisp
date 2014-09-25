#!/usr/bin/env python
# ************************************************************************
# * This tool shows multipathing devices and the corresponding 
# * storage WWN, LUN in a compact manner
# * This informations a extracted from 'prtconf -Dv' so you can use this
# * tool also 'offline' e.g. use explorer output 
# * 
# * Written By: Carsten Grzemba (cgrzemba@opencsw.org)
# * 
# CDDL HEADER START
#
# The contents of this file are subject to the terms of the
# Common Development and Distribution License (the "License").
# You may not use this file except in compliance with the License.
#
# You can obtain a copy of the license at pkg/OPENSOLARIS.LICENSE
# or http://www.opensolaris.org/os/licensing.
# See the License for the specific language governing permissions
# and limitations under the License.
#
# When distributing Covered Code, include this CDDL HEADER in each
# file and include the License file at pkg/OPENSOLARIS.LICENSE.
# If applicable, add the following below this CDDL HEADER, with the
# fields enclosed by brackets "[]" replaced with your own identifying
# information: Portions Copyright [yyyy] [name of copyright owner]
#
# CDDL HEADER END
# ************************************************************************

from sys import exit, argv
from subprocess import Popen, PIPE
from re import findall, match, sub, compile
import getopt
import pdb

filename = ''
printHex = False
printShort = False
discovZpool = False

printon_iscsi = False
printon_dev = False

lunlst = []

def usage():
    print """usage is:
list inforamtions for MPXIO devices
where options are:

    -f|--file <prtdiag -Dv Output file>
            file with the output of prtdiag -Dv

    -s|--short list, list only devlink and storage LUN
    
    -z|--zpool print LUN of all zpools

    -x|--hex print LUN in hex like luxadm
"""

class Lun(object):
     headprinted = False
     lst = []
     def __init__(self):
         self.guidlst = []
         self.lunlst = []           
         self.vendor = ''
         self.blksize= 800
         self.devlink = '/dev/rdsk/c0t'
         
     def __init__(self,inst):
         self.guidlst = []
         self.lunlst = []
         self.vendor = ''
         self.inst = inst
         self.blksize= 800
         self.devlink = '/dev/rdsk/c0t'

     def addDevId(self, id):
        self.devid = id
     def getDevId(self):
        return self.devid
     def addBlkSize(self, no):
        self.blksize = int(no,16)
     def addNBlk(self, no):
        self.nblocks = int(no,16)
     def addSerno(self, no):
        self.serial = no
     def addVendor(self, name):
        self.vendor = name
     def addProd(self, name):
        self.prod = name
     def addLink(self, name):
        self.devlink = name

     def addLun(self, no):
        self.lunlst.append(no)
     def addLink(self, link):
        self.devlink = link

     def addGuid(self,guid):
        if guid not in self.guidlst:
            self.guidlst.append(guid)

     def getGuid(self):
         if len(self.guidlst) > 0:
             return self.guidlst[0]
         return None

     def setSinglePath(self):
         ''' is not a multipahing device '''
         self.singlepath = True

     def printVal(self):
         if not Lun.headprinted and not printShort:
             print "ssd devid                                      SN                            Vendor  PROD           \n\tLun list\n\tguid list"
             Lun.headprinted = True
         elif not Lun.headprinted and not printShort:
             print "devlink, LUN list"
         print '' if printShort else "%3d" % self.inst,
         try:
             print '' if printShort else "%42s" % self.devid,
             print "%-50s" % ("%s" % self.devlink),
         except AttributeError:
             print "%-50s" % 'none' if printShort else "%-92s" % 'none',
         try:
             print '' if printShort else "%-28s" % self.serial,
         except AttributeError:
             print "%-28s" % 'none',
         try:
             print '' if printShort else "%-8s" % self.vendor,
         except AttributeError:
             print "%-8s" % 'none',
         try:
             print '' if printShort else "%-16s" % self.prod,
         except AttributeError:
             print "%-16s" % 'none',
         try:
             print "%8dMB" % int(self.nblocks*self.blksize/1024/1024),
         except AttributeError:
             print "%10s" % 'unknown',
         try:
             if self.singlepath: print "single path",
         except AttributeError:
             pass
         try:
             if not printShort or len(self.lunlst) == 0:
                 print
             for l in self.lunlst:
                 print "\tLUN %s" % l if printHex else "\t%s,%d" % (l.partition(',')[0],int(l.partition(',')[2],16))
                 if printShort:
                     break
         except AttributeError:
             pass
         try:
             if not printShort:
                 for g in self.guidlst:
                     print "\tGID %s" % g
         except AttributeError:
             print

     def merge(self):
         found = False
         for l in Lun.lst:
             try:
                 if l.getDevId() ==  self.getDevId():
                      found = True
                      l.addGuid(self.getGuid())
             except AttributeError:
                  pass
         if not found:
             Lun.lst.append(self)

def getZpoolDevs():
    mpdevs = []
    zpools = []

    with Popen(['/usr/sbin/mpathadm','list', 'LU'], stdout=PIPE).stdout as fl:  
        mpdevs = [ (line.strip()) for line in fl.readlines() if 'rdsk' in line]
    fl = Popen(['/usr/sbin/zpool','status'], stdout=PIPE).stdout
    lines = fl.readlines()
    iter_lines = iter(lines)
    devpat = compile('(/dev/(r)?dsk/)?(c.*d0)(s[0-9])?')
    for line in iter_lines:
        if 'pool:' in line:
            zd = {}
            poolname = line.split()[1]
            zd[poolname] = []
            for line in iter_lines:
                if len(line.split()) > 4:
                    if  line.split()[0] in ('errors:'):
                        break
                    if  line.split()[0] in (poolname,'mirror-0', 'NAME', 'scan:'):
                        continue
                    if match(devpat, line.split()[0]):
                        for d in mpdevs:
                            if match(devpat, line.split()[0]).groups()[2] == match(devpat, d).groups()[2]:
                                zd[poolname].append(d)
                                break

            zpools.append(zd)
    return zpools
 

def getDev(iter_lines,inst):
    lun = Lun(inst)
    for line in iter_lines:
        if 'Device Minor Nodes:' in line :
            for line in iter_lines:
                if len(lun.lunlst)  == 0:
                        # special handling for non multipathing device
                    lun.setSinglePath()
                    if line.split('=')[0].strip() == 'dev_path':
                        l = sub('^[a-z]','',line.rpartition('@')[2].strip().split(':')[0])
                        lun.addLun(l)
                        continue
                if line.split('=')[0].strip() == 'dev_link':
                    lun.addLink(line.split('=')[1].strip())
                    break
            lun.merge()
            return
        if 'name=' in line:
            if line.split('=')[1].split()[0] == "'inquiry-serial-no'":
                lun.addSerno(iter_lines.next().split('=')[1].split("'")[1])
                continue
            elif line.split('=')[1].split()[0] == "'device-pblksize'":
                lun.addBlkSize(iter_lines.next().split('=')[1])
                continue
            elif line.split('=')[1].split()[0] == "'device-nblocks'":
                lun.addNBlk(iter_lines.next().split('=')[1])
                continue
            elif line.split('=')[1].split()[0] == "'devid'":
                lun.addDevId(iter_lines.next().split('=')[1].split("'")[1])
                continue
            elif line.split('=')[1].split()[0] == "'inquiry-product-id'":
                lun.addProd(iter_lines.next().split('=')[1].split("'")[1])
                continue
            elif line.split('=')[1].split()[0] == "'inquiry-vendor-id'":
                lun.addVendor(iter_lines.next().split('=')[1].split("'")[1])
                continue
            elif line.split('=')[1].split()[0] == "'client-guid'":
                lun.addGuid(iter_lines.next().split('=')[1].split("'")[1])
                continue
        #          pdb.set_trace()
        if match('[ ]*Path [0-9]*: [/a-z0-9@,]*',line.strip()):
            lun.addLun(line.rpartition('@')[2][1:].strip())


### MAIN PROGRAM ###
if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(argv[1:], '?hsxf:z',
            ['help', 'short', 'hex', 'file=', 'zpool'])

    except getopt.GetoptError, e:
        usage()
        exit(1)

    for o, a in opts:
        if o in ('-h', '-?', '--help'):
            usage()
            exit(0)
        elif o in ('-x', '--hex'):
            printHex = True
        elif o in ('-s', '--short'):
            printShort = True
        elif o in ('-z', '--zpool'):
            discovZpool = True
        elif o in ('-f', '--file'):
            filename = a

    zpools = []
    if discovZpool:
        zpools = getZpoolDevs()

    if filename:
        fl = open(filename)
    else:
        fl = Popen(['/usr/sbin/prtconf','-Dv'],stdout=PIPE).stdout
        
    lines = fl.readlines()
    iter_lines = iter(lines)
    for line in iter_lines:
        if 'pseudo, instance' in line :
          printon_iscsi = False
        if 'iscsi, instance' in line or 'scsi_vhci, instance':
          printon_iscsi = True
        if printon_iscsi and 'name=' in line and line.split('=')[1].split()[0] == "'mpxio-disable'":
          print 'mpxio-disable: '+iter_lines.next().split('=')[1],
        if printon_iscsi and 'disk, instance' in line or 'ssd, instance' in line:
          getDev(iter_lines,int(findall('#[0-9]*',line)[0].replace("#","")))

    if zpools:
        devpat = compile('(/dev/(r)?dsk/)?(c.*d0)(s[0-9])?')
        for zp in zpools:
            
            # import pdb; pdb.set_trace()
            print "Pool: ", zp.keys()[0]
            for zpdev in zp.values():
                for l in Lun.lst:
                    for zpd in zpdev:
                        if match(devpat, l.devlink).groups()[2] == match(devpat, zpd).groups()[2]:
                            l.printVal()
                            break        
    else:
        for l in Lun.lst:
            l.printVal()
