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
            return True
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
        
        return len(self.info_check_requirement) == 0
        

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
            return True # nothing to check for first semester

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
                    # self.update_results.access_unplanned_info()
                    return False  

        return True
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


