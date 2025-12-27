from enum import Enum
from core_planner import PlannerMenu
from update_result import ResultMenu
from update_units import UpdateMenu, UnitMenu, ViewMenu
import utilities as u
import subprocess
import sys

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
                    print("Entering Plan my unit")
                    plan = PlannerMenu()
                    plan.run()
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