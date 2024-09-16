#!/usr/bin/env python3

import os
import subprocess
import argparse
from Bio.PDB import PDBList, PDBParser, PDBIO, Select

# Define paths to MGLTools and AutoGrid executables
MGLTOOLS = "/autodock/mgltools"
AUTOGRID = "/autodock/autogrid4"  # Adjust if your AutoGrid executable path is different

# List of standard amino acids to identify and exclude ligands
STANDARD_AA = [
    'ALA', 'ARG', 'ASN', 'ASP', 'CYS', 'GLU',
    'GLN', 'GLY', 'HIS', 'ILE', 'LEU', 'LYS',
    'MET', 'PHE', 'PRO', 'SER', 'THR', 'TRP',
    'TYR', 'VAL'
]

# List of metal ions to remove from the receptor (excluding Zn)
METALS_AND_IONS = [
    'NA', 'MG', 'K', 'CA', 'MN', 'FE', 'CO',
    'NI', 'CU', 'MO', 'CD', 'W', 'AU', 'HG',
    'CL', 'BR', 'F', 'I', 'SO4', 'PO4', 'NO3', 'CO3'
]

def run_command(command):
    """Execute a shell command."""
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {command}")
        print(e)
        exit(1)

def download_protein(protein_id):
    """Download the protein PDB file."""
    pdbl = PDBList()
    pdbl.retrieve_pdb_file(protein_id, pdir='.', file_format='pdb')
    original_filename = f'pdb{protein_id.lower()}.ent'
    new_filename = f'{protein_id}.pdb'
    if os.path.exists(original_filename):
        os.rename(original_filename, new_filename)
        print(f"Downloaded and renamed protein PDB to {new_filename}")
    else:
        print(f"Failed to download {protein_id}.pdb")
        exit(1)

def fix_pdb_atom_names(pdb_file):
    """Fix atom names and element symbols in the PDB file."""
    corrected_lines = []
    with open(pdb_file, 'r') as infile:
        for line in infile:
            if line.startswith(('ATOM', 'HETATM')):
                # Extract atom name and element symbol
                atom_name = line[12:16].strip()
                element_symbol = line[76:78].strip()
                
                # Correct atom name alignment (left-justified in columns 13-16)
                if len(atom_name) < 4:
                    atom_name = atom_name.ljust(4)
                else:
                    atom_name = atom_name[:4]
                
                # Derive element symbol from atom name if missing or incorrect
                if not element_symbol or len(element_symbol) > 2 or not element_symbol.isalpha():
                    element_symbol = ''.join(filter(str.isalpha, atom_name)).strip().upper()
                    if len(element_symbol) > 2:
                        element_symbol = element_symbol[:2]
                
                # Reconstruct the line with corrected atom name and element symbol
                fixed_line = (
                    line[:12] + atom_name + line[16:76] +
                    f"{element_symbol:>2}" + line[78:]
                )
                corrected_lines.append(fixed_line)
            else:
                corrected_lines.append(line)
    
    with open(pdb_file, 'w') as outfile:
        outfile.writelines(corrected_lines)
    print(f"Fixed atom names and element symbols in {pdb_file}")

def remove_alt_loc_and_metals(pdb_file, output_file):
    """Remove alternate location indicators and metal ions from the PDB file."""
    with open(pdb_file, 'r') as infile, open(output_file, 'w') as outfile:
        for line in infile:
            if line.startswith(('ATOM', 'HETATM')):
                alt_loc = line[16]
                res_name = line[17:20].strip()
                element = line[76:78].strip()
                
                # Skip alternate locations that are not 'A' or ' '
                if alt_loc not in ('A', ' '):
                    continue
                
                # Skip metal ions (excluding Zn)
                if element.upper() in METALS_AND_IONS:
                    continue
                
                # Replace alternate location indicator with space
                fixed_line = line[:16] + ' ' + line[17:]
                outfile.write(fixed_line)
        print(f"Removed alternate locations and metals. Output saved to {output_file}")

def extract_receptor_atom_types(pdbqt_file):
    """Extract unique receptor atom types from the PDBQT file."""
    atom_types = set()
    with open(pdbqt_file, 'r') as f:
        for line in f:
            if line.startswith('ATOM') or line.startswith('HETATM'):
                parts = line.strip().split()
                if len(parts) < 10:
                    continue  # Malformed line
                atom_type = parts[-1]  # Last field is the atom type
                atom_types.add(atom_type)
    print(f"Extracted receptor atom types: {sorted(atom_types)}")
    return " ".join(sorted(atom_types))

