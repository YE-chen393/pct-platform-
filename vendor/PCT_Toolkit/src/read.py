
import re
import numpy as np
import time
from MongoDB.connect import collection_calculation, collection_system, db

# Constants
metallic_radii = { 
    'AL': 1.43,
    'CR': 1.28, 
    'FE': 1.26,
    'LA': 1.87,
    'MN': 1.27,
    'NB': 1.46,
    'NI': 1.24, 
    'SN': 1.50, 
    'TI': 1.47,
    'VV': 1.34,
    # Add more elements and their metallic radii in meters as needed
}

class Atom:
    def __init__(self, element, position, label, optimized_metallic_radii = None):
        self.element = element
        self.position = position
        self.label = label
        self.n_nearest_neighbors = None  # Initialize the attribute

        if self.element in ["Vac", "H", "Va"]:
            self.radius = 0.4
        elif optimized_metallic_radii:
            self.radius = optimized_metallic_radii.get(label)
        else:
            element = element.upper()
            self.radius = metallic_radii.get(re.findall(r'^[A-Za-z]+', element)[0], 0.1)  # default radius if not found
        if self.radius == 0.1:
            print(f"Attention, metallic radius of {self.element} not defined #############################################################################################")
            time.sleep(0.2)

def read_poscar(poscar_path, optimized_metallic_radii = None, VACS=False, file_type = 'hydride'):    
    with open(poscar_path, 'r') as f:
        lines = f.readlines()
    scale = float(lines[1].strip())
    lattice_vectors = np.array([list(map(float, lines[i].split())) for i in range(2, 5)]) * scale
    counts = list(map(int, lines[6].split()))
    positions = []
    positions_Vac = []
    atom_labels = []
    idx = 8
    total_atoms = sum(counts)
    for _ in range(total_atoms):
        VAC =  False
        parts = lines[idx].split()
        if len(parts) > 3:
            label = parts[3] 
        else:
            raise ValueError("!!!NO ELEMENT DESCRIPTOR AFTER ATOM POSITION!!!")

        pos = []
        if "Vac" in label:
            if not VACS:
                break
            VAC = True

        # Check if a part contains a variable expression like '2*x' or just a number
        for part in parts[:3]:
            if VAC:
                pos.append(str(part))
            else:
                pos.append(float(part))

        if VAC:
            positions_Vac.append(pos)
        else:
            positions.append(pos)
        atom_labels.append(label)
        idx += 1

    # Adjust positions if necessary
    positions = np.array(positions)
    #if coord_type.startswith('d'):  # direct coordinates
    #    positions = positions @ lattice_vectors  # convert to cartesian

    atoms = []
    count_normal = 0
    count_Vac = 0        
    for i, label in enumerate(atom_labels):
        # Extract element symbol from label
        if label is not None:
            element = re.match(r'^[A-Za-z]+', label).group()
        if "Vac" in element:
            pos = positions_Vac[count_Vac]
            count_Vac += 1
        else:
            pos = positions[count_normal]
            count_normal += 1
        atom = Atom(element, pos, label, optimized_metallic_radii)
        atoms.append(atom)

    return lattice_vectors, atoms

def write_NN(hydride_file, atoms):
    lines = re.findall(r".*?\n", hydride_file)  # Keeps \n at the end of each line
    # Remove the last number from the string
    lines[6] = re.sub(r'\s*\d+\s*$', '', lines[6])
    final_string_list = lines[:8]
    # number of vacs:
    n_vacs = 0
    for atom in atoms:
        if 'Vac' in atom.label and '_' in atom.label:
            n_vacs += 1
    final_string_list[6] += ' ' + str(n_vacs) + '\n'
    for atom in atoms:
        string = " "
        for position in atom.position:
            string += str(position) + " "
        string += atom.label + '\n'
        if 'Vac' not in atom.label:
            final_string_list.append(string)
        if 'Vac' in atom.label and '_' in atom.label:
            final_string_list.append(string)    
    final_string = ""
    for string in final_string_list:
        final_string += string
    return final_string

def change_poscar(poscar_path, wyckoffs):
    with open(poscar_path, 'r') as f:
        lines = f.readlines()
    wyckoff_set = list(set(wyckoffs))
    wyckoff_dict = {}
    for w in wyckoff_set: 
        wyckoff_dict[w] = wyckoffs.count(w)
    for i, w in enumerate(wyckoffs):
        lines[8 + i] = lines[8 + i].strip() + f"{wyckoff_dict[w]}{w}\n"
    with open(poscar_path, 'w') as f:
        for string in lines:
            f.write(string)

