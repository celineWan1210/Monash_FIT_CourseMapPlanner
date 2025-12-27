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

    