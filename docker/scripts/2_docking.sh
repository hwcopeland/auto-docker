#!/bin/sh
set -e

# docking: (pdbid:str, batch_label:str) -> ()

[ $# != 2 ] && echo "usage: $0 pdbid batch_label" && exit 1

PDBID=$1
BATCH_LABEL=$2

AUTODOCK_GPU=/autodock/autodock_gpu
FILELIST=filelist_${BATCH_LABEL}

echo $PDBID.maps.fld > $FILELIST
ls ${BATCH_LABEL}_*.pdbqt >> $FILELIST


# TODO: smart naming for ligands.pdbqt to avoid conflicts in shared storage, 
# which may (???) be used for several docking workloads
$AUTODOCK_GPU --filelist $FILELIST
