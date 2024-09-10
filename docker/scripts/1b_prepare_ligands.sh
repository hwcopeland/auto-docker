#!/bin/sh
set -e

# prepare_ligands: (pdbid:str, batch_label:str) -> ()

[ $# != 2 ] && echo "usage: $0 pdbid batch_label" && exit 1

PDBID=$1
BATCH_LABEL=$2

FILELIST=filelist_${BATCH_LABEL}

# Convert SDF to PDBQT
# -m: split
obabel ${BATCH_LABEL}.sdf -O ${BATCH_LABEL}_.pdbqt -m

# Create a filelist from PBDID + all ligands in the batch
echo $PDBID.maps.fld > $FILELIST
ls ${BATCH_LABEL}_*.pdbqt >> $FILELIST
