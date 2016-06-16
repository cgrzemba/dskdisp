dskdisp
=======

This tool shows Disk Informations on Solaris which provided by prtconf.

On Solaris there are different tools for showing disk data like paths and luns
but there is no tool for showing this information in a compact manner.

This is a try to extract this informations from 'prtconf -Dv'. For list LUN associated to zpool it uses also output from 'mpathadm list LU' and 'zpool status'. It is also possible to show the data from **explorer** output offline.

 ./dskdisp.py -h
 usage is:
 list inforamtions for MPXIO devices
 where options are:

    -f|--file <prtdiag -Dv Output file>
            file with the output of prtdiag -Dv

    -g|--explorer <path to explorer> TAR(.gz) or unpacked explorer

    -s|--short list, list only devlink and storage LUN

    -z|--zpool print LUN of all zpools

    -x|--hex print LUN in hex like luxadm

show LUN per Zpool:
```
 ./dskdisp.py -sz
 mpxio-disable: 'no'
  
 Zpool:  rpool
   0  /dev/dsk/c0t5000CCA0259F42F0d0s0                        286102MB   5000cca0259f42f1,0
   1  /dev/dsk/c0t5000CCA0259A6444d0s0                        286102MB   5000cca0259a6445,0
  
 Zpool:  zones2
  30  /dev/dsk/c0t60080E50003ED2380000078754646F57d0s0        307200MB   50080e53e9d78004,5
```