def prepare_receptor(pdb_id):
    """Prepare the receptor PDBQT file using prepare_receptor4.py."""
    receptor_pdb = f"{pdb_id}.pdb"
    receptor_clean = f"{pdb_id}_clean.pdb"
    receptor_pdbqt = f"{pdb_id}.pdbqt"
    
    # Remove alternate locations and metal ions (excluding Zn)
    remove_alt_loc_and_metals(receptor_pdb, receptor_clean)
    
    # Fix atom names and element symbols
    fix_pdb_atom_names(receptor_clean)
    
    # Run prepare_receptor4.py
    prepare_script = f"{MGLTOOLS}/MGLToolsPckgs/AutoDockTools/Utilities24/prepare_receptor4.py"
    command = (
        f"LD_LIBRARY_PATH={MGLTOOLS}/lib {MGLTOOLS}/bin/python2.7 {prepare_script} "
        f"-r {receptor_clean} -o {receptor_pdbqt} -U nphs_lps_waters_nonstdres"
    )
    run_command(command)
    print(f"Prepared receptor PDBQT: {receptor_pdbqt}")

def prepare_gpf(pdb_id, receptor_types, grid_center):
    """Generate the GPF (Grid Parameter File) for AutoGrid."""
    gpf_file = f"{pdb_id}.gpf"
    receptor_pdbqt = f"{pdb_id}.pdbqt"
    
    # Define ligand_types as expected ligand atom types
    # Since you don't need ligand preparation, set to minimal or common types
    ligand_types = "C N S"  # Excluding 'O' as it causes issues
    
    with open(gpf_file, 'w') as f:
        f.write("npts 60 60 60\n")
        f.write("parameter_file AD4.1_bound.dat\n")
        f.write(f"gridfld {pdb_id}.maps.fld\n")
        f.write("spacing 0.375\n")
        f.write(f"receptor_types {receptor_types}\n")
        f.write(f"ligand_types   {ligand_types}\n")
        f.write(f"receptor {receptor_pdbqt}\n")
        f.write(f"gridcenter {grid_center[0]:.4f} {grid_center[1]:.4f} {grid_center[2]:.4f}\n")
        f.write("smooth 0.5\n")
        f.write(f"elecmap  {pdb_id}.e.map\n")
        f.write(f"dsolvmap {pdb_id}.d.map\n")
        f.write("dielectric -0.1465\n")
        
        # Define maps for each ligand atom type
        for atom_type in ligand_types.split():
            f.write(f"map {pdb_id}.{atom_type}.map\n")
    
    print(f"Generated GPF file: {gpf_file}")

def calculate_grid_center(pdbqt_file):
    """Calculate the center of mass of the receptor to set as the grid center."""
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure('receptor', pdbqt_file)
    atoms = list(structure.get_atoms())
    
    if not atoms:
        print(f"No atoms found in {pdbqt_file}. Cannot calculate grid center.")
        exit(1)
    
    center = [0.0, 0.0, 0.0]
    for atom in atoms:
        coord = atom.get_coord()
        center[0] += coord[0]
        center[1] += coord[1]
        center[2] += coord[2]
    
    center = [coord / len(atoms) for coord in center]
    print(f"Calculated grid center: {center}")
    return center

def run_autogrid(pdb_id):
    """Run AutoGrid using the generated GPF file."""
    gpf_file = f"{pdb_id}.gpf"
    command = f"{AUTOGRID} -p {gpf_file}"
    run_command(command)
    print("AutoGrid completed successfully.")

def main():
    """Main function to parse arguments and execute steps."""
    parser = argparse.ArgumentParser(description="Prepare protein (receptor) for AutoDock.")
    parser.add_argument("--protein_id", required=True, help="PDB ID of the protein (e.g., 7jrn).")
    
    args = parser.parse_args()
    pdb_id = args.protein_id.lower()
    
    # Step 1: Download the protein PDB file
    download_protein(pdb_id)
    
    # Step 2: Prepare the receptor
    prepare_receptor(pdb_id)
    
    # Step 3: Calculate grid center
    receptor_pdbqt = f"{pdb_id}.pdbqt"
    grid_center = calculate_grid_center(receptor_pdbqt)
    
    # Step 4: Extract receptor atom types
    receptor_types = extract_receptor_atom_types(receptor_pdbqt)
    
    # Step 5: Generate GPF file
    prepare_gpf(pdb_id, receptor_types, grid_center)
    
    # Step 6: Run AutoGrid
    run_autogrid(pdb_id)

if __name__ == "__main__":
    main()