def write_hydride(wyckoff_positions, poscar_path):
    with open(poscar_path, 'r') as f:
        lines = f.readlines()
    vac_count = 0
    metal_count = sum([int(c) for c in lines[6].strip().split()])
    for wyckoff_position in wyckoff_positions:
        #if wyckoff_position["multiplicity"] > 33:
        #    continue
        for position in wyckoff_position["positions"]:
            line = f' {position.replace("(", "").replace(")", "").replace(",", " ")} Vac{wyckoff_position["multiplicity"]}{wyckoff_position["letter"]}\n'
            lines.append(line)
        vac_count += wyckoff_position["multiplicity"]
    if vac_count != 0:
        lines[5] = lines[5].strip() + f" Vac\n"
        lines[6] = lines[6].strip() + f" {vac_count}\n"
    final_string = ""
    for string in lines:
        final_string += string
    return final_string, metal_count

def read_poscar_name(name, optimized_metallic_radii = None, VACS=False, file_type = 'poscar', STRING=False, elements=None, configuration=None, metal_ratio=None):    
    if STRING:
        lines = name.splitlines()
    else:
        system = collection_system.find_one({'system': name})
        if file_type == 'poscar':
            lines = system["poscar"].splitlines()
        else:
            lines = system["NN"].splitlines()
    if configuration:
        lines_configuration = configuration.splitlines()
        counts = list(map(int, lines_configuration[6].split()[:-1]))
        total_atoms = sum(counts)
        for idx in range(total_atoms + 8):
            if idx == 5 or idx == 6:
                parts = lines[idx].split()
                parts_conf = lines_configuration[idx].split()
                parts_new = parts_conf[:-1].append(parts[-1])
                lines[idx] = (' ').join(parts_new)
                continue
            lines[idx] = lines_configuration[idx]
    elif elements and not metal_ratio:
        lines_5 = lines[5].split()
        lines_6 = lines[6].split()
        idx = 8
        for ith_element, element in enumerate(elements):
            if elements[ith_element][0] not in ['H', 'Va']:
                lines_5[ith_element] = elements[ith_element][0]
            for _ in range(int(lines_6[ith_element])):
                if elements[ith_element][0] not in ['H', 'Va']:
                    parts = lines[idx].split()
                    parts[-1] = elements[ith_element][0]
                    lines[idx] = (' ').join(parts)
                idx += 1
        lines[5] = (' ').join(lines_5)
        # change the elements in the atomic positions
    scale = float(lines[1].strip())
    lattice_vectors = np.array([list(map(float, lines[i].split())) for i in range(2, 5)]) * scale
    counts = list(map(int, lines[6].split()))
    positions = []
    positions_Vac = []
    atom_labels = []
    idx = 8
    total_atoms = sum(counts)
    for _ in range(total_atoms):
        VAC =  False
        parts = lines[idx].split()
        if len(parts) > 3:
            label = parts[3] 
        else:
            raise ValueError("!!!NO ELEMENT DESCRIPTOR AFTER ATOM POSITION!!!")

        pos = []
        if "Vac" in label:
            if not VACS:
                break
            VAC = True

        # Check if a part contains a variable expression like '2*x' or just a number
        for part in parts[:3]:
            if VAC:
                pos.append(str(part))
            else:
                pos.append(float(part))

        if VAC:
            positions_Vac.append(pos)
        else:
            positions.append(pos)
        atom_labels.append(label)
        idx += 1

    # Adjust positions if necessary
    positions = np.array(positions)
    #if coord_type.startswith('d'):  # direct coordinates
    #    positions = positions @ lattice_vectors  # convert to cartesian

    atoms = []
    count_normal = 0
    count_Vac = 0        
    for i, label in enumerate(atom_labels):
        # Extract element symbol from label
        if label is not None:
            element = re.match(r'^[A-Za-z]+', label).group()
        if "Vac" in element:
            pos = positions_Vac[count_Vac]
            count_Vac += 1
        else:
            pos = positions[count_normal]
            count_normal += 1
        atom = Atom(element, pos, label, optimized_metallic_radii)
        atoms.append(atom)
    if metal_ratio:
        for ith_sl, element in enumerate(elements):
            if len(element) == 2:
                mixing_sl = ith_sl
        sl = 0
        atom_label_save = atoms[0].label
        total_metal_atoms = sum(counts[:-1])
        atoms_already = 0
        atoms_already_total = 0
        for atom in atoms:
            if atom.label != atom_label_save:
                atom_label_save = atom.label
                sl += 1
            if sl == mixing_sl:
                if atoms_already >= total_metal_atoms * metal_ratio:
                    atom.label = elements[sl][1]
                elif total_metal_atoms - atoms_already_total <= total_metal_atoms * metal_ratio:
                    atom.label = elements[sl][0]
                else:
                    if np.random.random() > metal_ratio:
                       atom.label = elements[sl][1] 
                    else:
                       atom.label = elements[sl][0] 
                atoms_already_total += 1
        # Custom sorting function
        sorted_atoms = sorted(atoms, key=lambda atom: (atom.label.startswith("Vac"), atom.label))            

        return lattice_vectors, sorted_atoms
    return lattice_vectors, atoms
    

    