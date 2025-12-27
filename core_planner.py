from pathlib import Path
import utilities as u
import os
import csv, json
from enum import Enum
from elective_planner import PlannerForElective
from update_result import UpdateResult
from pass_info import PreviousDetails

#index for the code list to stop at (core unit)
#since both a/d for year 1 have 3 core for sem 1, we only need 1 constant
YEAR_1_SEM_1 = 3 #3 core y1
YEAR_2_SEM_1_D = 2 #2 core for data science y2
YEAR_2_SEM_1_A   = 3 #3 core for algorithm & software y2
YEAR_3_SEM_1_D_F = 2 #2 core for data science y3 - feb intake 
YEAR_3_SEM_1_D = 1 #1 core for data science y3 - july intake 
YEAR_3_SEM_1_A = 2 #2 core for advanced y3 

class PlannerMenuEnum(Enum):
    VIEW_DETAILS = 0
    CHOOSE_ELECTIVE = 1
    CHANGE_ELECTIVE = 2
    VIEW_PLAN = 3
    SAVE_PlAN = 4
    QUIT_PLANNER = 5

class UserInfo():
    def __init__(self):
        # store user info
        self.stream = None
        self.year = None
        self.sem = None
        self.intake = None

    #-------------user info------------------
    def user_basic_info(self):
        """
        Prompt user for basic information such as their current stream, year and sem

        User answer must be within expected range using the function imported from utilities 

        @returns: (stream, year, sem)
        A tuple of three integer that contains user info
        """
        print("")
        username = input("Enter your username: ")
        print("")
        print("1. February Semester")
        print("2. July Semester")
        intake = u.read_integer("Enter intake: ", 1, 2)
        #print stream option
        print("")
        print("1. Data Science")
        print("2. Algorithms and Software")
        stream = u.read_integer("Enter current stream: ", 1, 2)
        year = u.read_integer("Enter year to plan [1/2/3]: ",1, 3)
        sem = u.read_integer("Enter sem to plan [1/2]: ", 1, 2)

        #if year 2 july semester: sem 1 for feb is sem 2 for july 
        if (intake == 1 and year == 2 and sem == 1):
            sem = 2
        elif (intake == 1 and year == 2 and sem == 2):
            sem = 1
        return (username, stream, year, sem, intake)

    def user_basic_info_web(self, username, stream, year, sem, intake):
        """Used by Flask API directly set user info instead of asking input"""
        self.username = username
        self.stream = int(stream)
        self.year = int(year)
        self.sem = int(sem)
        self.intake = int(intake)
        return (username, self.stream, self.year, self.sem, self.intake)


