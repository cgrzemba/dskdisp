dskdisp
=======

This tool shows Disk Informations on Solaris which provided by prtconf.

On Solaris there are different tools for showing disk data like paths and luns
but there is no tool for showing this information in a compact kind.

This is a try to extract this informations from 'prtconf -Dv'

./dskdisp.py -h
usage is:
list inforamtions for MPXIO devices
where options are:

    -f|--file <prtdiag -Dv Output file>
            file with the output of prtdiag -Dv

    -s|--short list, list only devlink and storage LUN

    -x|--hex print LUN in hex like luxadm


