#!/usr/bin/env python3

import argparse
import os
import sys
import subprocess
import concurrent.futures
import tempfile
from rdkit import Chem

def parse_args():
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Prepare ligands for AutoDock.")
    parser.add_argument("pdbid", type=str, help="PDB ID of the protein (e.g., 7jrn).")
    parser.add_argument("batch_label", type=str, help="Batch label (e.g., TTT_A).")
    return parser.parse_args()

def convert_sdf_to_pdbqt(mol, output_dir, batch_label, index):
    """
    Convert a single molecule from SDF to PDBQT using Open Babel.
    
    Parameters:
    - mol: RDKit molecule object.
    - output_dir: Directory to save the converted PDBQT files.
    - batch_label: Label for the batch.
    - index: Unique index for naming.
    """
    try:
        # Check if the molecule has at least one conformer
        if mol.GetNumConformers() == 0:
            # Generate a conformer if none exist
            from rdkit.Chem import AllChem
            AllChem.EmbedMolecule(mol)

        # Write molecule to a temporary SDF file with only the first conformation
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.sdf') as tmp_sdf:
            mol_block = Chem.MolToMolBlock(mol, confId=0)
            tmp_sdf.write(mol_block)
            tmp_sdf_path = tmp_sdf.name

        # Define output PDBQT filename in the batch-specific folder
        output_pdbqt = os.path.join(output_dir, f"{batch_label}_{index}.pdbqt")

        # Run Open Babel to convert SDF to PDBQT
        command = [
            'obabel',
            tmp_sdf_path,
            '-O',
            output_pdbqt,
            '-p', '7',      # Protonation state; adjust as needed
            '-ff', 'GAFF'    # Force field; adjust as needed
        ]

        # Execute the command
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Successfully converted molecule {index} to {output_pdbqt}")

        # Remove 'MODEL' and 'ENDMDL' lines from the output PDBQT file
        with open(output_pdbqt, 'r') as f:
            lines = f.readlines()

        with open(output_pdbqt, 'w') as f:
            for line in lines:
                if not (line.startswith('MODEL') or line.startswith('ENDMDL')):
                    f.write(line)

    except subprocess.CalledProcessError as e:
        print(f"Error converting molecule {index} to PDBQT:")
        print(e.stderr.decode())
    finally:
        # Clean up temporary file
        os.remove(tmp_sdf_path)

def main():
    # Parse arguments
    args = parse_args()
    pdbid = args.pdbid.lower()
    batch_label = args.batch_label
    filelist = f"filelist_{batch_label}"

    sdf_filename = f"{batch_label}.sdf"
    
    # Check if SDF file exists
    if not os.path.isfile(sdf_filename):
        print(f"Error: SDF file '{sdf_filename}' not found.")
        sys.exit(1)
    
    # Create output directory for the batch if it doesn't exist
    output_dir = batch_label
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Read molecules from SDF using RDKit
    suppl = Chem.SDMolSupplier(sdf_filename, removeHs=False)
    molecules = [mol for mol in suppl if mol is not None]
    
    if not molecules:
        print(f"Error: No valid molecules found in '{sdf_filename}'.")
        sys.exit(1)
    
    print(f"Found {len(molecules)} molecules in '{sdf_filename}'. Starting conversion...")

    # Convert molecules in parallel using ProcessPoolExecutor
    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = []
        for index, mol in enumerate(molecules, start=1):
            futures.append(executor.submit(convert_sdf_to_pdbqt, mol, output_dir, batch_label, index))
        
        # Optional: Wait for all futures to complete
        for future in concurrent.futures.as_completed(futures):
            # This will re-raise any exceptions caught in the worker processes
            future.result()
    
    # Generate the filelist
    with open(filelist, 'w') as fl:
        fl.write(f"{pdbid}.maps.fld\n")
        for index in range(1, len(molecules) + 1):
            pdbqt_file = os.path.join(output_dir, f"{batch_label}_{index}.pdbqt")
            fl.write(f"{pdbqt_file}\n")
    
    print(f"Filelist '{filelist}' created successfully.")

if __name__ == "__main__":
    main()
