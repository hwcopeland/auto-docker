#!/usr/bin/env python3

import os
import subprocess
import argparse
from Bio.PDB import PDBParser

# Define paths to MGLTools and AutoGrid executables
MGLTOOLS = "/autodock/mgltools"
AUTOGRID = "/autodock/autogrid4"  # Adjust if your AutoGrid executable path is different

def run_command(command): # This works good
    """Execute a shell command."""
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {command}")
        print(e)
        exit(1)

def download_protein(protein_id): 
    """Download the protein PDB file using wget."""
    filename = f'{protein_id}.pdb'
    url = f'https://files.rcsb.org/download/{filename}'  
    try:
        subprocess.run(['wget', url], check=True)
        if os.path.exists(filename):
            print(f"Downloaded and renamed protein PDB to {filename}")
        else:
            print(f"Failed to download {protein_id}.pdb")
            exit(2)  # Use a different exit code
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while downloading {protein_id}: {e}")
        exit(3)  # Use a different exit code

def prepare_receptor(pdb_id): 
    """Prepare the receptor PDBQT file using prepare_receptor4.py."""
    receptor_pdb = f"{pdb_id}.pdb"
    receptor_pdbqt = f"{pdb_id}.pdbqt"

    if os.path.exists(receptor_pdbqt):
        print(f"Receptor PDBQT file already exists: {receptor_pdbqt}")
        return  # Skip preparation if file exists

    prepare_script = f"{MGLTOOLS}/MGLToolsPckgs/AutoDockTools/Utilities24/prepare_receptor4.py"
    command = (
        f"LD_LIBRARY_PATH={MGLTOOLS}/lib {MGLTOOLS}/bin/python2.7 {prepare_script} "
        f"-r {receptor_pdb} -o {receptor_pdbqt} -U nphs_lps_waters_nonstdres"
    )
    run_command(command)
    print(f"Prepared receptor PDBQT: {receptor_pdbqt}")

def calculate_grid_center(pdbqt_file, ligand_id): 
    """Calculate the center of mass of the native ligand specified by ligand_id."""
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure('receptor', pdbqt_file)
    
    ligand_atoms = []
    
    for model in structure:
        for chain in model:
            for residue in chain:
                if residue.get_resname() == ligand_id:
                    ligand_atoms.extend(residue.get_atoms())
    
    if not ligand_atoms:
        print(f"No atoms found for ligand ID '{ligand_id}' in {pdbqt_file}. Cannot calculate grid center.")
        exit(1)

    # Calculate the center of the ligand
    center = [0.0, 0.0, 0.0]
    for atom in ligand_atoms:
        coord = atom.get_coord()
        center[0] += coord[0]
        center[1] += coord[1]
        center[2] += coord[2]

    center = [coord / len(ligand_atoms) for coord in center]
    print(f"Calculated grid center for ligand '{ligand_id}': {center}")

    # Save the center to a file
    with open('grid_center.txt', 'w') as f:
        f.write(f"{center[0]} {center[1]} {center[2]}\n")

    return center




def main():
    """Main function to parse arguments and execute steps."""
    parser = argparse.ArgumentParser(description="Prepare protein (receptor) for AutoDock4.")
    parser.add_argument("--protein_id", required=True, help="PDB ID of the protein (e.g., 7jrn).")
    parser.add_argument("--ligand_id", required=True, help="ID of the native ligand (e.g., LIG).")

    args = parser.parse_args()

    # Check if required arguments are provided
    if not args.protein_id or not args.ligand_id:
        logging.error("Missing required arguments: --protein_id and --ligand_id are required.")
        print("Error: Missing required arguments. Use --help for usage information.")
        exit(1)

    pdb_id = args.protein_id.lower()

    # Step 1: Download the protein PDB file
    download_protein(pdb_id)

    # Step 2: Prepare the receptor
    prepare_receptor(pdb_id)

    # Step 3: Calculate Native Ligand center
    receptor_pdbqt = f"{pdb_id}.pdbqt"
    grid_center = calculate_grid_center(receptor_pdbqt, args.ligand_id)

if __name__ == "__main__":
    main()