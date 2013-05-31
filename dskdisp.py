#!/usr/bin/env python

from sys import exit, argv
from subprocess import Popen, PIPE
from re import findall, match
import getopt
import pdb

# filename = 'prtconf_150.txt'
# filename = 'prtconf_unie.txt'
filename = ''
printHex = False
printShort = False

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
    
    -x|--hex print LUN in hex like luxadm
"""
    
class Lun(object):
     headprinted = False
     lst = []
     def __init__(self):
         self.guidlst = []
         self.lunlst = []
         self.vendor = ''
     def __init__(self,inst):
         self.guidlst = []
         self.lunlst = []
         self.vendor = ''
         self.inst = inst

     def addDevId(self, id):
        self.devid = id
     def getDevId(self):
        return self.devid  
     def addSerno(self, no):
        self.serial = no
     def addVendor(self, name):
        self.vendor = name
     def addProd(self, name):
        self.prod = name
     def addLun(self, no):
        self.lunlst.append(no)
     def addGuid(self,guid):
        if guid not in self.guidlst:
            self.guidlst.append(guid)
     def getGuid(self):
         return self.guidlst[0]
     def printVal(self):
         if not Lun.headprinted and not printShort:
             print "ssd devid                                      SN                            Vendor  PROD           \n\tLun list\n\tguid list"
             Lun.headprinted = True
         elif not Lun.headprinted:
             print "devlink, LUN list"
         print '' if printShort else "%3d" % self.inst,
         try:
             print '' if printShort else "%42s" % self.devid,
             print "/dev/rdsk/%sd0s2" % self.devid.partition('@')[2][1:].upper(),
         except AttributeError:
             pass
         try: 
             print '' if printShort else "%-28s" % self.serial, 
         except AttributeError:
             pass
         try: 
             print '' if printShort else "%-8s" % self.vendor, 
         except AttributeError:
             pass
         try: 
             print '' if printShort else "%-16s" % self.prod, 
         except AttributeError:
             pass
         try:
             print 
             for l in self.lunlst:
                 print "\t%s" % l if printHex else "\t%s,%d" % (l.partition(',')[0],int(l.partition(',')[2],16)) 
         except AttributeError:
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

def getDev(iter_lines,inst):
      lun = Lun(inst)
      for line in iter_lines:
          if 'Device Minor Nodes:' in line :
              lun.merge()
              return
          if 'name=' in line:
              if line.split('=')[1].split()[0] == "'inquiry-serial-no'":
                  lun.addSerno(iter_lines.next().split('=')[1].split("'")[1])
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
        opts, args = getopt.getopt(argv[1:], '?hsxf:', 
            ['help', 'short', 'hex', 'file=']) 

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
        elif o in ('-f', '--file'):
            filename = a

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
    
    for l in Lun.lst:
        l.printVal()
    
