import numpy as np
from src.read import metallic_radii
import scipy.optimize as opt
from src.config import tries, n_NN, distance, radius_thr, bounds_interstitial, spheres_not_touching, max_interstial
from src.CONSTANTS import translation_vectors
import re
import copy

def optimize_radii(lattice_vectors, atoms):
    subfolder_name = "STEP1_metallic_radii" # to store pictures and csv
    # Prepare initial radii array
    unique_labels = list(set(atom.label for atom in atoms))
    label_to_idx = {label: idx for idx, label in enumerate(unique_labels)}
    initial_radii = np.array([metallic_radii.get(re.match(r'^[A-Za-z]+', label).group(), 1) for label in unique_labels])
    # Objective function: negative total volume (since we will minimize)
    def objective(radii):
        total_d = []
        for i in range(len(atoms)):
            for j in range(i+1, len(atoms)):
                ri = radii[label_to_idx[atoms[i].label]]
                rj = radii[label_to_idx[atoms[j].label]]
                dij = np.linalg.norm(np.dot(lattice_vectors.T, positions[i]) - np.dot(lattice_vectors.T, positions[j]))
                total_d.append(abs(dij - (ri + rj)))
        total_d_sorted = np.sort(total_d)
        # only the nearest neighbor
        sum_min8 = sum(total_d_sorted[:1])
        return sum_min8

    # Constraints: spheres do not overlap
    def constraint_generator(i, j, positions):
        def constraint(radii):
            ri = radii[label_to_idx[atoms[i].label]]
            rj = radii[label_to_idx[atoms[j].label]]
            dij = np.linalg.norm(np.dot(lattice_vectors.T, positions[i]) - np.dot(lattice_vectors.T, positions[j]))
            return dij - (ri + rj)
        return constraint

    # If initial values too big: decrease them!
    positions = np.array([atom.position for atom in atoms])
    constrain_result = -1
    initial_radii = initial_radii / 0.99
    while constrain_result < 0:
        initial_radii = initial_radii*0.99
        constrain_result = 0
        for i in range(len(atoms)):
            for j in range(i+1, len(atoms)):
                con = constraint_generator(i, j, positions)
                constrain_result = min(constrain_result, con(initial_radii))
    
    # Collect constraints
    constraints = []
    for i in range(len(atoms)):
        for j in range(i+1, len(atoms)):
            con = {'type': 'ineq', 'fun': constraint_generator(i, j, positions)}
            constraints.append(con)
    # Bounds: radii should be positive
    bounds = [(0.5*radius, 1.5*radius) for radius in initial_radii]

    # Optimization
    result = opt.minimize(objective, initial_radii, method='SLSQP', bounds=bounds, constraints=constraints)
    optimized_radii = result.x

    # Update radii in atoms
    for atom in atoms:
        idx = label_to_idx[atom.label]
        atom.radius = optimized_radii[idx]
    return atoms, result.fun