class PlannerForCore():
    def __init__(self, user_info, pass_info):
        self.user_info = user_info
        self.pass_info = pass_info

        #reference from csv
        self.core_units_all = {}    
        self.filtered_core_units = {}
        self.filtered_core_list = []

        #user-specific data
        self.user_core_progress = {} 
        self.list_fullfilled = []
        self.completed_list = []
        self.current_sem = []

    def setup_user(self):
        username, stream, year, sem, intake = self.user_info.user_basic_info()
        self.user_info.username = username
        self.user_info.stream = stream
        self.user_info.year = year
        self.user_info.sem = sem
        self.user_info.intake = intake

    #-------------read core unit------------------
    def choose_core_file(self):
        """
        [can be extend]
        Select the correct csv file that have the current core unit info 
        Core unit file differs for DS/AS

        @returns
        the correct file path to the corret core unit csv
        """
        stream = self.user_info.stream
        year = self.user_info.year
        if (stream == 1 and year == 1):
            return "data/d_y1_core_units.csv"
        elif (stream == 2 and year == 1):
            return "data/a_y1_core_units.csv"
        elif (stream == 1 and year == 2):
            return "data/d_y2_core_units.csv"
        elif (stream == 2 and year == 2):
            return "data/a_y2_core_units.csv"
        elif (stream == 1 and year == 3):
            return "data/d_y3_core_units.csv"
        elif (stream == 2 and year == 3):
            return "data/a_y3_core_units.csv"
        else:
            return("No information found for your option")
        
    def read_core_unit(self):
        """
        read csv file and store the filtered (based on sem) and unfiltered dictionary of core units
        """

        stream = self.user_info.stream
        year = self.user_info.year
        sem = self.user_info.sem
        intake = self.user_info.intake

        core_file = Path(self.choose_core_file())

        #core unit list 
        core_unit_code_list = []
        filter_core_code_list = []
    
        #core unit dict
        core_unit_dict = {}

        #get all the info into core_unit dict and list
        if (not core_file.is_file()):
            print("System error: No information found")
        else:
            with open(self.choose_core_file(), mode='r', encoding="utf-8-sig") as file:
                core_unit_file = csv.DictReader(file)
                for line in core_unit_file:
                    #get the core_unit_code into a list
                    core_unit_code_list.append(line["unit_code"].strip())
                    #unit_code as key, get unit_name, semester, description, prereq and workload
                    core_unit_dict[line["unit_code"]] = {
                    #create dictionary so each row will be a key as well 
                        "unit_name": line["unit_name"].strip(), 
                        "sem_available": line["semester_available"].strip(),
                        "description": line["description "].strip(),
                        "prereq": line["prereq"].strip(),
                        "assign": line["Assignment"].strip(),
                        "test": line["Test"].strip(),
                        "final": line["Final"].strip()
                    }

        #filter the core unit dict and list based on sem
        #extend this for different year and sem 
        if (sem == 1 and year == 1):
            filter_core_code_list = core_unit_code_list[:YEAR_1_SEM_1]
        elif (sem == 2 and year == 1):
            filter_core_code_list = core_unit_code_list[YEAR_1_SEM_1:]
        elif (sem == 1 and year == 2 and stream == 1):
            filter_core_code_list = core_unit_code_list[:YEAR_2_SEM_1_D]
        elif (sem == 2 and year == 2 and stream == 1):
            filter_core_code_list = core_unit_code_list[YEAR_2_SEM_1_D:]
        elif (sem == 1 and year == 2 and stream == 2):
            filter_core_code_list = core_unit_code_list[:YEAR_2_SEM_1_A]
        elif (sem == 2 and year == 2 and stream == 2):
            filter_core_code_list = core_unit_code_list[YEAR_2_SEM_1_A:]
        elif (sem == 1 and year == 3 and stream == 1):
            if (intake == 1):
                filter_core_code_list = core_unit_code_list[:YEAR_3_SEM_1_D_F]
            else:
                filter_core_code_list = core_unit_code_list[:YEAR_3_SEM_1_D]
        elif (sem == 2 and year == 3 and stream == 1):
            if (intake == 1):
                filter_core_code_list = core_unit_code_list[YEAR_3_SEM_1_D_F:]
            else:
                filter_core_code_list = core_unit_code_list[YEAR_3_SEM_1_D:]
        elif (sem == 1 and year == 3 and stream == 2 and intake == 2):
            filter_core_code_list = core_unit_code_list[:YEAR_3_SEM_1_A]
        elif (sem == 2 and year == 3 and stream == 2 and intake == 2):
            filter_core_code_list = core_unit_code_list[YEAR_3_SEM_1_A:]
        elif (sem == 1 and year == 3 and stream == 2 and intake == 1):
            filter_core_code_list.append(core_unit_code_list[0])
            filter_core_code_list.append(core_unit_code_list[3])
        elif (sem == 2 and year == 3 and stream == 2 and intake == 1):
            filter_core_code_list.append(core_unit_code_list[1])
            filter_core_code_list.append(core_unit_code_list[2])

        for unit_code, unit_info in core_unit_dict.items():
            if (unit_code in filter_core_code_list):
                self.filtered_core_units[unit_code] = unit_info

        #check if the unit going to show had been swapped
        user_folder = Path(f"user_info/{self.user_info.username}")
        already_taken_units = set()
        
        if user_folder.exists():
            # Loop through all Y{year}S{sem}_units.json files
            for file in user_folder.glob("Y*S*_units.json"):
                # Skip the current semester file
                current_sem_file = f"Y{year}S{sem}_units.json"
                if file.name == current_sem_file:
                    continue
                    
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        semester_units = json.load(f)
                        # Add all units from this semester to the set
                        already_taken_units.update(semester_units.keys())
                except Exception as e:
                    print(f"Error reading {file}: {e}")
        
        # Remove already-taken units from the filter list
        filter_core_code_list = [
            code for code in filter_core_code_list 
            if code not in already_taken_units
        ]
        
        # Build filtered_core_units
        self.filtered_core_units = {
            k: v for k, v in core_unit_dict.items() 
            if k in filter_core_code_list
        }
        
        # Return filtered dict and unfiltered dict
        self.core_units_all = core_unit_dict
        self.filtered_core_list = filter_core_code_list
    
    def save_user_core(self):
        """
        Check if user's JSON already has the unit info saved.
        If not, add new core unit entries from self.core_units into JSON.
        """
        user_folder = Path("user_info") / self.user_info.username
        user_folder.mkdir(parents=True, exist_ok=True)
        file_path = user_folder / "core_units.json"

        # Load existing JSON data
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
        else:
            saved_data = {}

        # Track if anything new added
        new_added = False

        # Add missing core units
        for unit_code, unit_info in self.core_units_all.items():
            if unit_code not in saved_data:
                saved_data[unit_code] = unit_info
                new_added = True

        # Save only if something was added
        if new_added:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(saved_data, f, indent=4)
            print(f"Updated {file_path} with new core units.")
        else:
            print("No new core units to add. JSON already up-to-date.")

    #-------------display core unit at start------------------ 
    def unit_alert(self):
        """
        There is some confusion in terms of what sem means, when considering user's perspective, 
        their year 2 sem 1 should mean this is their second year first semester, so this unit alert will act as a disclaimer

        Feb intake sem 1 -> user first semester and Feb semester (S1)
        Feb intake sem 2 -> user second semester and July semester (S2)

        But for july intake
        July intake sem 1 -> user first semester and July semester (S2)
        July intake sem 2 -> user second semester and Feb semester (S1)

        So this function will alert user that what is the semester there are in, for better clarity
        """ 
        print("Reminder: ", end="")
        if (self.user_info.intake == 2 and self.user_info.sem == 1):
            self.current_sem = 2
            print("This is the July Semester")
        elif (self.user_info.intake == 2 and self.user_info.sem == 2):
            self.current_sem = 1
            print("This is the February Semester")
        elif (self.user_info.intake == 1 and self.user_info.sem == 1):
            self.current_sem = 1
            print("This is the February Semester")
        elif (self.user_info.intake == 1 and self.user_info.sem == 2):
            self.current_sem = 2
            print("This is the July Semester")


    #so at the start of this menu, the defaul core will be show
    #this function will format the info and show it nicely
    def display_core(self):
        """
        Display default core for that semester and year

        Before user choose to add elective or see any details
        It will show the unit code, name and its description
        """

        if (self.user_info.intake == 1 and self.user_info.sem == 2 and self.user_info.year == 2):
            self.user_info.sem = 1
        elif (self.user_info.intake == 1 and self.user_info.sem == 1 and self.user_info.year == 2):
            self.user_info.sem = 2

        print("")
        self.unit_alert()
        print("==============================================")
        print(f"Default Core Unit For Year {self.user_info.year} Sem {self.user_info.sem}")
        for unit_code, unit_info in self.filtered_core_units.items():
            print("---------------------------------------------")
            print(f"[ {unit_code} ]: {unit_info["unit_name"]}")
            print(f"Description: {unit_info["description"]}")
            print("")

    #show workload clearly in three section
    #print out workload info after getting the list
    def print_workload_info(self, workload_name, workload_list):
        """
        Display formatted workload information for sepecific workload type
        If the list is NONE

        @param workload_name (string) - workload type name to print out
        @param  workload_list (list) - marks for each workload of the same type
        """
        if ("NONE" in workload_list):
            print(f"No {workload_name} for this unit")
        else:
            workload_list_int = [float(s) for s in workload_list]
            #print assignment info
            print(f"Total {workload_name}: {len(workload_list_int)}")
            for i, workload in enumerate(workload_list_int):
                print(f"{workload_name[0].upper()}{i+1}: {workload/100:.0%}")

    def workload_extraction(self, assignment, test, final):
        """
        Return formatted workload info for assignment, test, and final as strings.
        Example: "20%, 30%"
        """
        def format_list(lst):
            return ', '.join([f"{int(s)}%" for s in lst if s.isdigit()]) or "None"

        # Split strings
        assignments_str = assignment.split(";")
        tests_str = test.split(";")
        finals_str = final.split(";")

        # Assignments
        assign_str = format_list(assignments_str)

        # Tests
        test_str = format_list(tests_str)

        # Finals
        if "NONE" in finals_str:
            final_str = "None"
        else:
            final_str = format_list(finals_str)

        return {
            "assign": assign_str,
            "test": test_str,
            "final": final_str
        }


    #show available sem clearly
    def sem_extraction(self, sem_available):
        """
        Display the sem in cleaerer format

        @param sem (list) - list containing 1 and/or 2 representing sem 1 and sem 2
        """
        sems_list_str = sem_available.split(";")

        sems_list = [int(s) for s in sems_list_str]

        print_sem_list = []

        for sem in sems_list:
            if (sem == 1):
                print_sem_list.append(f"February Semester")
            else:
                print_sem_list.append(f"July Semester")

        return print_sem_list

    #search for unit 
    def search_unit(self):
        """
        Display available core unit and return the searched unit to be printed in display_core

        @param stream (integer) - show available core based on student core

        @returns unit_code 
        """
        stream = self.user_info.stream
        core_unit_code_list = []
        if (stream == 1):
            stream_str = "Data Science"
        else:
            stream_str = "Algorithms and Software"

        #return list index
        print("")
        print(f"Core Units for Y{self.user_info.year}: {stream_str}")
        for i, unit_code in enumerate(self.core_units_all):
            core_unit_code_list.append(unit_code)
            print(f"{i+1}: {unit_code}")
        user_option_index = u.read_integer("Enter an option: ", 1, len(core_unit_code_list)) - 1

        #find the unit code from list
        searched_unit = core_unit_code_list[user_option_index]
        return searched_unit

    def choose_core_list(self):
        """
        search for the unit and display the info
        """
        searched_unit = self.search_unit()
        info = self.get_unit_core_info(searched_unit)
        print(json.dumps(info, indent=4))
    
    def display_prerequisites(self, unit_code):
        """
        Display prerequisites for a unit in a readable format.
        """
        prereq_dict = {}
        for u_code, unit_info in self.core_units_all.items():  
            prereq_dict[u_code] = unit_info.get("prereq", "NONE")
        
        prereq_str = prereq_dict.get(unit_code, "")
        
        if not prereq_str or prereq_str == "NONE":
            return f"{unit_code} has no prerequisites."

        if prereq_str.startswith('a;'):
            prereq_units = [u.strip() for u in prereq_str[2:].split(';')]
            return f"To take {unit_code}, you must have completed all of these units: {', '.join(prereq_units)}"

        elif prereq_str.startswith('12;'):
            prereq_units = [u.strip() for u in prereq_str[3:].split(';')]
            return f"To take {unit_code}, you must have completed 2 units"
        
        elif prereq_str.startswith('72;'):
            prereq_units = [u.strip() for u in prereq_str[3:].split(';')]
            return f"To take {unit_code}, you must have completed 72 units"

        elif prereq_str.startswith('o;'):
            prereq_units = [u.strip() for u in prereq_str[2:].split(';')]
            return f"To take {unit_code}, you must have completed at least one of these units: {', '.join(prereq_units)}"

        else:
            return f"To take {unit_code}, you must have completed: {prereq_str}"

    def get_unit_core_info(self, searched_unit):
        """
        Return detailed info about a core unit as a dictionary,
        including formatted workload.
        """
        user_path = Path(f"user_info/{self.user_info.username}/core_units.json")
        if not user_path.is_file():
            return None

        with open(user_path, "r", encoding="utf-8") as f:
            self.core_units_all = json.load(f)

        unit_info = self.core_units_all.get(searched_unit)
        if not unit_info:
            return None

        workload = self.workload_extraction(unit_info["assign"], unit_info["test"], unit_info["final"])

        return {
            "code": searched_unit,
            "name": unit_info['unit_name'],
            "description": unit_info['description'],
            "semesters": self.sem_extraction(unit_info['sem_available']),
            "prerequisites": self.display_prerequisites(searched_unit),
            "assign": workload['assign'],
            "test": workload['test'],
            "final": workload['final']
        }


    #--------------check core-----------------

    def check_unit_prereq(self):
        """
        Create a dictionary of all units and their prerequisites
        """
        prereq_dict = {}
        for unit_code, unit_info in self.core_units_all.items():
            prereq_dict[unit_code] = unit_info.get("prereq", "NONE")
        return prereq_dict  
    
    def normalize_code(self, code):
        code = code.strip().upper()
        if not code.startswith("FIT"):
            code = "FIT" + code
        return code


    def can_take_unit(self, unit_code, prereq_dict, completed_list):
        """
        Check if a unit can be taken based on prerequisites
        """
        completed_list = self.pass_info.saved_all_pass_unit()
        prereq_str = prereq_dict.get(unit_code, "")
        
        if not prereq_str or prereq_str == "NONE":
            print("No prerequisites required")
            return True

        # Check if it's an "a;" type (all units required)
        if prereq_str.startswith('a;'):
            prereq_units = [self.normalize_code(u) for u in prereq_str[2:].split(';') if u.strip()]
            print(f"Type: ALL required. Prereqs: {prereq_units}")
            result = all(unit in completed_list for unit in prereq_units)
            print(f"Result: {result}")
            return result

        # Check if it's a "12" type (any 2 units required)
        elif prereq_str == "12":
            print(f"Type: Any 12 CP. Completed: {len(completed_list)} units")
            result = len(completed_list) >= 2
            print(f"Result: {result}")
            return result
        
        elif prereq_str == "12":
            print(f"Type: Any 72 CP. Completed: {len(completed_list)} units")
            result = len(completed_list) >= 12
            print(f"Result: {result}")
            return result
        
        # Check if it's an "o;" type (one of the units required)
        elif prereq_str.startswith('o;'):
            prereq_units = [self.normalize_code(u) for u in prereq_str[2:].split(';') if u.strip()]
            print(f"Type: ONE OF required. Prereqs: {prereq_units}")
            result = any(unit in completed_list for unit in prereq_units)
            print(f"Result: {result}")
            return result

        else:
            # Single unit prerequisite
            normalized_prereq = self.normalize_code(prereq_str.strip())
            print(f"Type: Single unit. Normalized prereq: '{normalized_prereq}'")
            result = normalized_prereq in completed_list
            print(f"Result: {result}")
            return result
        
    def check_core_prereq(self):
        """
        Check if core units can be taken - return list of units with unmet prereqs
        """
        self.list_fullfilled = []
        prereq_dict = self.check_unit_prereq()
        completed_list = self.pass_info.saved_all_pass_unit()
        self.completed_list = completed_list
        
        unmet_units = []  

        for unit_code in self.filtered_core_list:
            can_take = self.can_take_unit(unit_code, prereq_dict, completed_list)
            self.list_fullfilled.append(can_take)
            
            if not can_take:
                print(f"You cannot take {unit_code} because prerequisite is not fulfilled")
                unmet_units.append(unit_code)  
        
        return unmet_units  
    
