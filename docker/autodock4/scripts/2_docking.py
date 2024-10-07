#!/usr/bin/env python3

import os
import sys
import subprocess

def docking(pdbid, batch_label):
    """
    Perform docking using vina.
    
    Args:
        pdbid (str): PDB ID of the protein (e.g., 7jrn).
        batch_label (str): Batch label (e.g., TTT_A).
    
    Returns:
        None
    """
    # Path to vina executable
    VINA = "/autodock/vina"
    
    # Define the directory containing the PDBQT ligand files and output directory
    pdbqt_dir = batch_label
    output_dir = os.path.join(pdbqt_dir, "pdbqt_docked")

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # List all relevant PDBQT files in the batch-specific folder
    pdbqt_files = [f for f in os.listdir(pdbqt_dir) if f.endswith(".pdbqt")]
    
    if not pdbqt_files:
        print(f"Error: No PDBQT files found in folder '{pdbqt_dir}' for batch label '{batch_label}'.")
        sys.exit(1)

    # Build the vina command with the required arguments
    command = [
        VINA,
        "--batch", f"{pdbqt_dir}/*.pdbqt",
        "--maps", f"{pdbid}",
        "--scoring", "ad4",
        "--dir", output_dir
    ]

    # Run vina with the constructed command
    try:
        subprocess.run(" ".join(command), shell=True, check=True)
        print(f"Docking completed successfully. Results are in '{output_dir}'.")
    except subprocess.CalledProcessError as e:
        print(f"Error: Vina execution failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Ensure correct number of arguments
    if len(sys.argv) != 3:
        print("Usage: python docking.py <pdbid> <batch_label>")
        sys.exit(1)

    # Get arguments from command line
    pdbid = sys.argv[1]
    batch_label = sys.argv[2]

    # Call the docking function
    docking(pdbid, batch_label)
