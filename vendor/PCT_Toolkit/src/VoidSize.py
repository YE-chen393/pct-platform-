from src.read import read_poscar, write_NN, write_hydride, read_poscar_name
from src.optimize import optimize_radii, optimize_interstitial

def void_size(poscar_path, wyckoff_positions):
    ### STEP 1: Optimize radii of metal spheres to prepare STEP 2 (calculation of vacancy sizes)
    print("STEP 1: Optimize radii of metal spheres ...")
    lattice_vectors, atoms = read_poscar(poscar_path)
    ### Perform optimization with iterations
    atoms_sizes = [[] for _ in atoms]
    atoms, result_fun = optimize_radii(lattice_vectors, atoms)
    for num, atom in enumerate(atoms):
        atoms_sizes[num].append(atom.radius)
    # Output optimized radii
    unique_optimized_metallic_radii = {}
    for atom in atoms:
        unique_optimized_metallic_radii[atom.label] = atom.radius
    
    ### STEP 2: Optimize vacancy sizes
    print("STEP2: optimization of vacancy sites")
    # TODO create hydride file with wyckoff_information
    hydride_file, metal_count = write_hydride(wyckoff_positions, poscar_path)
    lattice_vectors, atoms = read_poscar_name(hydride_file, unique_optimized_metallic_radii, VACS=True, STRING=True)
    atoms = optimize_interstitial(lattice_vectors, atoms, metal_count)
    ### STEP 3: write NN file
    NN_string = write_NN(hydride_file, atoms)
    return NN_string
