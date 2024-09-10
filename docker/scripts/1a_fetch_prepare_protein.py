import os
import shutil
from Bio.PDB import PDBList

#env
MGLTOOLS=/autodock/mgltools
AUTOGRID=/autodock/./autogrid4

# Const
standard_aa = ['ALA', 'ARG', 'ASN', 'ASP', 'CYS', 'GLU', 'GLN', 'GLY', 'HIS', 'ILE', 'LEU', 'LYS', 'MET', 'PHE', 'PRO', 'SER', 'THR', 'TRP', 'TYR', 'VAL']
metals_and_ions = ['NA', 'MG', 'K', 'CA', 'MN', 'FE', 'CO', 'NI', 'CU', 'ZN', 'MO', 'CD', 'W', 'AU', 'HG', 'CL', 'BR', 'F', 'I', 'SO4', 'PO4', 'NO3', 'CO3']


def download_protein(protein):
    pdbl = PDBList()
    pdbl.retrieve_pdb_file(protein, pdir='./Protein/', file_format='pdb')
    os.rename(f'pdb{protein.lower()}.ent', f'{protein}.pdb')

def get_ligand_residues(structure):
    ligand_residues = []
    for model in structure:
        for chain in model:
            ligand_residues.extend((chain, res) for res in chain if res.get_resname() not in standard_aa and res.get_resname() != "HOH")
    return ligand_residues

def write_ligands_to_files(ligand_residues, output_dir, metals_and_ions_dir, metals_and_ions):
    for chain, ligand in ligand_residues:
        io = PDBIO()
        s = Structure.Structure('Ligand')
        m = Model.Model(0)
        s.add(m)
        c = Chain.Chain(chain.id)
        m.add(c)
        c.add(ligand.copy())
        io.set_structure(s)
        filename = f'ligand_{ligand.get_resname()}.pdb'
        if ligand.get_resname() in metals_and_ions:
            io.save(os.path.join(metals_and_ions_dir, filename))
        else:
            io.save(os.path.join(output_dir, filename))

def prepare_receptor(protein):
    os.system(f"prepare_receptor -r {protein}_clean.pdb -o {protein}_clean.pdbqt -v -A hydrogens")
    