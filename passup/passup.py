#--------------------core_planner-----------------------------------------
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
    
        # return filtered dict and unfiltered dict
        self.core_units_all = core_unit_dict
        self.filtered_core_list = filter_core_code_list

        # build filtered_core_units (master filtered view)
        self.filtered_core_units = {k: v for k, v in core_unit_dict.items() if k in filter_core_code_list}
    
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

    #-------------Core Planner Function (Seach for Core)------------------
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
        Extract and display information for assignment, test and final 

        @param assignemnt (string)
        @param test (string)
        @param final (string)
        """
        assignments_str = assignment.split(";")
        tests_str = test.split(";")
        finals_str = final.split(";")

        #convert to integer for assignement 
        self.print_workload_info("assignment", assignments_str)

        #convert to integer for test
        self.print_workload_info("test", tests_str)

        #print final exam info
        if ("NONE" in finals_str):
            print(f"No finals for this unit")
        else:
            finals = [int(s) for s in finals_str]
            for i in finals:
                print(f"Final Exam: {i/100:.0%}")

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
        self.display_unit_core_info(searched_unit)
    
    def display_prerequisites(self, unit_code):
        """
        Display prerequisites for a unit in a readable format.
        """
        prereq_dict = {}
        for u_code, unit_info in self.filtered_core_units.items():  
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

        elif prereq_str.startswith('o;'):
            prereq_units = [u.strip() for u in prereq_str[2:].split(';')]
            return f"To take {unit_code}, you must have completed at least one of these units: {', '.join(prereq_units)}"

        else:
            return f"To take {unit_code}, you must have completed: {prereq_str}"

    #display unit that user search for 
    def display_unit_core_info(self, searched_unit):
        """
        Display detailed info about a core unit.
        Automatically loads from core_units.json if not already loaded.
        """
        # Ensure the dictionary is loaded
        user_path = Path(f"user_info/{self.user_info.username}/core_units.json")

        # Load if not already loaded
        if user_path.is_file():
            with open(user_path, "r", encoding="utf-8") as f:
                self.core_units_all = json.load(f)
        else:
            print(f"Error: {user_path} not found.")
            return

        unit_info = self.core_units_all.get(searched_unit)

        # Display formatted info
        print("")
        print(f"======= Unit Details - {searched_unit} =======")
        print(f"[ {searched_unit} ]: {unit_info['unit_name']}")
        print(f"Description: {unit_info['description']}")
        print(f"Available Semester: {', '.join(self.sem_extraction(unit_info['sem_available']))}")
        print(f"Prerequisites: {self.display_prerequisites(searched_unit)}")
        print("-----------------------------------")
        print("Workload")
        self.workload_extraction(unit_info["assign"], unit_info["test"], unit_info["final"])

    #--------------check core-----------------

    def check_unit_prereq(self):
        """
        this will loop throught he dictionary and create a dictionary that contains
        - unit code
        - prerequsite in a list
        """
        prereq_dict = {}
        final_unit_with_prereq = {}
        for unit_code, unit_info in self.filtered_core_units.items():
            prereq_dict[unit_code] = unit_info["prereq"]
        for unit_code, preq_info in prereq_dict.items():
            if (preq_info == "NONE"):
                pass
            else:
                final_unit_with_prereq[unit_code] = preq_info
        return final_unit_with_prereq

    def normalize_code(self, code):
        code = code.strip().upper()
        if not code.startswith("FIT"):
            code = "FIT" + code
        return code


    def can_take_unit(self, unit_code, prereq_dict, completed_list):
        """
        @param unit_code - the current unit that we are checking
        @param prereq_dict - the prereq dict that contain unit_code and the prerequisite
        @param completed_list - the complete list of all passed unit info

        if the prerequisite start with a 
        for unit in the prerequisite must be fulfill to take that unit
        else if the prerequisite start with 12 
        means two unit must be pass before taking that 
        else if the prerequisite start with o 
        one of the unit in the lsit must passed
        """
        prereq_str = prereq_dict.get(unit_code, "")
        if not prereq_str or prereq_str == "NONE":
            return True  # no prerequisites

        # Check if it's an "a;" type (all units required)
        if prereq_str.startswith('a;'):
            prereq_units = [self.normalize_code(u) for u in prereq_str[2:].split(';')]
            return all(unit in completed_list for unit in prereq_units)

        # Check if it's a "12" type (any 2 units required)
        elif prereq_str == "12":
            return len(completed_list) >= 2
        
        # Check if it's an "o;" type (one of the units required)
        elif prereq_str.startswith('o;'):
            prereq_units = [self.normalize_code(u) for u in prereq_str[2:].split(';')]
            return any(unit in completed_list for unit in prereq_units)

        else:
            return prereq_str.strip() in completed_list

    
    def check_core_prereq(self):
        """
        check if core unit can be take - if not alert message will show

        output message to alert user they cannot take current core unit because the prerequisite haven't been met
        """
        self.list_fullfilled = []
        prereq_dict = self.check_unit_prereq()
        completed_list = self.pass_info.saved_all_pass_unit()
        self.completed_list = completed_list
        for unit_code in self.filtered_core_list:
            self.list_fullfilled.append(self.can_take_unit(unit_code, prereq_dict, completed_list))
            if (self.can_take_unit(unit_code, prereq_dict, completed_list) == False):
                print(f"You cannot take {unit_code} because prerequisite is not fulfilled")
    
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

#--------------------------elective planner------------------------
import utilities as u
from pathlib import Path
import csv, json
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class PlannerForElective():
    def __init__(self, user_info, core_planner):
        """
        user_info from user info class
        username to be access anywhre in the calss
        core planner class
        all_elective_dict to showing all elective (L1-L3)
        all_elective_list to show all elective in a list 
        final_elecitive choose the final (1/2/3 based on elective spaces) elective
        final_unit_list_for_current_sem - contain four units - ready to be saved
        """
        self.user_info = user_info
        self.core_planner = core_planner
        self.all_electives_dict = {}
        self.all_electives_list = []
        self.final_elective = []
        self.final_unit_list_for_current_sem = []

    def setup_user(self):
        """
        access user basic info such as stream year sem and intake in this class
        """
        username, stream, year, sem, intake = self.user_info.user_basic_info()
        self.user_info.username = username
        self.user_info.stream = stream
        self.user_info.year = year
        self.user_info.sem = sem
        self.user_info.intake = intake
    
    def read_elective(self):
        """
        Read the elective unit csv file and save all the elective info as a dictionary 
        Save the elecitve unit code as list to allow easier sorting
        """
        with open("data/elective_units.csv", mode ="r", encoding="utf-8-sig") as file:
            elecitve_unit_file = csv.DictReader(file)
            for line in elecitve_unit_file:
                #save into list
                self.all_electives_list.append(line["unit_code"].strip())
                #save into dict
                self.all_electives_dict[line["unit_code"].strip()] = {
                    "unit_name": line["unit_name"].strip(), 
                    "sem_available": line["semester_available"].strip(),
                    "description": line["description "].strip(),
                    "prereq": line["prereq"].strip(),
                    "assign": line["Assignment"].strip(),
                    "test": line["Test"].strip(),
                    "final": line["Final"].strip(),
                    "approved_elective": line["Approved"].strip()
                }
        
    def manually_choose_based_on_level(self):
        print("Enter your interest elective level")
        print("Level 1")
        print("Level 2")
        print("Level 3")

        user_input = u.read_integer("Enter your choice: ",1,3)

        return user_input

    def get_available_electives_by_level(self, level):
        """Return electives of the given level that pass availability and prereq checks."""
        available = []
        for unit_code in self.all_electives_list:
            if unit_code[3] == str(level):  # check level
                # also check it's not already chosen
                if unit_code not in self.final_elective and unit_code not in self.core_planner.core_units_all:
                    available.append(unit_code)
        return available
    
    def choose_elective_manually(self, user_input):
        """
        this choose elective manually will display a list of elective and let user choose
        if they want year 1 or year 2 or year 3 elective
        """
        user_choice_elective_list = []
        for unit_code in self.all_electives_list:
            if (unit_code[3] == str(user_input)):
                user_choice_elective_list.append(unit_code)
        
        for i, unit_code in enumerate(user_choice_elective_list):
            print(f"{i+1}: {unit_code}")

        user_option_index = u.read_integer("Enter an option: ", 1, len(user_choice_elective_list)) - 1
        chosen_elective = user_choice_elective_list[user_option_index]
        return chosen_elective

    def recommend_electives_smart(self, level, user_interest, num_reco=3):
        """
        Recommend electives based on similarity between user's interest and elective descriptions.
        """
        # 1. Filter electives by level and availability
        available_units = self.get_available_electives_by_level(level)
        
        if not available_units:
            print("No available electives found for this level.")
            return []
        
        # 2. Prepare descriptions
        descriptions = [self.all_electives_dict[unit]["description"] for unit in available_units]
        
        # 3. Vectorize descriptions and user interest
        vectorizer = TfidfVectorizer(stop_words='english')
        vectors = vectorizer.fit_transform(descriptions + [user_interest])
        
        # 4. Compute cosine similarity
        user_vector = vectors[-1]  # last vector is user input
        elective_vectors = vectors[:-1]
        similarities = cosine_similarity(user_vector, elective_vectors)[0]
        
        # 5. Rank electives by similarity
        ranked_indices = similarities.argsort()[::-1]  # highest first
        recommended_units = [available_units[i] for i in ranked_indices[:num_reco]]
        
        return recommended_units


    def choose_elective_system_recommendation(self):
        print("Enter the year/level of elective you want recommendation for (1/2/3):")
        level = u.read_integer("Enter level: ", 1, 3)
        
        user_interest = input("Describe your interest/future goals: ")

        recommended = self.recommend_electives_smart(level, user_interest)

        if not recommended:
            print("No matching electives found.")
            return

        print("Recommended electives for you:")
        print("0. Don't want any of these")  # Option to opt out
        for i, unit in enumerate(recommended):
            print(f"{i+1}. {unit}: {self.all_electives_dict[unit]['unit_name']}")

        user_choice = u.read_integer(f"Choose elective (0-{len(recommended)}): ", 0, len(recommended))
        
        if user_choice == 0:
            print("No elective chosen from recommendations.")
            return

        chosen_elective = recommended[user_choice - 1]
        self.final_elective.append(chosen_elective)
        print(f"Elective {chosen_elective} added successfully!")


    def check_elective_preq(self, chosen_elective):
        """
        @param chosen_elective check if chosen_elective prerequisite had been met

        call the can_take_unit function at core planner 
        @return true if prereq been met
        """
        preq_dict = {}
        for unit_code, unit_info in self.all_electives_dict.items():
            if (unit_code == chosen_elective):
                preq_dict[chosen_elective] = unit_info["prereq"]
        
        can_take = self.core_planner.can_take_unit(chosen_elective, preq_dict, self.core_planner.completed_list)
            
        return can_take

    def check_elective_available_sem(self, chosen_elective):
        """
        this will create a sem_list and check if user current semester 

        @return true if the unit is available at that semester
        """
        sems_list_str = []
        for unit_code, unit_info in self.all_electives_dict.items():
            if (unit_code == chosen_elective):
                sems_list_str = unit_info["sem_available"].split(";") 
    
        sems_list = [int(s) for s in sems_list_str]
        if (self.core_planner.current_sem not in sems_list):
            return False    
        else:
            return True

    def check_availability(self):
        """
        @return elective if 

        the elective is available at the semester (july or feb sem)
        the elective prerequisite had been fulfilled, user had passed that unit

        else 
        it will keep loop until the chosen elective is true for both situation
        """
        unit_code_core = [unit_code for unit_code in self.core_planner.core_units_all.keys()]
        chosen_elective = self.choose_elective_manually(self.manually_choose_based_on_level())
        while True:
            if not self.check_elective_available_sem(chosen_elective):
                print(f"You cannot choose {chosen_elective} because it is not available in this semester")
            elif not self.check_elective_preq(chosen_elective):
                print(f"You cannot choose {chosen_elective} because prerequisite is not fulfilled")
            elif chosen_elective in unit_code_core:
                print(f"You cannot choose {chosen_elective} as elective because it is a core for your stream")
            elif chosen_elective in self.final_elective:  
                print(f"You have already chosen {chosen_elective} as an elective")
            else:
                return chosen_elective
        
            print("Please try again.")
            print("")
            chosen_elective = self.choose_elective_manually(self.manually_choose_based_on_level())
    
    def display_prerequisites(self, unit_code):
        """
        Display prerequisites for a unit in a readable format.
        """
        user_path = Path(f"user_info/{self.user_info.username}/elective_units.json")

        # Always reload data
        if user_path.is_file():
            with open(user_path, "r", encoding="utf-8") as f:
                self.all_electives_dict = json.load(f)
        else:
            print(f"Error: {user_path} not found.")
            return
        
        prereq_dict = {}
        for u_code, unit_info in self.all_electives_dict.items():  
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

        elif prereq_str.startswith('o;'):
            prereq_units = [u.strip() for u in prereq_str[2:].split(';')]
            return f"To take {unit_code}, you must have completed at least one of these units: {', '.join(prereq_units)}"

        else:
            return f"To take {unit_code}, you must have completed: {prereq_str}"

    def display_elecive(self, chosen_elective):
        """
        user choose they want to choose elective or core unit info
        display unit using the sem extraction and workload extraction 

        @param searched_unit unit that we want to search information from 
        """

        user_path = Path(f"user_info/{self.user_info.username}/elective_units.json")

        # Always reload data
        if user_path.is_file():
            with open(user_path, "r", encoding="utf-8") as f:
                self.all_electives_dict = json.load(f)
        else:
            print(f"Error: {user_path} not found.")
            return

        # Find and display chosen elective
        unit_info = self.all_electives_dict.get(chosen_elective)
        if not unit_info:
            print(f"Elective unit '{chosen_elective}' not found.")
            return

        print("")
        print(f"======= Unit Details - {chosen_elective} =======")
        print(f"[ {chosen_elective} ]: {unit_info['unit_name']}")
        print(f"Description: {unit_info['description']}")
        print(f"Available Semester: {', '.join(self.core_planner.sem_extraction(unit_info['sem_available']))}")
        print(f"Prerequisites: {self.display_prerequisites(chosen_elective)}")
        print("-----------------------------------")
        print("Workload")
        self.core_planner.workload_extraction(unit_info["assign"], unit_info["test"], unit_info["final"])

    
    def elective_space(self):
        """
        return different elective space based on the default course map
        """
        if (self.user_info.intake == 1):
            if (self.user_info.stream == 1 and self.user_info.year == 1 and self.user_info.sem == 1):
                return 1
            elif ((self.user_info.stream == 1 and self.user_info.year == 1 and self.user_info.sem == 2)):
                return 1
            elif ((self.user_info.stream == 1 and self.user_info.year == 2 and self.user_info.sem == 1)):
                return 1
            elif ((self.user_info.stream == 1 and self.user_info.year == 2 and self.user_info.sem == 2)):
                return 2
            elif ((self.user_info.stream == 1 and self.user_info.year == 3 and self.user_info.sem == 1)):
                return 2
            elif ((self.user_info.stream == 1 and self.user_info.year == 3 and self.user_info.sem == 2)):
                return 3
            elif ((self.user_info.stream == 2 and self.user_info.year == 1 and self.user_info.sem == 1)):
                return 1 
            elif ((self.user_info.stream == 2 and self.user_info.year == 1 and self.user_info.sem == 2)):
                return 2
            elif ((self.user_info.stream == 2 and self.user_info.year == 2 and self.user_info.sem == 1)):
                return 1
            elif ((self.user_info.stream == 2 and self.user_info.year == 2 and self.user_info.sem == 2)):
                return 1
            elif ((self.user_info.stream == 2 and self.user_info.year == 3 and self.user_info.sem == 1)):
                return 1
            elif ((self.user_info.stream == 2 and self.user_info.year == 3 and self.user_info.sem == 2)):
                return 2
        elif (self.user_info.intake == 2):
            if (self.user_info.stream == 1 and self.user_info.year == 1 and self.user_info.sem == 1):
                return 1
            elif ((self.user_info.stream == 1 and self.user_info.year == 1 and self.user_info.sem == 2)):
                return 1
            elif ((self.user_info.stream == 1 and self.user_info.year == 2 and self.user_info.sem == 1)):
                return 2
            elif ((self.user_info.stream == 1 and self.user_info.year == 2 and self.user_info.sem == 2)):
                return 1
            elif ((self.user_info.stream == 1 and self.user_info.year == 3 and self.user_info.sem == 1)):
                return 3
            elif ((self.user_info.stream == 1 and self.user_info.year == 3 and self.user_info.sem == 2)):
                return 2
            elif ((self.user_info.stream == 2 and self.user_info.year == 1 and self.user_info.sem == 1)):
                return 1 
            elif ((self.user_info.stream == 2 and self.user_info.year == 1 and self.user_info.sem == 2)):
                return 2
            elif ((self.user_info.stream == 2 and self.user_info.year == 2 and self.user_info.sem == 1)):
                return 1
            elif ((self.user_info.stream == 2 and self.user_info.year == 2 and self.user_info.sem == 2)):
                return 1
            elif ((self.user_info.stream == 2 and self.user_info.year == 3 and self.user_info.sem == 1)):
                return 2
            elif ((self.user_info.stream == 2 and self.user_info.year == 3 and self.user_info.sem == 2)):
                return 2
    
    def save_user_elective(self):
        """
        Check if user's JSON already has the elective info saved.
        If not, add new elective unit entries from self.elective_units into JSON.
        """
        user_folder = Path("user_info") / self.user_info.username
        user_folder.mkdir(parents=True, exist_ok=True)
        file_path = user_folder / "elective_units.json"

        # Load existing JSON data
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
        else:
            saved_data = {}

        # Track if anything new added
        new_added = False

        # Add new elective units if not already in JSON
        for unit_code, unit_info in self.all_electives_dict.items():
            if unit_code not in saved_data:
                saved_data[unit_code] = unit_info
                new_added = True

        # Save only if something new was added
        if new_added:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(saved_data, f, indent=4)
            print(f"Updated {file_path} with new elective units.")
        else:
            print("No new elective units to add. JSON already up-to-date.")
    

    def user_choice_choose_elective(self):
        """
        There is two way to choose elective where it can be entered manually (where user already have a choice)
        or
        Recommend by system (based on user interest)
        """
        #accept user input - ask about choose manually or smart planner help choose
        if (len(self.final_elective) < self.elective_space()):
            print("")
            print("Do you want to choose elective manually or recommend by system?")
            print("1. Enter Manually")
            print("2. System Recommendation")

            user_input = u.read_integer("Enter your choice: ",1,2)

            if (user_input == 1):
                chosen_elective = self.check_availability()
                self.display_elecive(chosen_elective)
                user_double_confirm = input("You want to add this unit as elective? [Y/N]: ")
                while (user_double_confirm != "Y"):
                    chosen_elective = self.check_availability()
                    self.display_elecive(chosen_elective)
                    user_double_confirm = input("You want to add this unit as elective? [Y/N]: ")
                self.final_elective.append(chosen_elective)
                print("Elective Added")
                print(f"Electives chosen: {len(self.final_elective)}/{self.elective_space()}")
            else:
                self.choose_elective_system_recommendation()
        else:
            print("No more elective spaces")
    #-----------------------Change Elective--------------------------
    def change_elective(self):
        """
        check the final elective list and list out all the added elective 
        - call the check_avaibility function to make sure the elective is available
        """
        if (len(self.final_elective) == 0):
            print("NO elective chosen")
        else:
            for i, unit in enumerate(self.final_elective):
                print(f"{i+1}: {unit}")
            user_input = u.read_integer("Choose elective to change: ",1, len(self.final_elective))
            chosen_elective = self.final_elective[user_input-1]
            chosen_elective = self.check_availability()
            self.display_elecive(chosen_elective)
            user_double_confirm = input("You want to add this unit as elective? [Y/N]: ")
            while (user_double_confirm != "Y"):
                chosen_elective = self.check_availability()
                self.display_elecive(chosen_elective)
                user_double_confirm = input("You want to add this unit as elective? [Y/N]: ")
            self.final_elective[user_input-1] = chosen_elective  
            print("Elective Changed Successfully")

    
    #------------------------Combine information----------------------------
    def combine_information(self):
        """
        Combine the core unit list with the elective list as well as the dictionary
        then we can view the unit_code and name if the final unit list is 4 (4 each sem)
        """
        final_unit_list = []
        final_unit_dict = self.core_planner.core_units_all | self.all_electives_dict
        final_unit_list = self.core_planner.filtered_core_list + self.final_elective

        print("")
        print(f"Current plan for Y{self.user_info.year}S{self.user_info.sem}")
        if (len(final_unit_list) == 4):
            for unit_code, unit_info in final_unit_dict.items():
                if (unit_code in final_unit_list):
                    print(f"{unit_code}: {unit_info["unit_name"]}")
        else:
            print("Incomplete / Error in planner")

        self.final_unit_list_for_current_sem = final_unit_list

    
    #-----------------------Save Info----------------------------------
    def saved_as_JSON(self):
        """
        create a new user folder (if havent)
        then the final version (checked using option 4) will saved as json and inside the user folder
        """
        json_dict = {}
        status = "planned"
        if (False in self.core_planner.list_fullfilled):
            print("Unable to save current planner")
            self.core_planner.check_core_prereq()
            
        else:
            if (len(self.final_unit_list_for_current_sem) == 4):
                for unit in self.final_unit_list_for_current_sem:
                    json_dict[unit]= status
                filename = f"user_info/{self.user_info.username}/Y{self.user_info.year}S{self.user_info.sem}_units.json"
                try:
                    os.mkdir(f"user_info/{self.user_info.username}")
                except FileExistsError:
                    pass
                with open(filename, "w") as f:
                    json.dump(json_dict, f, indent = 4)
                
                print(f"Planner saved for Y{self.user_info.year}S{self.user_info.sem}")
            else:
                print("Please review your information using option 4")

    #-------------------choose core or elecitve to serach---------------------------
    def choose_core_or_elective_list(self):
        """
        serach for core or elective which will call different function
        - show a list of available core / elective
        - user choose one and display all the info for that unit in details
        """
        print("You want to searched for core or elective unit?")
        print("1. Core Unit Lists")
        print("2. Elective Unit Lists")

        user_option = u.read_integer("Enter your choice: ", 1, 2)

        if (user_option == 1):
            self.core_planner.choose_core_list()
        else:
            user_input = self.manually_choose_based_on_level()
            chosen_elective = self.choose_elective_manually(user_input)
            self.display_elecive(chosen_elective)
        



#----------------------main----------------------------------
from enum import Enum
from core_planner import PlannerMenu
from update_result import ResultMenu
from update_units import UpdateMenu, UnitMenu, ViewMenu
import utilities as u

class MainMenu(Enum):
    PLAN_MY_UNIT = 0
    VIEW_PLANNER = 1
    UPDATE_RESULT = 2
    UPDATE_UNITS = 3
    QUIT = 4

class SmartUnitPlanner:
    def __init__(self):
        print("Welcome to Monash Smart Unit Planner\n")

    #print menu 
    def print_menu(self):
        """
        Print the menu options for the main menu
        """
        print("====Smart Course Planner Menu====")
        print("1. Plan my unit")
        print("2. View save plan")
        print("3. Enter my result")
        print("4. Update units")
        print("5. Quit")

    #return user option
    def user_option(self):
        """
        Return valid user option index 
        """
        while True:
            try:
                self.print_menu()
                user_option = u.read_integer("Enter an option: ", 1, len(MainMenu))
                return (user_option - 1)
            except ValueError:
                print("Please enter an valid option\n")


    def run(self):
        """
        Main Menu function is called here
        
        Choice 1 - Plan Menu
        Enter plan unit menu
        Choice 2 - View Current Planner 
        - COMING SOON
        Choice 3 - Enter result
        Choice 4 - Quit
        """
        planner = PlannerMenu()

        update_menu = UpdateMenu(
            planner.pass_info.user_info,      
            planner.update_result,
            planner.pass_info,
            planner.planner_core
        )
        while True:
            choice_index = self.user_option()
            choice = MainMenu(choice_index)

            match choice:
                case MainMenu.PLAN_MY_UNIT:
                    print("Entering plan unit menu")
                    planner.run()
                case MainMenu.VIEW_PLANNER:
                    print("Viewing current planner")
                    viewer = ViewMenu()
                    viewer.run()
                case MainMenu.UPDATE_RESULT:
                    print("Entering result menu")
                    result = ResultMenu()
                    result.run()
                case MainMenu.UPDATE_UNITS:
                    print("Entering units menu")
                    unit = UnitMenu(update_menu)
                    unit.run()
                case MainMenu.QUIT:
                    print("Bye!")
                    break
            
            print("")

if __name__ == "__main__":
    app = SmartUnitPlanner()
    app.run()

#---------------------------pass-info---------------------------
import utilities as u
import json
import os
from update_result import UpdateResult

class PreviousDetails():
    def __init__(self, user_info, update_results):
        """
        @param user_info that was entered previously 
        username - can access the file anywhere in the class
        info_check_requiremnet - message showing there is missing year/sem unit info 
        json_file_list - list of json file name that user had previously saved
        """
        self.user_info = user_info
        self.update_results = update_results
        self.info_check_requirement = []
        self.json_file_list = []
    
    def setup_user(self):
        """
        intialize user basic info such as their stream, year and sem
        """
        username, stream, year, sem, intake = self.user_info.user_basic_info()
        self.user_info.username = username
        self.user_info.stream = stream
        self.user_info.year = year
        self.user_info.sem = sem
        self.user_info.intake = intake
    
    def check_file_path(self, file_path, year, sem):
        """
        @param file_path - path that includes username
        @param year - current year that is checking
        @param sem - current sem checking
        check if file path exsits,
        if file not found, append the error message to a list
        """
        if os.path.exists(file_path):
            print(f"Found information for Y{year}S{sem}")
        else:
            string = (f"Cannot find information for Y{year}S{sem}")
            print(string)
            self.info_check_requirement.append(string)
    
    def check_previous_record(self):
        """
        accept user input to write the correct file path and call the check_file_path function 
            - to display error message
        this will check if required info (file exists for all previous year and sem)
        if not output the error message
        """
        self.info_check_requirement = [] 
        sem = self.user_info.sem
        year = self.user_info.year

        if (self.user_info.intake == 1 and year == 2 and sem == 1):
            sem = 2
        elif (self.user_info.intake == 1 and year == 2 and sem == 2):
            sem = 1
        #if not year 1 sem 1 start record information
        if (self.user_info.year == 1 and self.user_info.sem == 1):
            pass
        else:
            #check if previous record is available
            print("")
            file_path = f"user_info/{self.user_info.username}/Y{year}S{sem}_units.json"
            #check loop need to check if file exists for all previous year and sem
            # Move to previous semester first
            if sem == 1:
                sem = 2
                year -= 1
            else:
                sem -= 1

            # Then start checking from that previous sem backward
            while year > 0:
                file_path = f"user_info/{self.user_info.username}/Y{year}S{sem}_units.json"
                self.check_file_path(file_path, year, sem)

                if year == 1 and sem == 1:
                    break  # Stop once we reach Y1S1

                # Move to the next previous semester
                if sem == 1:
                    sem = 2
                    year -= 1
                else:
                    sem -= 1
        

    def check_json_planned(self):
        """
        Check if the JSON file results had been entered, or just planned.
        Only process files starting with 'Y' and ending with '.json'.
        """
        file_path = f"user_info/{self.user_info.username}"

        # Ensure folder exists
        while not os.path.exists(file_path):
            print("Please enter a valid username")
            self.user_info.username = input("Enter your username: ")
            file_path = f"user_info/{self.user_info.username}"

        # List all files in folder
        self.json_file_list = os.listdir(file_path)

        if self.user_info.year == 1 and self.user_info.sem == 1:
            return  # nothing to check for first semester

        for file in self.json_file_list:
            # Only process JSON files starting with 'Y'
            if not (file.startswith("Y") and file.endswith(".json")):
                continue

            file_path_full = os.path.join(file_path, file)
            try:
                with open(file_path_full, "r", encoding="utf-8") as f:
                    unit_passed_info_file = json.load(f)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue

            for unit_code, passed_info in unit_passed_info_file.items():
                if passed_info == "planned":
                    print("Please update your pass unit result")
                    self.update_results.access_unplanned_info()
                    break

    
    #-------------------check core---------------------------
    def saved_all_pass_unit(self):
        """
        Return a list of unit codes that the user has passed.
        Only loads valid JSON files (optionally starting with 'Y') from the user's folder.
        """
        all_unit_dict = {}
        passed_unit_list = []

        folder_path = f"user_info/{self.user_info.username}"
        if not os.path.exists(folder_path):
            return passed_unit_list

        for file in os.listdir(folder_path):
            # Skip non-JSON files
            if not file.endswith(".json"):
                continue
            if not file.startswith("Y"):
                continue

            file_path = os.path.join(folder_path, file)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    unit_info_json = json.load(f)
                all_unit_dict.update(unit_info_json)
            except (json.JSONDecodeError, UnicodeDecodeError):
                print(f"Skipping invalid or non-JSON file: {file}")
                continue

        # Build the passed unit list
        for unit_code, unit_passed_info in all_unit_dict.items():
            if unit_passed_info not in ("planned", "F"):
                passed_unit_list.append(unit_code)
        
        return passed_unit_list


#------------------------scrape-------------------------
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup 
import time

# --- Setup Chrome options ---
chrome_options = Options()
chrome_options.add_argument("--headless")  # run in background
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")

# --- Path to your chromedriver ---
service = Service("/home/wanyi/Downloads/chromedriver-linux64/chromedriver")
driver = webdriver.Chrome(service=service, options=chrome_options)

# --- Load the page ---
def get_info(year, unit_code):
    """
    load info based on the intake year and unit code and get the info such as unit name, sem available, workload

    @param year year to search for
    @param unit_code unit code to search for

    @return unit_name, semester_str, assign, test, final - which can replace the user database directly after changes made
    """
    url = f"https://handbook.monash.edu/{year}/units/{unit_code}"
    driver.get(url)

    time.sleep(3)

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    # --- Unit name ---
    h2_tag = soup.find("h2", {"data-testid": "ai-header"})
    if not h2_tag:

        return None, None, None, None, None, None  # return placeholders

    text = h2_tag.get_text(strip=True)
    unit_name = text.split("-", 1)[1].strip() if "-" in text else text.strip()

    # # --- Prerequisites ---
    # prereq_raw = "NONE"  
    # prereq_container = soup.find("div", id="Prerequisite")
    # if prereq_container:
    #     text = prereq_container.get_text(separator=" ", strip=True)
    #     fit_units = re.findall(r"\bFIT\d{4}\b", text)

    #     # Find which logical operator (AND/OR) appears first
    #     match = re.search(r"\b(AND|OR)\b", text, re.I)
    #     if match:
    #         first_op = match.group(1).upper()
    #         if first_op == "AND":
    #             prereq_raw = "a;" + ";".join(fit_units)
    #         elif first_op == "OR":
    #             prereq_raw = "o;" + ";".join(fit_units)
    #     elif fit_units:
    #         prereq_raw = ";".join(fit_units)

    # --- Semester available ---
    semester_headers = soup.find_all("h4", class_="css-3d3idg-AccordionRowComponent--SDefaultHeading evoq1ba0")
    semesters_set = set()
    for h in semester_headers:
        text = h.get_text(strip=True).upper()
        if "-MALAYSIA-" in text:
            if "S1" in text:
                semesters_set.add("1")
            if "S2" in text:
                semesters_set.add("2")
    semesters_str = ";".join(sorted(semesters_set, key=int))

    # --- Assessments ---
    try:
        # Wait for the assessment section to be present
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[id^='Assessment-']"))
        )
        
        # Find all accordion buttons and expand them
        accordion_buttons = driver.find_elements(By.CSS_SELECTOR, "div[id^='Assessment-'] button")
        
        for idx, button in enumerate(accordion_buttons):
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", button)
                time.sleep(0.3)
                
                aria_expanded = button.get_attribute("aria-expanded")
                
                if aria_expanded != "true":
                    driver.execute_script("arguments[0].click();", button)
                    time.sleep(0.5)
            except:
                pass
        
        time.sleep(1)
    except:
        pass

    # --- Updated page source ---
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    assign_list, test_list, final_list = [], [], []

    # --- Find the Assessment section ---
    assessment_section = soup.find("div", id=lambda x: x and x.startswith("Assessment-"))

    if assessment_section:
        # Find all h4 titles
        sections = assessment_section.find_all("h4", class_="css-3d3idg-AccordionRowComponent--SDefaultHeading")
        
        for section in sections:
            section_title = section.get_text(strip=True).lower()
            
            # Find the accordion row container
            accordion_row = section.find_parent("div", class_=lambda x: x and "SAccordionItemHeader" in str(x))
            
            if accordion_row:
                # Find the next sibling which should contain the expanded content
                content_div = accordion_row.find_next_sibling()
                
                if content_div:
                    # Find all CardBody divs within this content
                    value_divs = content_div.find_all("div", class_=lambda x: x and "CardBody" in str(x))
                    
                    # Look for the div containing "Value %"
                    for vdiv in value_divs:
                        text = vdiv.get_text(strip=True)
                        if "Value %" in text or "Value%" in text:
                            # Extract the percentage value
                            value = text.replace("Value %", "").replace("Value%", "").replace(":", "").strip()
                            
                            # Categorize based on section title
                            if "quiz" in section_title or "test" in section_title:
                                test_list.append(value)
                            elif "examination" in section_title or "final" in section_title:
                                final_list.append(value)
                            else:
                                assign_list.append(value)
                            break  # Found the value, move to next section

    # Convert lists to semicolon-separated strings
    assign = ";".join(assign_list) if assign_list else "NONE"
    test = ";".join(test_list) if test_list else "NONE"
    final = ";".join(final_list) if final_list else "NONE"
    # --- Result ---
    result = {
        unit_code: {
                "unit_name": unit_name, 
                "sem_available": semesters_str,
                "assign": assign,
                "test": test,
                "final": final
        }
    }

    return unit_name, semesters_str, assign, test, final




#--------------update_result--------------------
import os, json
import utilities as u
from enum import Enum

class ResultMenuEnum(Enum):
    UPDATE_RESULT_M = 0
    DISPLAY_RESULT = 1
    QUIT = 2

def print_result_menu():
    """
    Print out the option to choose
    """
    print("")
    print("====Update Result Menu====")
    print("1. Update Result")
    print("2. View Results")
    print("3. Quit")


def user_option():
    """
    Return user option index to match the ResultMenuEnum
    """
    while True:
        try:
            print_result_menu()
            user_option = u.read_integer("Enter an option: ", 1, len(ResultMenuEnum))
            return (user_option - 1)
        except ValueError:
            print("Please enter an valid option\n")

class UpdateResult():
    def __init__(self):
        """
        access username and file_path anywhere in the list
        json_list contain all the filename info of that user
        read_username_bool make sure username is entered once only 
        """
        self.username = ""
        self.file_path = ""
        self.json_list = []
        self.read_username_bool = False

    def read_username(self):
        """
        read username and turn the read_username_bool to True 
        thismake sure username is read once and it will remember for all function below
        """
        self.username = input("Enter your username: ")
        self.read_username_bool = True

    def read_json(self):
        """
        if user_name havent be recorded, read username here

        read the json file by accesing the folder path (containing username)
        a list of json_file name of that user is recorded
        """
        if (self.read_username_bool == False):
            self.read_username()
        self.json_list = []
        self.file_path = f"user_info/{self.username}" 
        #listdir list all file inside folder
        for file in os.listdir(self.file_path):
            if file.endswith(".json") and file.startswith("Y"):
                self.json_list.append(file)


    def check_valid_input(self, prompt):
        """
        let user enter the grade of that unit

        @return user correct grade (with correct format) is return
        """
        valid_input_list = ["HD", "D", "C", "P", "F"]
        updated_grade = input(prompt)
        while updated_grade not in valid_input_list:
            print("Invalid grade")
            updated_grade = input(prompt)
        return updated_grade
    
    def update_grade(self, unit_info_):
        """
        for grade that is mark planned- user can enter new grade
        for grade that previously had recorded - user can enter new grade (with their previous grade showing at the side)
        """
        for unit_code, grade in unit_info_.items():
            if (grade == "planned"):
                updated_grade = self.check_valid_input(f"{unit_code}: ")
                unit_info_[unit_code] = updated_grade
            else:
                prompt = f"{unit_code} (current grade: {grade}): "
                updated_grade = self.check_valid_input(prompt)
                unit_info_[unit_code] = updated_grade
        
    def show_grade(self):
        """
        show result option
        Show user result for all sem and year that had been recorded
        """
        if not self.read_username_bool:
            self.read_username()
        self.read_json()
        for file in self.json_list:
            full_path = os.path.join(self.file_path, file)
            name_only = file.split("_")[0]
            print(f"Result For {name_only}")

            with open(full_path, "r") as f:
                unit_info = json.load(f)

            for unit_code, grade in unit_info.items():
                print(f"{unit_code}: {grade}")
            print("")

    def access_unplanned_info(self):
        """
        Enter username (if haven't), check folder.
        Save in a list, check and call update grade function.
        Only process files that start with 'Y'.
        """
        self.read_json()
        
        for file in self.json_list:
            if not file.startswith("Y"):
                continue  # skip files that don't start with 'Y'
            
            full_path = os.path.join(self.file_path, file)
            name_only = file.split("_")[0]
            print(f"Result For {name_only}")

            # Read file into local variable
            with open(full_path, "r") as f:
                unit_info_ = json.load(f)

            # Update grades
            self.update_grade(unit_info_)

            # Save back to the same file
            with open(full_path, "w") as f:
                json.dump(unit_info_, f, indent=4)

            print("Saved updates for", file)
            print("")

        
class ResultMenu():
    def __init__(self):
        self.update_result = UpdateResult()
    
    def run(self):
        """
        1- Update result and save the result back to the json file
        2- Display all the previous year and sem result
        3- Quit this result menu
        """
        while True:
            choice_index = user_option()
            choice = ResultMenuEnum(choice_index)

            match choice:
                case ResultMenuEnum.UPDATE_RESULT_M:
                    self.update_result.access_unplanned_info()
                case ResultMenuEnum.DISPLAY_RESULT:
                    print("")
                    self.update_result.show_grade()
                case ResultMenuEnum.QUIT:
                    break

    
#----------------------update_unit------------------
from scrape import get_info
import json
import matplotlib.pyplot as plt
from pathlib import Path
from matplotlib.patches import Rectangle

class UpdateMenu():
    def __init__(self, user_info, update_result, pass_info, core_planner):
        """
        Class to handle course and unit information for user 

        @attribute user_info basic information about user such as useranme, enrolled_units
        @attribute update_result update result information to know user's prerequisite info
        @attribute pass_info information about passed units or completed prerequisite
        @attribute core_planner info about core planner
        """
        self.user_info = user_info
        self.update_result = update_result
        self.pass_info = pass_info
        self.core_planner = core_planner

    def core_dict_change_info(self):
        """
        Update the data if user feel like their info is incorrect, user can serach for that year and the requirements

        system will load user data and update the info back into the json file to accessed later at search units
        """
        # Load user paths
        username = input("Enter your username: ").strip()
        file_path_core = Path(f"user_info/{username}/core_units.json")
        file_path_elective = Path(f"user_info/{username}/elective_units.json")

        # Load core data
        if not file_path_core.is_file():
            print("core_units.json not found. Please generate it first.")
            return
        with open(file_path_core, "r", encoding="utf-8") as f:
            core_units_data = json.load(f)

        # Load elective data
        if not file_path_elective.is_file():
            print("elective_units.json not found. Please generate it first.")
            return
        with open(file_path_elective, "r", encoding="utf-8") as f:
            elective_units_data = json.load(f)

        # Ask for unit to update
        year = input("Enter your intake year: ").strip()
        user_unit_code = input("Enter unit code to update: ").strip().upper()
        unit_name, semesters_str, assign, test, final = get_info(year, user_unit_code)

        if unit_name is None:
            print(f"No unit found for {user_unit_code} in year {year}. Update canceled.")
            return

        # Update flag
        updated = False
        updated_info = None

        # Try updating in core_units.json
        if user_unit_code in core_units_data:
            core_units_data[user_unit_code].update({
                "unit_name": unit_name,
                "sem_available": semesters_str,
                "assign": assign,
                "test": test,
                "final": final
            })
            updated = True
            updated_info = core_units_data[user_unit_code]

        # Try updating in elective_units.json
        elif user_unit_code in elective_units_data:
            elective_units_data[user_unit_code].update({
                "unit_name": unit_name,
                "sem_available": semesters_str,
                "assign": assign,
                "test": test,
                "final": final
            })
            updated = True
            updated_info = elective_units_data[user_unit_code]

        if not updated:
            print(f"{user_unit_code} not found in either core or elective files.")
            return

        # Save changes
        with open(file_path_core, "w", encoding="utf-8") as f:
            json.dump(core_units_data, f, indent=4)
        with open(file_path_elective, "w", encoding="utf-8") as f:
            json.dump(elective_units_data, f, indent=4)

        # Display updated info
        print("\nUpdated Unit Information:")
        print(f"======= Unit Details - {user_unit_code} =======")
        print(f"[ {user_unit_code} ]: {updated_info['unit_name']}")
        print(f"Available Semester: {', '.join(self.core_planner.sem_extraction(updated_info['sem_available']))}")
        print("-----------------------------------")
        print("Workload")
        self.core_planner.workload_extraction(updated_info["assign"], updated_info["test"], updated_info["final"])
        print(f"\nChanges saved successfully to {username}'s files.")


class UnitMenu:
    def __init__(self, update_menu):
        self.update_menu = update_menu

    def run(self):
        # Access core planner through update_menu
        self.update_menu.core_dict_change_info()


class ViewMenu:
    def __init__(self):
        pass

    def read_user_semester_plan(self, username, year, sem):
        """
        Read a specific semester's planning JSON for a user
        Returns dict of {unit_code: status} or None if file doesn't exist
        """
        user_folder = Path("user_info") / username
        filename = f"Y{year}S{sem}_units.json"
        file_path = user_folder / filename
        
        if file_path.is_file():
            with open(file_path, 'r') as f:
                return json.load(f)
        return None

    def get_all_user_plans(self, username):
        """
        Read all semester plans for a user (Y1S1 through Y3S2)
        Only includes semesters that have saved JSON files
        Returns dict: {"Y1S1": {unit: status}, "Y1S2": {...}, ...}
        """
        all_plans = {}
        
        # Check all possible semesters
        for year in range(1, 4):  # Years 1-3
            for sem in range(1, 3):  # Semesters 1-2
                semester_key = f"Y{year}S{sem}"
                plan = self.read_user_semester_plan(username, year, sem)
                if plan is not None:  # Only add if file exists
                    all_plans[semester_key] = plan
        
        return all_plans

    def visualize_user_course(self, username):
        """
        Visualize all saved semesters for a specific user
        Shows passed (green) vs planned (gray) units
        Uses whatever units are in the user's JSON files
        """
        # Get all user's plans
        user_plans = self.get_all_user_plans(username)
        
        if not user_plans:
            print(f"No saved plans found for {username}")
            return
        
        fig, ax = plt.subplots(figsize=(12, len(user_plans) * 1.5))
        
        semesters = sorted(user_plans.keys())  # Y1S1, Y1S2, etc.
        y_pos = len(semesters) - 1
        
        for semester in semesters:
            # Semester label
            ax.text(-0.5, y_pos, semester, fontsize=12, fontweight='bold', 
                    ha='right', va='center')
            
            # Get all units for this semester from JSON
            semester_plan = user_plans[semester]
            units = list(semester_plan.keys())
            
            # Draw unit boxes
            for i, unit in enumerate(units):
                # Check status
                is_planned = semester_plan[unit] != "planned"
                color = 'lightgreen' if is_planned else 'lightgray'
                
                # Draw box
                rect = Rectangle((i * 1.1, y_pos - 0.4), 1.0, 0.8, 
                            facecolor=color, edgecolor='black', linewidth=1)
                ax.add_patch(rect)
                
                # Unit code
                ax.text(i * 1.1 + 0.5, y_pos, unit, fontsize=10, 
                    ha='center', va='center', fontweight='bold')
            
            y_pos -= 1
        
        # Dynamic x-axis limit based on max units in any semester
        max_units = max(len(plan) for plan in user_plans.values())
        ax.set_xlim(-1, max_units * 1.1 + 0.5)
        ax.set_ylim(-1, len(semesters))
        ax.axis('off')
        
        plt.title(f'Course Plan for {username}', fontsize=14, fontweight='bold')
        plt.tight_layout()
        # Save to user_info folder
        user_folder = Path("user_info") / username
        output_path = user_folder / f'{username}_course_structure.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Course structure saved to {output_path}")
        plt.close()

    def run(self):
        username = input("Enter username to view planner: ")
        
        # Check if user folder exists
        user_folder = Path("user_info") / username
        if not user_folder.exists():
            print(f"No planning data found for user: {username}")
        else:
            print(f"Viewing current planner for {username}...")
            self.visualize_user_course(username)

#---------------------utilities-------------------------
def read_integer(prompt, start, end):
    while True:
        try:
            user_input = int(input(prompt))
            if (start <= user_input <= end):
                return user_input
            else:
                print("Invalid input. Please try again")
        except ValueError:
            print("Invalid input. Please try again")

    