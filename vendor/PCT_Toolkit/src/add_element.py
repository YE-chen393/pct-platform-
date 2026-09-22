from src.create_database_entries_from_system import create_reference_elements, create_endmembers_new, create_mixing_new
from MongoDB.connect import collection_calculation, collection_system, db

def add_element(name=None):
    if name:
        systems = collection_system.find({'system': name})
    else:
        systems = collection_system.find({})
    for system in systems:
        # check if its a new system
        if not system.get("max_hydrogen"):
            continue
        ## check if element is in accordance with already stored elements    
        #if system["elements"] and len(element) != len(system["elements"][0]):
        #    raise ValueError("Structure of new element is not in accordance with existing elements")
        #if element in system["elements"]:
        #    raise ValueError("Element already in system.")
        #system_elements = copy.deepcopy(system['elements'])
        #system_elements.append(element)
        #collection_system.update_one({'_id': system['_id']}, {'$set': {'elements': system_elements}})
        #collection_system.update_one({'_id': system['_id']}, {'$push': {'elements': element}})
        create_reference_elements()
        create_endmembers_new(system)
        # check for reference element
        #for sl in element:
        #    task = collection_calculation.find_one({'elements': sl[0], 'type': 'reference'})
        #    if not task:
        #        create_reference_elements()

        # TODO check for mixing!
        create_mixing_new(system)