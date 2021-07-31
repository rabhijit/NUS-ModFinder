import requests
import json
import time
import re

acad_year = "2021-2022"
server = "https://api.nusmods.com/v2/" + acad_year

"""
Filter functions, to exclude certain mods from search
"""

def exclude_postgrad_mods(mod_code):
    digit_pos = int(re.search(r"\d", mod_code).group(0))
    if digit_pos >= 5:
        return False
    return True

def exclude_unique_mods(mod_code):
    # e.g. DYOM mod codes
    mod_header = mod_code[0:2]
    unique_headers = set(["DM", "BI"])
    if mod_header in unique_headers:
        return False
    return True

"""
NUSMods API functions, to get module data
"""

def get_mods_list():
    resp = requests.get(server + "/moduleList.json")
    return resp.json()

def get_mods_codes(exclude_postgrads_flag):
    mods_list = get_mods_list()
    mods_codes = filter(exclude_unique_mods, (mod["moduleCode"] for mod in mods_list))
    if exclude_postgrads_flag:
        mods_codes = filter(exclude_postgrad_mods, mods_codes)
    return list(mods_codes)

def get_mods_names():
    mods_list = get_mods_list()
    mods_dict = {}
    for mod in mods_list:
        mods_dict[mod['moduleCode']] = mod['title']
    return mods_dict

def get_specific_mod_info(mod_code):
    try:
        resp = requests.get(server + "/modules/" + mod_code + ".json")
        return resp.json()
    except json.decoder.JSONDecodeError:
        return {}

def get_specific_mod_prereqs(mods_info):
    for mod in mods_info:
        print(mod['prerequisite'])

def read_user_mods():
    with open('modules_taken.txt') as file:
        mods = file.readlines()
        file.close()
    return [mod.rstrip() for mod in mods]

"""
Evaluation / search functions to check eligibility
"""

def evaluate_prereq_tree(user_mods, prereq_tree):
    # recurse through prerequisite tree to see if you meet requirements for this mod
    if isinstance(prereq_tree, str): # only one pre-req, not a tree
        if prereq_tree in user_mods:
            return True
        else:
            return False
    else:
        operator = list(prereq_tree.keys())[0]
        prereq_list = prereq_tree[operator]

        if operator == 'or':
            fulfill_status = False
        else: # operator == 'and'
            fulfill_status = True

        for term in prereq_list:
            if isinstance(term, dict):
                evaluate_prereq_tree(user_mods, term)
            else:
                if term in user_mods and operator == 'or':
                    fulfill_status = True
                elif term not in user_mods and operator == 'and':
                    fulfill_status = False

        return fulfill_status

def find_eligible_mods(user_mods, exclude_postgrads_flag):
    # search through every available mod in NUS. if you can't take a mod, remove all of its further mods as well
    fulfillment_list = []
    mods_covered = set(user_mods)
    mods_codes = get_mods_codes(exclude_postgrads_flag)
    while mods_codes:
        mod = mods_codes.pop(0)
        if mod in mods_covered:
            continue

        mod_info = get_specific_mod_info(mod)
        if 'prerequisite' not in mod_info and 'prereqTree' not in mod_info:
            # module has no pre-reqs
            fulfillment_list.append(mod)
        elif 'prereqTree' in mod_info:
            prereq_tree = mod_info['prereqTree']
            fulfill_status = evaluate_prereq_tree(user_mods, prereq_tree)
            if fulfill_status:
                fulfillment_list.append(mod)

        # remove all fulfillReqs from mods_codes
        if 'fulfillRequirements' in mod_info:
            mod_postreqs = set(mod_info['fulfillRequirements'])
            mods_covered |= mod_postreqs

    return fulfillment_list

def save_to_file(eligible_mods):
    # save to eligible_modules.txt
    mods_dict = get_mods_names()
    with open("eligible_modules.txt", "w") as txt_file:
        for mod in eligible_mods:
            mod_name = mods_dict[mod]
            full_mod = mod + " " + mod_name
            txt_file.write(full_mod + "\n")

def main():
    print('Welcome to ModFinder!\nPlease ensure you have filled up all the modules you have taken so far, in \'modules_taken.txt\'.\n')

    exclude_postgrads_input = ""
    while exclude_postgrads_input != "yes" and exclude_postgrads_input != "no":
        exclude_postgrads_input = input('Would you like to exclude post-graduate modules from your search? (i.e. 5k mods and above). \nI found it speeds up search quite a bit. Enter \'yes\' or \'no\' below:\n>> ')
    exclude_postgrads_flag = True if exclude_postgrads_input == "yes" else False

    print("\nOkay, let's go.")
    start_time = time.time()

    print('Loading modules you\'ve taken so far...\n')
    user_mods = read_user_mods()
    print('Finding modules you\'re eligible for...\nThis might take 3 - 5 minutes. NUS has a lot of modules! Feel free to let this run in the background.')
    eligible_mods = find_eligible_mods(user_mods, exclude_postgrads_flag)

    print('Saving to \'eligible_modules.txt\'...\n')
    save_to_file(eligible_mods)

    end_time = time.time()
    elapsed_time = round(end_time - start_time, 2)
    print("Done in", elapsed_time, "seconds.")
    print('You can find the modules you are eligible for in \'eligible_modules.txt\'.\n')
    print('Note: some modules may have non-modular requirements, e.g. A-level pre-requisites, cohort requirements or min. number of credits, that we can\'t check for. Do make sure to check for those.\n\nHave a nice day!')

if __name__ == '__main__':
    main()

