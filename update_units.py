from scrape import get_info
import io
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
    

    def load_unit_names(self, username):
        core_file = Path(f"user_info/{username}/core_units.json")
        elective_file = Path(f"user_info/{username}/elective_units.json")
        unit_names = {}
        
        if core_file.is_file():
            with open(core_file, 'r', encoding='utf-8') as f:
                core_units = json.load(f)
                for code, info in core_units.items():
                    unit_names[code] = info.get("unit_name", "")
        
        if elective_file.is_file():
            with open(elective_file, 'r', encoding='utf-8') as f:
                elective_units = json.load(f)
                for code, info in elective_units.items():
                    unit_names[code] = info.get("unit_name", "")
        
        return unit_names

    def visualize_user_course(self, username):
        """
        Visualize all saved semesters for a specific user
        Shows passed (green) vs planned (gray) units
        Displays unit code and unit name
        """
        # Get all user's plans
        user_plans = self.get_all_user_plans(username)
        if not user_plans:
            print(f"No saved plans found for {username}")
            return
        
        # Load unit names
        unit_names = self.load_unit_names(username)
        
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
                
                # Ultra long box dimensions
                box_width = 6.0
                box_height = 0.8
                x_offset = i * (box_width + 0.6)  # extra spacing to match
                
                # Draw box
                rect = Rectangle((x_offset, y_pos - box_height / 2), box_width, box_height, 
                                facecolor=color, edgecolor='black', linewidth=1)
                ax.add_patch(rect)
                
                # Unit code + name
                name_text = unit_names.get(unit, "")
                words = name_text.split()
                if len(words) > 3:
                    # Break into two lines after the third word
                    name_text = ' '.join(words[:3]) + '\n' + ' '.join(words[3:])
                display_text = f"{unit}\n{name_text}"

                ax.text(x_offset + box_width / 2, y_pos, display_text, fontsize=8, 
                        ha='center', va='center', fontweight='bold')


            
            y_pos -= 1
        
        # Dynamic x-axis limit based on max units in any semester
        max_units = max(len(plan) for plan in user_plans.values())
        ax.set_xlim(-1, max_units * (box_width + 0.6))
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
    
    def generate_course_png(self, username):
        """
        Generate the course structure PNG in-memory for a given user.
        Returns BytesIO or None if no plans exist.
        """
        user_plans = self.get_all_user_plans(username)
        if not user_plans:
            return None  # No plans found

        unit_names = self.load_unit_names(username)

        fig, ax = plt.subplots(figsize=(12, len(user_plans) * 1.5))
        semesters = sorted(user_plans.keys())
        y_pos = len(semesters) - 1

        for semester in semesters:
            ax.text(-0.5, y_pos, semester, fontsize=12, fontweight='bold', ha='right', va='center')
            semester_plan = user_plans[semester]
            units = list(semester_plan.keys())
            for i, unit in enumerate(units):
                is_planned = semester_plan[unit] != "planned"
                color = 'lightgreen' if is_planned else 'lightgray'
                box_width, box_height = 6.0, 0.8
                x_offset = i * (box_width + 0.6)
                rect = Rectangle((x_offset, y_pos - box_height / 2), box_width, box_height,
                                 facecolor=color, edgecolor='black', linewidth=1)
                ax.add_patch(rect)
                name_text = unit_names.get(unit, "")
                words = name_text.split()
                if len(words) > 3:
                    name_text = ' '.join(words[:3]) + '\n' + ' '.join(words[3:])
                display_text = f"{unit}\n{name_text}"
                ax.text(x_offset + box_width / 2, y_pos, display_text, fontsize=8, ha='center', va='center', fontweight='bold')
            y_pos -= 1

        max_units = max(len(plan) for plan in user_plans.values())
        ax.set_xlim(-1, max_units * (box_width + 0.6))
        ax.set_ylim(-1, len(semesters))
        ax.axis('off')
        plt.title(f'Course Plan for {username}', fontsize=14, fontweight='bold')
        plt.tight_layout()

        # Save to BytesIO
        img_bytes = io.BytesIO()
        plt.savefig(img_bytes, format='png', dpi=150, bbox_inches='tight')
        plt.close()
        img_bytes.seek(0)
        return img_bytes

    def run(self):
        username = input("Enter username to view planner: ")
        
        # Check if user folder exists
        user_folder = Path("user_info") / username
        if not user_folder.exists():
            print(f"No planning data found for user: {username}")
        else:
            print(f"Viewing current planner for {username}...")
            self.visualize_user_course(username)