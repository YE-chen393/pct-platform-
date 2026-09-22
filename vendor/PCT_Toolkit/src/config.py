#

# Show pictures on the fly?
show = False

### VoidSize
# minimum radius of vacancy (Westlake) # TODO refine this with DFT?
radius_thr = 0

## Values to change if vacancy detection is not working properly
# intensity of global optimization of parameters of wykoff positions of vacancy sites 
tries = 3 # 8 is a reasonable value
# Minimum distance between two vacancy positions [Angstrom]
distance = 0.4 
# nearest neighbors to calculate the vacancy size (Normally Tetrahedral = 4, Octahedral = 8, but 4 works fine mostly)
n_NN = 4
bounds_interstitial = []
#bounds_interstitial = {'Vac3f': [], 'Vac4h': [[0.369,0.371]], 'Vac6m': [[0.136,0.138]], 'Vac12n': [[0.454,0.456],[0.116,0.118]], 'Vac12o': [[0.203,0.205],[0.353,0.355]]}
spheres_not_touching = False # True if vacancies must touch metal spheres


# number of metal atoms for supercell_size
n_metal_atoms = 12
# maximum hydrogen atoms (per supercell)
n_hydrogen = 32
# number of poscar files per hydrogen concentration
n_POSCAR = 20
# maximum number of interstitial sites found for constructing the .NN file
max_interstial = 10 # n_interstitials = max_interstial * n_metal_atoms
# Entropy of the disappearing gas phase
dS_H2 = 130 # J / molK