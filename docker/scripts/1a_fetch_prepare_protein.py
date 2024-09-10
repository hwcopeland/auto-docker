import os
import subprocess
import argparse
from Bio.PDB import PDBList, PDBParser, PDBIO, Structure, Model, Chain

MGLTOOLS = "/autodock/mgltools"
AUTOGRID = "/autodock/./autogrid4"

standard_aa = ['ALA', 'ARG', 'ASN', 'ASP', 'CYS', 'GLU', 'GLN', 'GLY', 'HIS', 'ILE', 'LEU', 'LYS', 'MET', 'PHE', 'PRO', 'SER', 'THR', 'TRP', 'TYR', 'VAL']
metals_and_ions = ['NA', 'MG', 'K', 'CA', 'MN', 'FE', 'CO', 'NI', 'CU', 'ZN', 'MO', 'CD', 'W', 'AU', 'HG', 'CL', 'BR', 'F', 'I', 'SO4', 'PO4', 'NO3', 'CO3']

# Function to run shell commands
def run_command(command):
    subprocess.run(command, shell=True, check=True)

# Download and save the protein file
def download_protein(protein):
    pdbl = PDBList()
    pdbl.retrieve_pdb_file(protein, pdir='.', file_format='pdb')
    os.rename(f'pdb{protein.lower()}.ent', f'{protein}.pdb')

# Extract ligands directly in the current dir
def extract_ligands(protein_file):
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure('protein', protein_file)
    
    ligand_residues = []
    for model in structure:
        for chain in model:
            for res in chain:
                if res.get_resname() not in standard_aa and res.get_resname() != "HOH":
                    ligand_residues.append((chain, res))
    
    io = PDBIO()
    for chain, ligand in ligand_residues:
        ligand_structure = Structure.Structure('Ligand')
        model = Model.Model(0)
        chain_copy = Chain.Chain(chain.id)
        model.add(chain_copy)
        chain_copy.add(ligand.copy())
        ligand_structure.add(model)
        
        io.set_structure(ligand_structure)
        ligand_filename = f'ligand_{ligand.get_resname()}_{chain.id}.pdb'
        io.save(ligand_filename)

# Find the native ligand
def find_native_ligand(native_ligand):
    ligand_file = None
    for file in os.listdir('.'):
        if native_ligand in file and file.startswith(f'ligand_{native_ligand}'):
            ligand_file = file
            break
    if not ligand_file:
        raise ValueError(f"Native ligand {native_ligand} not found.")
    return ligand_file

# Calculate the grid center based on the native ligand
def calculate_grid_center(ligand_file):
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure('ligand', ligand_file)
    atoms = list(structure.get_atoms())
    
    center_of_mass = [0.0, 0.0, 0.0]
    for atom in atoms:
        pos = atom.get_coord()
        center_of_mass[0] += pos[0]
        center_of_mass[1] += pos[1]
        center_of_mass[2] += pos[2]
    
    center_of_mass = [coord / len(atoms) for coord in center_of_mass]
    return center_of_mass

# Prepare the GPF file
def prepare_gpf(pdb_id, receptor_types, ligand_types, grid_center):
    gpf_file = f"{pdb_id}.gpf"
    with open(gpf_file, 'w') as f:
        f.write(f"npts 60 60 60\n")
        f.write("parameter_file AD4.1_bound.dat\n")
        f.write(f"gridfld {pdb_id}.maps.fld\n")
        f.write("spacing 0.375\n")
        f.write(f"receptor_types {receptor_types}\n")
        f.write(f"ligand_types   {ligand_types}\n")
        f.write(f"receptor {pdb_id}.pdbqt\n")
        f.write(f"gridcenter {grid_center[0]:.4f} {grid_center[1]:.4f} {grid_center[2]:.4f}\n")
        f.write("smooth 0.5\n")
        f.write("elecmap  {pdb_id}.e.map\n")
        f.write("dsolvmap {pdb_id}.d.map\n")
        f.write("dielectric -0.1465\n")

    for ligand_type in ligand_types.split():
        with open(gpf_file, 'a') as f:
            f.write(f"map {pdb_id}.{ligand_type}.map\n")

# Prepare the receptor
def prepare_receptor(pdb_id):
    receptor_pdb = f"{pdb_id}.pdb"
    receptor_pdbqt = f"{pdb_id}.pdbqt"
    prepare_script = f"{MGLTOOLS}/MGLToolsPckgs/AutoDockTools/Utilities24/prepare_receptor4.py"
    run_command(f"LD_LIBRARY_PATH={MGLTOOLS}/lib {MGLTOOLS}/bin/python2.7 {prepare_script} -r {receptor_pdb} -o {receptor_pdbqt}")

# Run autogrid
def run_autogrid(pdb_id):
    gpf_file = f"{pdb_id}.gpf"
    run_command(f"{AUTOGRID} -p {gpf_file}")

# Main function to handle command line inputs
def main():
    parser = argparse.ArgumentParser(description="Prepare receptor and ligands for AutoDock.")
    parser.add_argument("--protein_id", required=True, help="PDB ID of the protein.")
    parser.add_argument("--native_ligand", required=True, help="Name of the native ligand.")
    
    args = parser.parse_args()

    # Step 1: Download protein (to current dir)
    download_protein(args.protein_id)

    # Step 2: Extract ligands (to current dir)
    extract_ligands(f"{args.protein_id}.pdb")

    # Step 3: Find the native ligand
    ligand_file = find_native_ligand(args.native_ligand)

    # Step 4: Calculate the grid center based on the native ligand
    grid_center = calculate_grid_center(ligand_file)

    # Step 5: Prepare receptor (PDB to PDBQT conversion)
    prepare_receptor(args.protein_id)

    # Step 6: Prepare GPF with correct grid center
    prepare_gpf(args.protein_id, "A C HD N OA P", "A C HD N OA P NA", grid_center)

    # Step 7: Run autogrid
    run_autogrid(args.protein_id)

if __name__ == "__main__":
    main()