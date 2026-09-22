AVOGADRO = 6.02214086e23
EV_TO_KJ = 1.60218e-22

metallic_radii_dict = {
    'ac': 186,
    'al': 143,
    'am': 173,
    'ba': 222,
    'be': 112,
    'bk': 170,
    'cd': 151,
    'cs': 265,
    'ca': 197,
    'cf': 186,
    'ce': 181.8,
    'cr': 128,
    'co': 125,
    'cu': 128,
    'cm': 174,
    'dy': 178.1,
    'er': 176.1,
    'eu': 180.4,
    'fm': None,
    'ga': 135,
    'gd': 180.4,
    'h': 32,
    'hf': 159,
    'hg': 151,
    'ho': 176.2,
    'in': 167,
    'ir': 135.5,
    'fe': 126,
    'la': 187,
    'li': 152,
    'lu': 173.8,
    'mg': 160,
    'mn': 127,
    'mo': 139,
    'nd': 181.4,
    'np': 155,
    'ni': 124,
    'nb': 146,
    'os': 135,
    'pd': 137,
    'pt': 138.5,
    'pu': 159,
    'ra': 159,
    're': 137,
    'rh': 134,
    'rb': 248,
    'ru': 134,
    'sm': 180.4,
    'sc': 162,
    'sr': 215,
    'ta': 146,
    'tc': 136,
    'te': 136,
    'tb': 177.3,
    'tl': 170,
    'th': 179,
    'tm': 175.9,
    'sn': 145,
    'ti': 147,
    'u': 156,
    'vv': 134,
    'w': 139,
    'y': 180,
    'zn': 134,
    'zr': 160
}

# List of magnetic elements (transition metals or elements with significant magnetic behavior)
magnetic_elements = ["FE", "CO", "NI", "MN", "CR", "VV", "TI", "CU", "MO", "NB", "RU", "RH", "PD", "IR", "OS", "RE"]

# Complete list of all elements in the periodic table
all_elements = [
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca", 
    "Sc", "Ti", "Vv", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn", "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", 
    "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn", "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", 
    "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", 
    "Pt", "Au", "Hg", "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th", "Pa", "U", "Np", "Pu", "Am", "Cm", 
    "Bk", "Cf", "Es", "Fm", "Md", "No", "Lr", "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds", "Rg", "Cn", "Nh", "Fl", "Mc", 
    "Lv", "Ts", "Og"
]

# Create a dictionary with elements and their corresponding magnetization values
MAGNETIZATION_DICT = {element.upper(): (5 if element.upper() in magnetic_elements else 0.6) for element in all_elements}

# --------------------------------------------------------------
# translation_vectors — 由 PCT_Toolkit.optimize 引用
# 用来在邻居判定时尝试把 metal 沿 ±1 整数向量平移到相邻像胞。
# 27 个邻居(±1, ±1, ±1)的分数平移向量。
# --------------------------------------------------------------
import itertools as _itertools
translation_vectors = [
    [tx, ty, tz]
    for tx, ty, tz in _itertools.product((-1, 0, 1), repeat=3)
]