class PlannerMenu():
    def __init__(self):
        """
        all the classes (in differnt file) is called here 
        """
        user_info = UserInfo()
        self.update_result = UpdateResult()
        self.pass_info = PreviousDetails(user_info, self.update_result)
        self.planner_core = PlannerForCore(user_info, self.pass_info)    
        self.planner_elective = PlannerForElective(user_info, self.planner_core)

    #show planner menu
    def print_menu(self):
        """"
        Print out the planner menu available options
        """
        print(f"====Planner Menu for Y{self.planner_core.user_info.year}S{self.planner_core.user_info.sem}====")
        print("1. Search Unit Details")
        print("2. Choose Elective")
        print("3. Change Elective")
        print("4. View Current Plan")
        print("5. Save Plan")
        print("6. Quit Planner Menu")

    #return choice index
    def user_option(self):
        """
        Return user option index to switch between cases
        """
        while True:
            try:
                self.print_menu()
                user_option = u.read_integer("Enter an option: ", 1, len(PlannerMenuEnum))
                return (user_option - 1)
            except ValueError:
                print("Please enter an valid option\n")
    

    def run(self):
        """
        This is where all the different function will get called

        user_basic_info - Allow user enter stream, year and sem
        read_core_unit - Read the correct core unit csv file
        display_core - Display the default core units for that year and sem

        Choice 1. View details of the core unit / elective units

        Choice 2 - Choose elective 

        Choice 3 - Change elective

        Choice 4 - View Current Plan

        Choice 5 - Save current plan
        - we can only save after reviewing it at choice 4 
        - any prerequistie havent been fulfilled at core will cause the plan to be unable to save

        Choice 6. 
        Quit
        """
        # user enters their info        
        while True:
            self.planner_core.setup_user()
            self.pass_info.check_previous_record()
            if (len(self.pass_info.info_check_requirement) != 0):
                print("Error. No info found for previous year or sem")
                print("You should plan for all previous year and sem and save the data")
                self.pass_info.info_check_requirement = []
            else:
                break
        
        #check if the json file is available
        #then check if the json file grade had been updated
        #then cehck if the prerequiste of core units had been fullfilled 
        if (self.planner_core.user_info.year == 1 and self.planner_core.user_info.sem == 1):
            pass
        else:
            self.pass_info.check_json_planned()
        # Try to load saved core units first
        self.planner_core.read_core_unit()
        for code, info in self.planner_core.core_units_all.items():
            if code not in self.planner_core.user_core_progress:
                pass
        self.planner_core.save_user_core()
        self.planner_core.display_core()
        if (self.planner_core.user_info.year == 1 and self.planner_core.user_info.sem == 1):
            pass
        else:
            self.planner_core.check_core_prereq()
        self.planner_elective.read_elective()
        self.planner_elective.save_user_elective()

        while True:
            #option
            choice_index = self.user_option()
            choice = PlannerMenuEnum(choice_index)

            match choice:
                case PlannerMenuEnum.VIEW_DETAILS:
                    print("")
                    self.planner_elective.choose_core_or_elective_list()
                case PlannerMenuEnum.CHOOSE_ELECTIVE:
                    self.planner_elective.user_choice_choose_elective()
                case PlannerMenuEnum.CHANGE_ELECTIVE:
                    self.planner_elective.change_elective()
                case PlannerMenuEnum.VIEW_PLAN:
                    self.planner_elective.combine_information()
                case PlannerMenuEnum.SAVE_PlAN:
                    self.planner_elective.saved_as_JSON()
                case PlannerMenuEnum.QUIT_PLANNER:
                    print("Quiting Planner Menu....")
                    break

            print("")

    