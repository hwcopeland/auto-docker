#!/bin/sh
set -e

[ $# != 1 ] && echo "usage: $0 pdbid" && exit 1

MGLTOOLS=/autodock/mgltools
AUTOGRID=/autodock/./autogrid4
SCRIPT=$(readlink -f "$0")
SCRIPTDIR=$(dirname "$SCRIPT")

PDBID=$(echo $1 | tr '[:upper:]' '[:lower:]')
RECEPTOR_PDB=${PDBID}.pdb

# 1- Retrieve protein, and convert it to PDBQT
wget https://files.rcsb.org/download/${PDBID}.pdb -O $RECEPTOR_PDB

# only keep the longest chain (-r)
obabel $RECEPTOR_PDB -o pdb -r -h -O $RECEPTOR_PDB

LD_LIBRARY_PATH=$MGLTOOLS/lib $MGLTOOLS/bin/python2.7 \
	$MGLTOOLS/MGLToolsPckgs/AutoDockTools/Utilities24/prepare_receptor4.py \
	-r $RECEPTOR_PDB -o $PDBID.pdbqt

# 2- Prepare GPF
# TODO: how to set that from outside the script - auto-detect?, generic list?, ... ???
LIGAND_TYPES='A C HD N OA P NA'

# detect the list of atom types in the protein
RECEPTOR_TYPES=$(awk '{ print $13 }' $PDBID.pdbqt | sort -u | xargs)

# copy AD4.2_bound.dat in the same directory as grid.gpf
cp $SCRIPTDIR/AD4.1_bound.dat AD4.1_bound.dat

tee $PDBID.gpf << EOF
npts 60 60 60
parameter_file AD4.1_bound.dat

gridfld $PDBID.maps.fld
spacing 0.375
receptor_types $RECEPTOR_TYPES
ligand_types   $LIGAND_TYPES       
receptor $PDBID.pdbqt       
gridcenter 49.8363 17.6087 36.2723
smooth 0.5
EOF

# one map file per atom type in the ligands
for r in $LIGAND_TYPES; do
	echo "map $PDBID.$r.map" >> $PDBID.gpf
done

echo "
elecmap  $PDBID.e.map               # electrostatic potential map
dsolvmap $PDBID.d.map              # desolvation potential map
dielectric -0.1465                   # <0, AD4 distance-dep.diel;>0, constant
" >> $PDBID.gpf

# 3- Perform autogrid
$AUTOGRID -p $PDBID.gpf
