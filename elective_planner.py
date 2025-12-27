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
        Save the elective unit code as list to allow easier sorting
        Skip electives that already exist in the user's core_units.json
        """
        # Load the user's core units first
        core_units = {}
        core_path = f"user_info/{self.user_info.username}/core_units.json"

        if os.path.exists(core_path):
            with open(core_path, "r", encoding="utf-8") as f:
                core_units = json.load(f)

        with open("data/elective_units.csv", mode="r", encoding="utf-8-sig") as file:
            elective_unit_file = csv.DictReader(file)
            for line in elective_unit_file:
                unit_code = line["unit_code"].strip()

                # Skip if the elective already exists in core units
                if unit_code in core_units:
                    continue

                # Save into list
                self.all_electives_list.append(unit_code)

                # Save into dict
                self.all_electives_dict[unit_code] = {
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
        #Filter electives by level and availability
        available_units = self.get_available_electives_by_level(level)
        
        if not available_units:
            print("No available electives found for this level.")
            return []
        
        #Prepare descriptions
        descriptions = [self.all_electives_dict[unit]["description"] for unit in available_units]
        
        #Vectorize descriptions and user interest
        vectorizer = TfidfVectorizer(stop_words='english')
        vectors = vectorizer.fit_transform(descriptions + [user_interest])
        
        #Compute cosine similarity
        user_vector = vectors[-1]  # last vector is user input
        elective_vectors = vectors[:-1]
        similarities = cosine_similarity(user_vector, elective_vectors)[0]
        
        #Rank electives by similarity
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
        
        elif prereq_str.startswith('72;'):
            prereq_units = [u.strip() for u in prereq_str[3:].split(';')]
            return f"To take {unit_code}, you must have completed 12 units"


        elif prereq_str.startswith('o;'):
            prereq_units = [u.strip() for u in prereq_str[2:].split(';')]
            return f"To take {unit_code}, you must have completed at least one of these units: {', '.join(prereq_units)}"

        else:
            return f"To take {unit_code}, you must have completed: {prereq_str}"
        
    def get_unit_elective_info(self, chosen_elective):
        """
        Return detailed info about an elective unit as a dictionary,
        including formatted workload using core_planner's workload_extraction.
        """

        user_path = Path(f"user_info/{self.user_info.username}/elective_units.json")
        if not user_path.is_file():
            return None

        with open(user_path, "r", encoding="utf-8") as f:
            self.all_electives_dict = json.load(f)

        unit_info = self.all_electives_dict.get(chosen_elective)
        if not unit_info:
            return None

        # Ensure values are strings to avoid .split() errors
        assign = str(unit_info.get("assign", "0"))
        test = str(unit_info.get("test", "0"))
        final = str(unit_info.get("final", "0"))

        workload = self.core_planner.workload_extraction(assign, test, final)

        return {
            "code": chosen_elective,
            "name": unit_info.get("unit_name", ""),
            "description": unit_info.get("description", ""),
            "semesters": self.core_planner.sem_extraction(unit_info.get('sem_available', '')),
            "prerequisites": self.display_prerequisites(chosen_elective),
            "assign": workload.get("assign", "N/A"),
            "test": workload.get("test", "N/A"),
            "final": workload.get("final", "N/A"),
            "approved": unit_info.get("approved_elective", "N/A")
        }

    
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
                info = self.get_unit_elective_info(chosen_elective)
                print(json.dumps(info, indent=4))
                user_double_confirm = input("You want to add this unit as elective? [Y/N]: ")
                while (user_double_confirm != "Y"):
                    chosen_elective = self.check_availability()
                    info = self.get_unit_elective_info(chosen_elective)
                    print(json.dumps(info, indent=4))
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
            info = self.get_unit_elective_info(chosen_elective)
            print(json.dumps(info, indent=4))
            user_double_confirm = input("You want to add this unit as elective? [Y/N]: ")
            while (user_double_confirm != "Y"):
                chosen_elective = self.check_availability()
                info = self.get_unit_elective_info(chosen_elective)
                print(json.dumps(info, indent=4))
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
        for unit_code, unit_info in final_unit_dict.items():
            if (unit_code in final_unit_list):
                print(f"{unit_code}: {unit_info["unit_name"]}")

        self.final_unit_list_for_current_sem = final_unit_list

    
    #-----------------------Save Info----------------------------------
    def saved_as_JSON(self):
        """
        Save final planner as JSON. Returns True if successful, False otherwise.
        """
        json_dict = {}
        status = "planned"

        if False in self.core_planner.list_fullfilled:
            print("Unable to save current planner: core prerequisites not fulfilled")
            self.core_planner.check_core_prereq()
            return False  # indicate failure

        if len(self.final_unit_list_for_current_sem) != 4:
            print("Cannot save: exactly 4 units required")
            return False  # indicate failure

        for unit in self.final_unit_list_for_current_sem:
            json_dict[unit] = status

        filename = f"user_info/{self.user_info.username}/Y{self.user_info.year}S{self.user_info.sem}_units.json"
        os.makedirs(f"user_info/{self.user_info.username}", exist_ok=True)

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(json_dict, f, indent=4)

        print(f"Planner saved for Y{self.user_info.year}S{self.user_info.sem}")
        return True  # indicate success


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
            info = self.get_unit_elective_info(chosen_elective)
            print(json.dumps(info, indent=4))


