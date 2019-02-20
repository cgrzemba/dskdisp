#!/usr/bin/env python -t
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
import os
from socket import gethostname

filename = ''
printHex = False
printShort = False
discovZpool = False

printon_iscsi = False
printon_dev = False

explo_prtconf = 'sysconfig/prtconf-vD.out'
explo_zpools = 'disks/zfs/zpool_status_-v.out'
explo_mpath = 'disks/mpathadm/mpathadm_list_LU.out'
# arch_members = (explo_prtconf, explo_zpools, explo_mpath)

lunlst = []

def usage():
    print """usage is:
list inforamtions for MPXIO devices
where options are:

    -f|--file <prtdiag -Dv Output file>
            file with the output of prtdiag -Dv
	--explorer <path>

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
         self.blksize= 512
         self.pblksize= 512
         self.devlink = '/dev/rdsk/c0t'
         
     def __init__(self,inst):
         self.guidlst = []
         self.lunlst = []
         self.vendor = ''
         self.inst = inst
         self.blksize= 512
         self.pblksize= 512
         self.devlink = '/dev/rdsk/c0t'

     def addDevId(self, id):
        self.devid = id
     def getDevId(self):
        return self.devid
     def addBlkSize(self, no):
        self.blksize = int(no,16)
     def addPBlkSize(self, no):
        self.pblksize = int(no,16)
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
             print "ssd  devid                                     devlink                                            SN                           Vendor   PROD                   size\n\tLun list\n\tGID/dev WWN"
             Lun.headprinted = True
         elif not Lun.headprinted and not printShort:
             print "devlink, LUN list"
         print "%3d" % self.inst,
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
             print "%8dGB" % int(self.nblocks*self.blksize/1024/1024/1024),
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
         except ValueError:
             pass
         try:
             if not printShort:
                 for g in self.guidlst:
                     print "\t%s" % g
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

def getZpoolDevs(ml=None, zl=None):
    mpdevs = []
    zpools = []

    if not ml or not zl:
        ml = Popen(['/usr/sbin/mpathadm','list', 'LU'], stdout=PIPE).stdout
        zl = Popen(['/usr/sbin/zpool','status'], env={'LC_ALL':'C'}, stdout=PIPE).stdout
    mpdevs = [ (line.strip()) for line in ml.readlines() if 'rdsk' in line]
    
    lines = zl.readlines()
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
        if 'sd, instance' in line:
            # offline LUN has no dev links
            lun.addLink('')
            lun.merge()
            return line
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
            return line
        if 'name=' in line:
            if line.split('=')[1].split()[0] == "'inquiry-serial-no'":
                lun.addSerno(iter_lines.next().split('=')[1].split("'")[1])
                continue
            elif line.split('=')[1].split()[0] == "'device-pblksize'":
                lun.addPBlkSize(iter_lines.next().split('=')[1])
                continue
            elif line.split('=')[1].split()[0] == "'device-blksize'":
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
            else:
                continue
        #          pdb.set_trace()
        if match('[ ]*Path [0-9]*: [/a-z0-9@,]*',line.strip()):
            lun.addLun(line.rpartition('@')[2][1:].strip())

def openExplo(explorer):
    if os.path.isdir(explorer):
        fprtconf = open(os.path.join(explorer,explo_prtconf))
        fzpools = open(os.path.join(explorer,explo_zpools))
        fmpath = open(os.path.join(explorer,explo_mpath))
    elif os.path.isfile(explorer):
        import tarfile
        
        basetf = match("(.+).tar.*", explorer).groups()[0]
        tar = tarfile.open(explorer)
        fprtconf = tar.extractfile(os.path.join(basetf, explo_prtconf))
        fzpools = tar.extractfile(os.path.join(basetf, explo_zpools))
        fmpath = tar.extractfile(os.path.join(basetf, explo_mpath))
    else:
        print "file/directory %s not found" % explorer
        exit(1)
    return fprtconf,fzpools,fmpath

### MAIN PROGRAM ###
if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(argv[1:], '?hsxf:zg:',
            ['help', 'short', 'hex', 'file=', 'zpool', 'explorer='])

    except getopt.GetoptError, e:
        usage()
        exit(1)
    
    explorer = None
    fzpools = None
    fmpath = None
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
        elif o in ('-g', '--explorer'):
            explorer = a

    zpools = []
    

    if explorer:
        if filename:
            print "WARNING: ignore %s because use explorer output" % filename
        fl,fzpools,fmpath = openExplo(explorer)
    else:
        if filename:
            if discovZpool:
                print "ERROR: would use ZPOOL data of %s" % gethostname()
                exit(2)
            fl = open(filename)
        else:
            fmpath = Popen(['/usr/sbin/mpathadm','list', 'LU'], stdout=PIPE).stdout
            fzpools = Popen(['/usr/sbin/zpool','status'], env={'LC_ALL':'C'}, stdout=PIPE).stdout
            fl = Popen(['/usr/sbin/prtconf','-Dv'],stdout=PIPE).stdout
    if discovZpool:
        zpools = getZpoolDevs(fmpath, fzpools)
        
    lines = fl.readlines()
    iter_lines = iter(lines)
    prevline, line = None, iter_lines.next()
    for line in iter_lines:
        if 'pseudo, instance' in line :
            printon_iscsi = False
        if 'iscsi, instance' in line or 'scsi_vhci, instance' in line:
            printon_iscsi = True
        if printon_iscsi and 'name=' in line and line.split('=')[1].split()[0] == "'mpxio-disable'":
            print 'mpxio-disable: '+iter_lines.next().split('=')[1],
        if printon_iscsi and 'disk, instance' in line or 'sd, instance' in line:
            lastline = getDev(iter_lines,int(findall('#[0-9]*',line)[0].replace("#","")))
            while 'disk, instance' in lastline or 'sd, instance' in lastline:
                lastline = getDev(iter_lines,int(findall('#[0-9]*',lastline)[0].replace("#","")))

    # pdb.set_trace()
    if zpools:
        devpat = compile('(/dev/(r)?dsk/)?(c.*d0)(s[0-9])?')
        for zp in zpools:
            
            # import pdb; pdb.set_trace()
            print "\nZpool: ", zp.keys()[0]
            for zpdev in zp.values():
                for l in Lun.lst:
                    for zpd in zpdev:
                        try:
                            if match(devpat, l.devlink).groups()[2] == match(devpat, zpd).groups()[2]:
                                l.printVal()
                                break        
                        except AttributeError:
                           pass
    else:
        for l in Lun.lst:
            l.printVal()