def optimize_interstitial(lattice_vectors, atoms, metal_count):
    subfolder_name = "STEP2_vacancy_size"
    metal_atoms = [atom for atom in atoms if not atom.label.startswith("Vac")]
    vac_atoms = [atom for atom in atoms if atom.label.startswith("Vac")]
    unique_vac_labels = list(set(atom.label for atom in vac_atoms))
    # Function to extract the sorting key
    def extract_sort_key(label):
        match = re.match(r"(Vac)(\d+)([a-zA-Z]+)", label)
        if match:
            return (int(match.group(2)), match.group(3))
        return (float('inf'), "")  # Handle cases where the format doesn't match
    # Sort labels
    sorted_vac_labels = sorted(unique_vac_labels, key=extract_sort_key)

    ### OBJECTIVE AND CONSTRAINT FUNCTION TO OPTIMIZE WYCKOFF PARAMETERS WHILE MAXIMIZING RADII OF VACANCIES
    # Objective function: negative total volume (since we will minimize)
    result_rows = []
    condensed_resultss = []
    FINISHED = False
    vac_count = 0
    for number, label in enumerate(sorted_vac_labels):
        if FINISHED:
            break
        unique_vac_atoms = [atom for atom in vac_atoms if atom.label == label]
        def objective(vars):
            total_sum = 0
            for vac_atom in unique_vac_atoms:
                r_vac, *position_parameter = vars
                # Create a dictionary to map x, y, z to the values in position_parameter
                position_values = {}
                pp_count = 0 # how many unique parameters exist (0-3)
                for letter in ["x", "y", "z"]:
                    if any(letter in str(coord) for coord in vac_atom.position):
                        position_values[letter] = position_parameter[pp_count]
                        pp_count += 1
                    else:
                        position_values[letter] = 0

                # Initialize the position_vac list by evaluating vac_atom.position, assuming it contains expressions like [2*x, x, 0.5]
                position_vac = []
                for coord in vac_atom.position:
                    try:
                        # Evaluate the position expression using the values of x, y, z
                        evaluated_value = eval(coord, {}, position_values)     
                        # If the evaluated position is greater than 1, subtract 1 (wrap using % 1)
                        position_vac.append(evaluated_value % 1)
                    except Exception as e:
                        raise ValueError(f"Error evaluating position expression {coord}: {e}")
                total_d = []
                position_vac = np.array(position_vac, dtype=float)
                for atom in metal_atoms:
                    r_metal = atom.radius
                    original_position = np.dot(lattice_vectors.T, atom.position)
                    # Calculate original distance (no translation)
                    dij_original = np.linalg.norm(original_position - np.dot(lattice_vectors.T, position_vac))
                    total_d.append(abs(dij_original - (r_metal + r_vac)))
                    # Try translating in different directions and check if it's closer
                    for translation in translation_vectors:
                        translated_position = original_position + np.dot(lattice_vectors.T, translation)
                        dij_translated = np.linalg.norm(translated_position - np.dot(lattice_vectors.T, position_vac))
                        # Append the closest distance (whether original or translated)
                        total_d.append(abs(dij_translated - (r_metal + r_vac)))

                total_d_sorted = np.sort(total_d)
                sum_min8 = sum(total_d_sorted[:n_NN])
                total_sum += sum_min8
            return sum_min8 - r_vac
        
        # Constraints: spheres do not overlap
        def constraint_generator():
            def constraint(vars):
                r_vac, *position_parameter = vars
                positions_vac = []
                for enum, vac_atom in enumerate(unique_vac_atoms):
                    # Create a dictionary to map x, y, z to the values in position_parameter
                    position_values = {}
                    pp_count = 0 # how many unique parameters exist (0-3)
                    for letter in ["x", "y", "z"]:
                        if any(letter in str(coord) for coord in vac_atom.position):
                            position_values[letter] = position_parameter[pp_count]
                            pp_count += 1
                        else:
                            position_values[letter] = 0
                    # Initialize the position_vac list by evaluating vac_atom.position, assuming it contains expressions like [2*x, x, 0.5]
                    position_vac = []
                    for coord in vac_atom.position:
                        try:
                            # Evaluate the position expression using the values of x, y, z
                            evaluated_value = eval(coord, {}, position_values)     
                            # If the evaluated position is greater than 1, subtract 1 (wrap using % 1)
                            position_vac.append(evaluated_value % 1)
                        except Exception as e:
                            raise ValueError(f"Error evaluating position expression {coord}: {e}")
                    position_vac = np.array(position_vac, dtype=float)
                    positions_vac.append(position_vac)
                # 2 Constraints: 
                     # 2. Positions of all vacs in this site must be unique
                for i, position_vac in enumerate(positions_vac):
                    for position_vac2 in positions_vac[i + 1:]:
                        if np.linalg.norm(np.dot(lattice_vectors.T, position_vac) - np.dot(lattice_vectors.T, position_vac2)) < distance:
                            return -1
                # 1. Sphere of metal atom must not overlap with any sphere of interstitial
                minimum_value = 0.1
                for metal_atom in metal_atoms:
                    # position of metal metal_atom
                    original_metal_atom_position = np.dot(lattice_vectors.T, metal_atom.position)
                    for position_vac in positions_vac:
                        # Calculate original distance (no translation)
                        dij_original = np.linalg.norm(original_metal_atom_position - np.dot(lattice_vectors.T, position_vac))
                        closest_dij = dij_original  # Start with the original distance
                        # Try translating in different directions and check if it's closer
                        for translation in translation_vectors:
                            translated_position = original_metal_atom_position + np.dot(lattice_vectors.T, translation)
                            dij_translated = np.linalg.norm(translated_position - np.dot(lattice_vectors.T, position_vac))
                            #if dij_translated - (metal_atom.radius + r_vac) < 0:
                            #    return -1
                            # If translated distance is closer, update the closest distance
                            if dij_translated < closest_dij:
                                closest_dij = dij_translated
                            minimum_value = min(minimum_value, closest_dij - (metal_atom.radius + r_vac))
                return minimum_value
            return constraint
        
        ### OPTIMIZE N (TRIES) TIMES TO GET THE BEST SOLUTION
        highest_radiuss = []
        lowest_funs = []
        save_result_xs = []
        pp_count = 0 # how many unique parameters exist (0-3)
        for letter in ["x", "y", "z"]:
            if any(letter in str(coord) for vac_atom in unique_vac_atoms for coord in vac_atom.position):
                pp_count += 1
        bound = [(radius_thr, 0.8)]
        if bounds_interstitial:
            bound.extend(bounds_interstitial[label])
        else:
            for _ in range(pp_count):
                bound.append((0, 0.96))
        tries_fitted = (1 if pp_count == 0 else (tries))
        wyckoff_number = label.removeprefix('Vac')
        for ith_try in range(tries_fitted):
            print_string = f"Position {wyckoff_number}: Try {ith_try + 1} / {tries_fitted}: "
            initial_params = np.array(np.random.rand() * (bound[0][1] - bound[0][0]) + bound[0][0])
            for i in range(pp_count):
                initial_params = np.append(initial_params, np.random.rand() * (bound[i + 1][1] - bound[i + 1][0]) + bound[i + 1][0])
            # Collect constraint
            constraint_fun = constraint_generator()
            constraint = {'type': 'ineq', 'fun': constraint_fun}
    
            result = opt.minimize(objective, initial_params, method='SLSQP', bounds=bound, constraints=constraint)             
            if spheres_not_touching and abs(result.x[0] + result.fun) > 1e-3:
                print(print_string + " Sphere not touching!")
                continue
            elif constraint_fun(result.x) < 0:
                print(print_string + " Constraint not fullfilled after optimization!")
                continue
            print(print_string + f" Distance: {result.fun}, Radius: {result.x[0]}, Wyckoff parameters: {result.x[1:] if len(result.x) > 1 else 'N/A'}")           
            radius, *position_parameter = result.x
            lowest_funs.append(result.fun)
            highest_radiuss.append(radius)
            save_result_xs.append(result.x)

        ### SORT OUT OVERLAPPING RESULTS
        # Convert only NumPy arrays to lists, leave Python lists as they are
        lowest_funs_list = lowest_funs if isinstance(lowest_funs, list) else lowest_funs.tolist()
        if not lowest_funs_list:
            continue
        # Define a tolerance for small `lowest_funs` values
        tolerance = 1e-6
        # Sort by `lowest_funs_list`, and for values within tolerance, sort by `highest_radiuss`
        sorted_arrays = sorted(zip(lowest_funs_list, highest_radiuss, save_result_xs), 
                               key=lambda x: (x[0] if x[0] > tolerance else 0, -x[1]))
        # Unzip the sorted result
        lowest_funs_sorted, highest_radiuss_sorted, save_result_xs_sorted = zip(*sorted_arrays)
        # Convert the sorted tuples back into lists (since zip() returns tuples)
        lowest_funs_sorted = list(lowest_funs_sorted)
        highest_radiuss_sorted = list(highest_radiuss_sorted)
        save_result_xs_sorted = list(save_result_xs_sorted)

        def save_result(save_resultx, unique_vac_atoms, condensed_results, result_rows, result_fun, original_atoms, mult, modify_original=False, only_positions = False):
            positions = []
            radius, *position_parameter = save_resultx
            result_row = []

            for enum, vac_atom in enumerate(unique_vac_atoms):
                positions.append([])
                # Check if we should modify the original or create a copy
                if modify_original:
                    vac_atom_to_modify = vac_atom  # Modify the original vac_atom
                else:
                    vac_atom_to_modify = copy.deepcopy(vac_atom)  # Create a deep copy

                position_values = {}
                pp_count = 0 # how many unique parameters exist (0-3)
                for letter in ["x", "y", "z"]:
                    if any(letter in str(coord) for coord in vac_atom_to_modify.position):
                        position_values[letter] = position_parameter[pp_count]
                        pp_count += 1
                    else:
                        position_values[letter] = 0

                position = []
                for coord in vac_atom_to_modify.position:
                    try:
                        # Evaluate the position expression using the values of x, y, z
                        evaluated_value = eval(coord, {}, position_values)     
                        # If the evaluated position is greater than 1, subtract 1 (wrap using % 1)
                        position.append(evaluated_value % 1)
                    except Exception as e:
                        raise ValueError(f"Error evaluating position expression {coord}: {e}")
                positions[enum].append(position)
                # Set the radius
                vac_atom_to_modify.radius = radius



                # Update the position of the vac_atom (either original or copy)
                vac_atom_to_modify.position = position
                vac_atom_to_modify.label += (f"_{mult}")
                # If we are not modifying the original, append the copy to the original_atoms array
                if not modify_original and not only_positions:
                    original_atoms.append(vac_atom_to_modify)

                # Save the result for this row
                result_row.append(result_fun)
            if only_positions:
                return positions
            condensed_results[-1].insert(0, vac_atom_to_modify.label)
            # Append the result row to the result_rows
            result_rows.append(result_row)

            return result_rows, original_atoms, condensed_results, positions
        
        # Convert the result back to lists if needed
        lowest_funs_sorted = list(lowest_funs_sorted)
        highest_radiuss_sorted = list(highest_radiuss_sorted)
        save_result_xs_sorted = list(save_result_xs_sorted)

        saved_result_xs = []
        unique_vac_atoms_deepcopy = copy.deepcopy(unique_vac_atoms)  # Create a deep copy
        condensed_results = []
        positions_saved = []
        # Manually check which sites should be included# Find first number sequence in the string
        match = re.search(r'\d+', label)
        if match:
            multiplicity = int(match.group())  # Convert to integer
        for i in range(len(lowest_funs_sorted)):
            if len(saved_result_xs) == 0:
                condensed_results.append(save_result_xs_sorted[i].tolist())
                result_rows, atoms, condensed_results, positions = save_result(save_result_xs_sorted[i], unique_vac_atoms, condensed_results, result_rows, lowest_funs_sorted[i], atoms, len(saved_result_xs), modify_original=True)
                positions_saved.append(positions)
                saved_result_xs.append(save_result_xs_sorted[i])
                print("Saved first result: ", save_result_xs_sorted[i])
                vac_count += multiplicity
            elif highest_radiuss_sorted[i] > radius_thr and len(save_result_xs_sorted[i]) > 1:
                ANY_SAVED_RESULT_IS_SAME = False
                positions_new = save_result(save_result_xs_sorted[i], unique_vac_atoms_deepcopy, condensed_results, result_rows, lowest_funs_sorted[i], atoms, len(saved_result_xs), modify_original=False, only_positions=True)
                for positions in positions_saved:
                    if ANY_SAVED_RESULT_IS_SAME:
                        break
                    # it has to be different from every position (but only in one of the position vectors)
                    positions = np.array(positions)
                    positions_new = np.array(positions_new)
                    for distance_vectors in np.linalg.norm(np.dot(positions[:, np.newaxis], lattice_vectors) - np.dot(positions_new, lattice_vectors), axis=2):
                        if ANY_SAVED_RESULT_IS_SAME:
                            break
                        for distance_vector in distance_vectors:
                            if (np.linalg.norm(distance_vector) < distance):
                                ANY_SAVED_RESULT_IS_SAME = True
                                break
                if ANY_SAVED_RESULT_IS_SAME:
                    continue
                condensed_results.append(save_result_xs_sorted[i].tolist())
                result_rows, atoms, condensed_results, positions = save_result(save_result_xs_sorted[i], unique_vac_atoms_deepcopy, condensed_results, result_rows, lowest_funs_sorted[i], atoms, len(saved_result_xs), modify_original=False)
                positions_saved.append(positions)
                saved_result_xs.append(save_result_xs_sorted[i])
                print("Saved next result: ", save_result_xs_sorted[i])
                vac_count += multiplicity
            if vac_count >= max_interstial * metal_count:
                FINISHED = True
                break
        condensed_resultss.append(condensed_results)
    return atoms
