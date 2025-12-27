from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS
from pathlib import Path
from scrape import get_info 
import google.generativeai as genai
import json
import os


from core_planner import PlannerForCore, UserInfo
from elective_planner import PlannerForElective
from pass_info import PreviousDetails
from update_result import UpdateResult
from update_units import ViewMenu
from chat import UnitAdvisorAI
from forum import ForumManager
from utilities import initialize_user 

import re

app = Flask(__name__, static_folder='static', static_url_path='')
vm = ViewMenu()
CORS(app)

# Initialize global UpdateResult instance
update_result = UpdateResult()


@app.route('/')
def index():
    """
    Send the 'index.html' file from the 'static' directory
    This allows Flask to serve the main frontend page when the user visits the root URL
    """
    return send_from_directory('static', 'main.html')

@app.route('/plan')
def plan_units():
    """
    Serve the Plan My Unit page (your existing index.html)
    """
    return send_from_directory('static', 'index.html')


@app.route('/results')
def enter_results():
    """
    Serve the Enter Results page
    """
    return send_from_directory('static', 'results.html')


@app.route('/update')
def update_units():
    """
    Serve the Update Units page
    """
    return send_from_directory('static', 'update.html')

@app.route('/chat')
def chat_page():
    """
    Serve the chat interface page
    """
    return send_from_directory('static', 'chat.html')

@app.route('/forum')
def forum_page():
    """
    Serve the forum interface page
    """
    return send_from_directory('static', 'forum.html')


@app.route('/api/check-unit-availability', methods=['POST'])
def check_unit_availability():
    """
    Check if a core unit is available this semester and if prerequisites are fulfilled.
    """
    import os, json

    try:
        data = request.json
        print("Received JSON:", data)

        if not data:
            return jsonify({'success': False, 'error': 'No JSON data received'}), 400

        # Extract inputs
        username = data.get('username')
        unit_code = data.get('unit_code')
        try:
            stream = int(data.get('stream', 0))
            year = int(data.get('year', 0))
            sem = int(data.get('semester', 0))
            intake = int(data.get('intake', 0))
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Invalid numeric values'}), 400

        if not all([username, unit_code, stream, year, sem, intake]):
            return jsonify({'success': False, 'error': 'Missing required parameters'}), 400

        # Initialize user info
        user_info = UserInfo()
        user_info.user_basic_info_web(username, stream, year, sem, intake)

        # Load previous records
        update_result = UpdateResult()
        pass_info = PreviousDetails(user_info, update_result)
        completed_units = pass_info.saved_all_pass_unit()

        # Read core units directly from JSON
        json_path = os.path.join('user_info', username, 'core_units.json')
        if not os.path.exists(json_path):
            return jsonify({'success': False, 'error': 'core_units.json not found'}), 404

        with open(json_path, 'r') as f:
            core_units_all = json.load(f)

        # Determine current semester
        if intake == 2 and sem == 1:
            current_sem = 2
        elif intake == 2 and sem == 2:
            current_sem = 1
        elif intake == 1 and sem == 1:
            current_sem = 1
        elif intake == 1 and sem == 2:
            current_sem = 2
        else:
            current_sem = sem

        # Get unit info
        unit_info = core_units_all.get(unit_code)
        if not unit_info:
            return jsonify({'success': False, 'error': f'Unit {unit_code} not found'}), 404

        # Check semester availability
        sem_available_raw = unit_info.get('sem_available', '')
        sem_list = [int(s) for s in sem_available_raw.split(";") if s.strip().isdigit()]
        available_this_sem = current_sem in sem_list

        # Build prereq_dict same as start-planning
        prereq_dict = {u: info.get("prereq", "NONE") for u
        , info in core_units_all.items()}

        # Check if prerequisites are fulfilled
        planner_core = PlannerForCore(user_info, pass_info)
        prereq_fulfilled = planner_core.can_take_unit(unit_code, prereq_dict, completed_units)

        # Determine reason if cannot take
        reason = ""
        if not available_this_sem and not prereq_fulfilled:
            reason = "Not available this semester and prerequisites not met"
        elif not available_this_sem:
            reason = "Not available this semester"
        elif not prereq_fulfilled:
            reason = "Prerequisites not met"

        return jsonify({
            'success': True,
            'available_this_sem': available_this_sem,
            'prereq_fulfilled': prereq_fulfilled,
            'can_take': available_this_sem and prereq_fulfilled,
            'reason': reason,
            'unit_info': {
                'code': unit_code,
                'name': unit_info.get('unit_name', unit_code),
                'sem_available': sem_list,
                'prereq': unit_info.get('prereq', 'NONE')
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/start-planning', methods=['POST'])
def start_planning():
    """
    Receive user data from frontend and verify previous semester record 
    It will check if all the result is updated and return list of correct core units

    @returns 
    Java resposnse 
    - sucess (bool) - show whether planning process is sucessfull
    - core units (list) - list of core units
    - semester_name (str) - name of that semester (July or February)
    - current_sem (int) - current semester (1, 2)
    - error (str) - planning unsucessful 
    """
    try:
        data = request.get_json()
        print("Received data:", data)

        user_info, core_planner, elective_planner = initialize_user(data)
        print("initialize_user done")

        from pass_info import PreviousDetails
        from update_result import UpdateResult

        update_result = UpdateResult()
        pass_info = PreviousDetails(user_info, update_result)
        deferred_cores = get_deferred_cores(user_info)

        # Get semester alert message
        semester_name = ""
        if user_info.intake == 2 and user_info.sem == 1:
            semester_name = "July Semester"
            core_planner.current_sem = 2
        elif user_info.intake == 2 and user_info.sem == 2:
            semester_name = "February Semester"
            core_planner.current_sem = 1
        elif user_info.intake == 1 and user_info.sem == 1:
            semester_name = "February Semester"
            core_planner.current_sem = 1
        elif user_info.intake == 1 and user_info.sem == 2:
            semester_name = "July Semester"
            core_planner.current_sem = 2

        # Proceed if all good
        core_units_list = []
        for code in getattr(core_planner, 'filtered_core_list', []):
            unit_info = core_planner.filtered_core_units[code]
            
            # Get prerequisite fulfillment (reusing elective logic)
            prereq_dict = {u: info.get("prereq", "NONE") for u, info in core_planner.filtered_core_units.items()}
            prereq_fulfilled = core_planner.can_take_unit(code, prereq_dict, core_planner.pass_info.saved_all_pass_unit())
            
            core_units_list.append({
                'code': code,
                'name': unit_info['unit_name'],
                'description': unit_info['description'],
                'sem_available': unit_info['sem_available'],
                'prereq': unit_info['prereq'],
                'assign': unit_info['assign'],
                'test': unit_info['test'],
                'final': unit_info['final'],
                'prereq_fulfilled': prereq_fulfilled  
            })


        return jsonify({
            'success': True,
            'core_units': core_units_list,
            'semester_name': semester_name,
            'current_sem': core_planner.current_sem,
            'deferred_cores': deferred_cores  # Add this line
        })


    except Exception as e:
        import traceback
        print("ERROR:", e)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

    
@app.route('/api/core-unit-info', methods=['POST'])
def core_unit_info():
    """
    retrieve detailed information about a specific core units
    Receive username and unit code from the frontend and return detail information for the requested unit

    @returns
    JSON response:
    - sucess (bool): show if request is sucessful
    - unit (dict): information about reqeusted unit
    - error (str): error message indicating this does not work
    """
    try:
        data = request.json
        username = data.get('username')
        unit_code = data.get('unit_code')

        if not username or not unit_code:
            return jsonify({'success': False, 'error': 'Missing username or unit_code'}), 400

        user_info = UserInfo()
        user_info.username = username

        planner = PlannerForCore(user_info, None)
        planner.read_core_unit() 
        unit_data = planner.get_unit_core_info(unit_code)

        if not unit_data:
            return jsonify({'success': False, 'error': 'Unit not found or core_units.json missing'}), 404

        return jsonify({'success': True, 'unit': unit_data})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/get-electives', methods=['POST'])
def get_electives():
    """
    retrieve user information from frontend, generate a list of available elective units 
    filter the core unit and elective that are already chosen and check for semester and prereq

    @returns
    JSON response
    - success (bool): Whether the request was successful
    - electives (list): List of available elective units with details
    - elective_space (int): Number of elective slots available
    - current_chosen (int): Number of electives already selected
    - error (str): Error message if any issue occurs
    """
    try:
        data = request.json
        user_info, core_planner, elective_planner = initialize_user(data)

        # Build electives list while filtering core and unavailable units
        electives_list = []
        for unit_code, unit_info in elective_planner.all_electives_dict.items():
            is_core = unit_code in core_planner.core_units_all
            already_chosen = unit_code in elective_planner.final_elective
            available_sem = elective_planner.check_elective_available_sem(unit_code)
            prereq_fulfilled = elective_planner.check_elective_preq(unit_code)

            if is_core or already_chosen:
                continue  # skip core and already chosen units

            electives_list.append({
                'code': unit_code,
                'name': unit_info['unit_name'],
                'description': unit_info['description'],
                'level': int(unit_code[3]),
                'sem_available': unit_info['sem_available'],
                'prereq': unit_info['prereq'],
                'assign': unit_info['assign'],
                'test': unit_info['test'],
                'final': unit_info['final'],
                'available_this_sem': available_sem,
                'prereq_fulfilled': prereq_fulfilled,
                'approved': unit_info['approved_elective']
            })

        # Get deferred cores
        deferred_cores = get_deferred_cores(user_info)

        # Calculate elective space
        elective_space = elective_planner.elective_space()

        # Subtract deferred cores (they take up space)
        elective_space -= len(deferred_cores)

        if elective_space < 0:
            elective_space = 0

        current_chosen = elective_space

        return jsonify({
            'success': True,
            'electives': electives_list,
            'elective_space': elective_space,
            'current_chosen': current_chosen
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/recommend-electives', methods=['POST'])
def recommend_electives():
    """
    recommend elective units based on the user's interests and study level
    initializes the user and planner objects, then uses a recommendation
    algorithm to suggest suitable elective units

    @returns 
    JSON response:
    - success (bool): Whether the recommendation process was successful.
    - recommendations (list): List of recommended elective units 
    """
    try:
        data = request.json
        username = data.get('username')
        level = int(data.get('level'))
        interest = data.get('interest')
        already_chosen = data.get('already_chosen', [])

        # Initialize user and planners
        user_info, core_planner, elective_planner = initialize_user(data)
        elective_planner.final_elective = already_chosen

        recommended = elective_planner.recommend_electives_smart(level, interest, num_reco=5)

        recommendations = []
        for unit_code in recommended:
            if unit_code in core_planner.core_units_all or unit_code in already_chosen:
                continue
            unit_info = elective_planner.all_electives_dict[unit_code]
            recommendations.append({
                'code': unit_code,
                'name': unit_info['unit_name'],
                'description': unit_info['description'],
                'level': int(unit_code[3])
            })

        return jsonify({'success': True, 'recommendations': recommendations})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    

@app.route('/api/elective-unit-info', methods=['POST'])
def elective_unit_info():
    """
    Show elective information in a nice format
    """
    try:
        data = request.json
        username = data.get('username')
        unit_code = data.get('unit_code')

        if not username or not unit_code:
            return jsonify({'success': False, 'error': 'Missing username or unit_code'}), 400

        user_info = UserInfo()
        user_info.username = username

        core_planner = PlannerForCore(user_info, None)
        core_planner.read_core_unit()

        elective_planner = PlannerForElective(user_info, core_planner)
        elective_planner.read_elective()
        elective_planner.save_user_elective()

        # Use refactored display_elecive
        unit_data = elective_planner.get_unit_elective_info(unit_code)

        if 'error' in unit_data:
            return jsonify({'success': False, 'error': unit_data['error']}), 404

        return jsonify({'success': True, 'unit': unit_data})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

def get_deferred_cores(user_info):
    """
    Read all deferred units from deferred_units.json
    Only return units that are not already planned in any Y{year}S{sem}_units.json
    """
    deferred_path = Path(f"user_info/{user_info.username}/deferred_units.json")
    if not deferred_path.exists():
        return []

    with open(deferred_path, "r", encoding="utf-8") as f:
        deferred_data = json.load(f)

    user_folder = Path(f"user_info/{user_info.username}")
    planned_units = set()
    # Loop through all Y{year}S{sem}_units.json
    for file in user_folder.glob("Y*S*_units.json"):
        with open(file, "r", encoding="utf-8") as f:
            planned_units.update(json.load(f).keys())

    # Filter out deferred units that are already planned
    deferred_list = [
        {"code": code, "from_semester": sem_info}
        for code, sem_info in deferred_data.items()
        if code not in planned_units
    ]
    return deferred_list


@app.route('/api/save-plan', methods=['POST'])
def save_plan():
    """
    Save plan into two separate JSONs:
    - Y{year}S{sem}_units.json for planned units
    - deferred_units.json for all deferred units
    """
    try:
        data = request.json
        username = data.get('username')
        year = int(data.get('year'))
        sem = int(data.get('semester'))
        stream = int(data.get('stream'))  
        intake = int(data.get('intake')) 
        core_units = data.get('core_units', [])  # Selected cores
        deferred_cores = data.get('deferred_cores', [])  # Deferred cores
        electives = data.get('electives', [])

        # --- initialize user info ---
        user_info = UserInfo()
        user_info.username = username
        user_info.year = year
        user_info.sem = sem
        user_info.stream = stream  
        user_info.intake = intake  

        # --- pass info check ---
        pass_info = PreviousDetails(user_info, update_result)
        completed_units = pass_info.saved_all_pass_unit()

        # --- core planner ---
        core_planner = PlannerForCore(user_info, pass_info)
        core_planner.read_core_unit()  
        selected_core_codes = [u['code'] for u in core_units]
        core_planner.filtered_core_list = selected_core_codes

        # --- prerequisite check ---
        unmet_prereqs = core_planner.check_core_prereq()
        if unmet_prereqs:
            return jsonify({
                'success': False,
                'error': f"Cannot save. Prerequisites not met for: {', '.join(unmet_prereqs)}"
            }), 400

        # --- Save planned units into Y{year}S{sem}_units.json ---
        planner = PlannerForElective(user_info, core_planner)
        planner.final_unit_list_for_current_sem = selected_core_codes + [e['code'] for e in electives]
        planned_dict = {unit: "planned" for unit in planner.final_unit_list_for_current_sem}

        user_folder = Path(f"user_info/{username}")
        user_folder.mkdir(parents=True, exist_ok=True)
        planned_filename = user_folder / f"Y{year}S{sem}_units.json"

        with open(planned_filename, "w", encoding="utf-8") as f:
            json.dump(planned_dict, f, indent=4)

        # --- Save deferred units into deferred_units.json ---
        deferred_path = user_folder / "deferred_units.json"

        # Load old deferred data if exists
        if deferred_path.exists():
            with open(deferred_path, "r", encoding="utf-8") as f:
                deferred_data = json.load(f)
        else:
            deferred_data = {}

        # Add new deferred units with source semester info
        for d in deferred_cores:
            deferred_data[d] = f"Y{year}S{sem}"

        # Remove any deferred units that were reselected this semester
        for u in selected_core_codes:
            if u in deferred_data:
                deferred_data.pop(u)

        with open(deferred_path, "w", encoding="utf-8") as f:
            json.dump(deferred_data, f, indent=4)

        return jsonify({
            'success': True,
            'message': f'Plan saved for Y{year}S{sem}',
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    


@app.route('/api/get-results', methods=['POST'])
def get_results():
    """
    Retrieve all semester results for a user
    Returns all Y{year}S{sem}_units.json files
    """
    try:
        data = request.json
        username = data.get('username')
        
        if not username:
            return jsonify({'success': False, 'error': 'Username is required'}), 400
        
        user_folder = Path(f"user_info/{username}")
        
        if not user_folder.exists():
            return jsonify({'success': False, 'error': f'User {username} not found'}), 404
        
        results = {}
        
        # Find all semester files (Y1S1_units.json, Y1S2_units.json, etc.)
        for file in user_folder.glob("Y*S*_units.json"):
            # Extract semester name from filename (e.g., "Y1S1_units.json" -> "Y1S1")
            semester_name = file.stem.split('_')[0]
            
            with open(file, 'r', encoding='utf-8') as f:
                units = json.load(f)
                results[semester_name] = units
        
        return jsonify({
            'success': True,
            'results': results,
            'username': username
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/save-results', methods=['POST'])
def save_results():
    """
    Save updated results back to the user's JSON files
    """
    try:
        data = request.json
        username = data.get('username')
        results = data.get('results')
        
        if not username or not results:
            return jsonify({'success': False, 'error': 'Username and results are required'}), 400
        
        user_folder = Path(f"user_info/{username}")
        
        if not user_folder.exists():
            return jsonify({'success': False, 'error': f'User {username} not found'}), 404
        
        # Save each semester's results
        for semester, units in results.items():
            file_path = user_folder / f"{semester}_units.json"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(units, f, indent=4)
        
        return jsonify({
            'success': True,
            'message': f'Results saved for {len(results)} semester(s)'
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/view')
def view_plans():
    """
    Serve the View Saved Plans page or generate the course PNG
    Automatically reads the username from cookie set in /result
    """
    username = request.cookies.get("username")  #read from cookie

    if not username:
        return "Username not found. Please load results first.", 400

    user_folder = Path("user_info") / username
    if not user_folder.exists():
        return f"No data found for user {username}", 404

    # Generate PNG using ViewMenu
    vm = ViewMenu()
    vm.visualize_user_course(username)

    output_file = f"{username}_course_structure.png"
    return send_from_directory(user_folder, output_file)


@app.route('/api/update-unit', methods=['POST'])
def update_unit():
    """
    Update unit information by scraping Monash Handbook
    Uses the get_info function from scrape.py
    USe sem_extraction() and workload_extraction() for proper formatting
    """
    try:
        data = request.json
        username = data.get('username')
        intake_year = data.get('intake_year')
        unit_code = data.get('unit_code', '').strip().upper()

        if not all([username, intake_year, unit_code]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: username, intake_year, or unit_code'
            }), 400

        # Check if user exists
        user_folder = Path(f"user_info/{username}")
        if not user_folder.exists():
            return jsonify({
                'success': False,
                'error': f'User {username} not found. Please complete unit planning first.'
            }), 404

        # Scrape unit info from Monash Handbook
        unit_name, semesters_str, assign, test, final = get_info(intake_year, unit_code)

        if unit_name is None:
            return jsonify({
                'success': False,
                'error': f'Unit {unit_code} not found in {intake_year} handbook. Please check the unit code and year.'
            }), 404

        # Format semester information inline
        # Converts "1;2" → ["February Semester", "July Semester"]
        semesters_list = []
        if semesters_str and semesters_str.strip().upper() != "NONE":
            for sem in semesters_str.split(";"):
                sem = sem.strip()
                if sem == "1":
                    semesters_list.append("February Semester")
                elif sem == "2":
                    semesters_list.append("July Semester")
        
        # Format workload using workload_extraction()
        # Converts "20;30", "10", "60" -> {"assign": "20%, 30%", "test": "10%", "final": "60%"}
        try:
            user_info_temp = UserInfo()
            user_info_temp.username = username
            temp_planner = PlannerForCore(user_info_temp, None)
            workload = temp_planner.workload_extraction(assign, test, final)
        except Exception:
            # Fallback if extraction fails
            workload = {
                'assign': assign or 'None',
                'test': test or 'None',
                'final': final or 'None'
            }

        # Load user's core and elective units
        core_file = user_folder / "core_units.json"
        elective_file = user_folder / "elective_units.json"

        updated = False
        updated_location = None

        # Try updating core units
        if core_file.exists():
            with open(core_file, 'r', encoding='utf-8') as f:
                core_units_data = json.load(f)

            if unit_code in core_units_data:
                core_units_data[unit_code].update({
                    "unit_name": unit_name,
                    "sem_available": semesters_str,  
                    "assign": assign,                 
                    "test": test,                     
                    "final": final                    
                })
                
                with open(core_file, 'w', encoding='utf-8') as f:
                    json.dump(core_units_data, f, indent=4)
                
                updated = True
                updated_location = "core_units.json"

        # Try updating elective units
        if not updated and elective_file.exists():
            with open(elective_file, 'r', encoding='utf-8') as f:
                elective_units_data = json.load(f)

            if unit_code in elective_units_data:
                elective_units_data[unit_code].update({
                    "unit_name": unit_name,
                    "sem_available": semesters_str,  
                    "assign": assign,                 
                    "test": test,                     
                    "final": final                    
                })
                
                with open(elective_file, 'w', encoding='utf-8') as f:
                    json.dump(elective_units_data, f, indent=4)
                
                updated = True
                updated_location = "elective_units.json"

        if not updated:
            return jsonify({
                'success': False,
                'error': f'{unit_code} not found in your core or elective units. You may need to add it to your course plan first.'
            }), 404

        #Return formatted info for display (not for storage)
        return jsonify({
            'success': True,
            'message': f'Unit {unit_code} updated successfully',
            'updated_file': updated_location,
            'unit_info': {
                'code': unit_code,
                'name': unit_name,
                'semesters': semesters_str,         
                'semesters_list': semesters_list,     
                'assign': workload['assign'],        
                'test': workload['test'],             
                'final': workload['final']            
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500



@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Handle chat messages and route them to UnitAdvisorAI.
    Supports multiple conversation intents:
    recommendation, workload, comparison, readiness analysis, etc.
    """
    try:
        data = request.get_json()

        api_key = data.get('apiKey')
        if not api_key:
            return jsonify({
                'success': False, 
                'error': 'API key not provided. Please set your API key in the chat interface.'
            })
        
        # Initialize advisor with user's API key
        advisor = UnitAdvisorAI(api_key=api_key)

        # === User Metadata ===
        username = data.get('username')
        intake = data.get('intake')
        stream = data.get('stream')
        year = data.get('year')
        semester = data.get('semester')
        interest = data.get('interest', '')

        # === User Message ===
        message = data.get('message', '').strip().lower()

        if not username or not message:
            return jsonify({'success': False, 'error': 'Missing username or message'}), 400

        response = None

        # === Unit Recommendations ===
        if any(word in message.lower() for word in ['recommend', 'suggest', 'choose']):
            interest_to_use = interest if interest else message.replace('recommend', '').replace('suggest', '').strip()
            if not interest_to_use:
                response = "💡 Please specify what you're interested in (e.g., 'recommend data-related units')."
            else:
                response = advisor.recommend_units(
                    username=username,
                    intake=intake,
                    stream=stream,
                    year=year,
                    semester=semester,
                    interest=interest_to_use
                )

        # === Workload / Difficulty Check ===
        elif any(keyword in message.lower() for keyword in ['workload', 'difficulty']):
            planned_units = advisor.load_planned_units(username, year, semester)
            if not planned_units:
                response = f"⚠️ No planned units found for Y{year}S{semester}. Please ensure you've added them first."
            else:
                response = advisor.show_workload(username, year, semester, planned_units)

        # === Show Current Plan ===
        elif any(keyword in message.lower() for keyword in ['current plan', 'taken', 'my units', 'show plan']):
            response = advisor.show_all_semesters_with_info(username)

        # === Intent 4: Compare Units ===
        elif 'compare' in message:
            unit_codes = re.findall(r'FIT\d{4}', message.upper())
            if len(unit_codes) >= 2:
                response = advisor.compare_unit_readiness(
                    username=username,
                    unit_codes=unit_codes,
                    year=year,
                    semester=semester,
                    stream=stream,
                    intake=intake,
                    interest=interest
                )
            else:
                response = "To compare units, type something like: 'compare FIT2004 and FIT3155'."

        # === Single Unit Readiness Deep Dive ===
        elif any(word in message.lower() for word in ['can i take', 'should i add', 'should i take', 'hard', 'can i add', 'detail', 'details']):
            unit_codes = re.findall(r'FIT\d{4}', message.upper())
            if unit_codes:
                unit_code = unit_codes[0]
                
                # Check if this is an "add unit" scenario
                is_adding = any(phrase in message.lower() for phrase in ['add'])
                
                if is_adding:
                    # User wants to know: "Should I ADD FIT3143 to my semester?"
                    response = advisor.analyze_adding_unit(
                        username=username,
                        new_unit_code=unit_code,
                        year=year,
                        semester=semester,
                        stream=stream,
                        intake=intake
                    )
                else:
                    # User wants to know:
                    response = advisor.analyze_unit_readiness_single(
                        username=username,
                        unit_code=unit_code,
                        year=year,
                        semester=semester,
                        stream=stream,
                        intake=intake
                    )
            else:
                response = "Please include a unit code (e.g., 'can I take FIT3155?' or 'should I add FIT3143?')."

        # === Semester Readiness (Full Semester Overview) ===
        elif any(phrase in message.lower() for phrase in ['analyze', 'analysis', 'analyze semester', 'review', 'am i ready', 'semester readiness']):
            response = advisor.analyze_semester_readiness(
                username=username,
                year=year,
                semester=semester,
                stream=stream,
                intake=intake
            )

        # === Sentiment / Feedback Summary ===
        elif any(word in message.lower() for word in ['feedback', 'others', 'opinions', 'community']):
            unit_codes = re.findall(r'FIT\d{4}', message.upper())
            if unit_codes:
                response = advisor.summarize_unit_sentiment(unit_codes[0])
            else:
                response = "Please include a unit code (e.g., 'show feedback for FIT1047')."

        # === Resource / Study Advice ===
        elif any(word in message.lower() for word in ['resource', 'material', 'study help', 'guide', 'overview']):
            unit_codes = re.findall(r'FIT\d{4}', message.upper())
            if unit_codes:
                response = advisor.summarize_unit_overview(username, unit_codes[0])
            else:
                response = "Please include a unit code (e.g., 'show resources for FIT1008')."

        # === General AI Help / Planning ===
        else:
            all_units = advisor.load_all_units(username)
            matched = False
            for code, info in all_units.items():
                if code.lower() in message:
                    response = advisor.ask_ai_about_unit(code, info, message)
                    matched = True
                    break
            if not matched:
                if any(phrase in message.lower() for phrase in [
                    'plan semester', 'plan my', 'should i take',
                    'what units should', 'which units should', 'help me choose'
                ]):
                    response = "🧭 To get personalized planning help, please type 'recommend units for me' and specify your interest!"
                else:
                    response = advisor.general_advice(username, message, interest=interest)

        return jsonify({'success': True, 'response': response})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/forum/units', methods=['POST'])
def get_forum_units():
    """
    Get all available units for the forum
    """
    try:
        data = request.json
        username = data.get('username')
        
        if not username:
            return jsonify({'success': False, 'error': 'Username is required'}), 400
        
        forum_manager = ForumManager(username)
        all_units = forum_manager.load_all_units()
        
        # Get discussion stats for each unit
        units_with_stats = []
        for code, info in all_units.items():
            stats = forum_manager.get_discussion_stats(code)
            units_with_stats.append({
                'code': code,
                'name': info['name'],
                'description': info['description'],
                'type': info['type'],
                'discussion_count': {
                    'general': stats['general'],
                    'resources': stats['resources'],
                    'private': stats['private']
                }
            })
        
        return jsonify({
            'success': True,
            'units': units_with_stats
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/forum/discussions', methods=['POST'])
def get_discussions():
    """
    Get discussions for a specific unit and tag
    """
    try:
        data = request.json
        username = data.get('username')
        unit_code = data.get('unit_code')
        tag = data.get('tag')
        
        if not all([username, unit_code, tag]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        if tag not in ['general', 'resources', 'private']:
            return jsonify({'success': False, 'error': 'Invalid tag'}), 400
        
        forum_manager = ForumManager(username)
        
        # Check access permission for private discussions
        if tag == 'private':
            # For private, we need to check if this is the user's own private section
            if username != data.get('request_username', username):
                return jsonify({
                    'success': False, 
                    'error': 'Access denied: Private discussions are only visible to the owner'
                }), 403
        
        discussions = forum_manager.get_unit_discussions(unit_code, tag)
        
        return jsonify({
            'success': True,
            'discussions': discussions,
            'unit_code': unit_code,
            'tag': tag
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/forum/add-discussion', methods=['POST'])
def add_discussion():
    """
    Create a new discussion thread
    """
    try:
        data = request.json
        username = data.get('username')
        unit_code = data.get('unit_code')
        tag = data.get('tag')
        title = data.get('title')
        content = data.get('content')
        
        if not all([username, unit_code, tag, title, content]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        if tag not in ['general', 'resources', 'private']:
            return jsonify({'success': False, 'error': 'Invalid tag'}), 400
        
        forum_manager = ForumManager(username)
        result = forum_manager.add_discussion(unit_code, tag, title, content)
        
        return jsonify(result)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/forum/add-reply', methods=['POST'])
def add_reply():
    """
    Add a reply to an existing discussion
    """
    try:
        data = request.json
        username = data.get('username')
        unit_code = data.get('unit_code')
        tag = data.get('tag')
        discussion_id = data.get('discussion_id')
        content = data.get('content')
        
        if not all([username, unit_code, tag, discussion_id, content]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        if tag not in ['general', 'resources', 'private']:
            return jsonify({'success': False, 'error': 'Invalid tag'}), 400
        
        forum_manager = ForumManager(username)
        result = forum_manager.add_reply(unit_code, tag, discussion_id, content)
        
        return jsonify(result)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/forum/delete-discussion', methods=['POST'])
def delete_discussion():
    """
    Delete a discussion (only by creator)
    """
    try:
        data = request.json
        username = data.get('username')
        unit_code = data.get('unit_code')
        tag = data.get('tag')
        discussion_id = data.get('discussion_id')
        
        if not all([username, unit_code, tag, discussion_id]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        forum_manager = ForumManager(username)
        result = forum_manager.delete_discussion(unit_code, tag, discussion_id)
        
        return jsonify(result)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

    
@app.route('/api/forum/toggle-like', methods=['POST'])
def toggle_like():
    """
    Toggle like on a discussion
    """
    try:
        data = request.json
        username = data.get('username')
        unit_code = data.get('unit_code')
        tag = data.get('tag')
        discussion_id = data.get('discussion_id')
        
        if not all([username, unit_code, tag, discussion_id]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        forum_manager = ForumManager(username)
        result = forum_manager.toggle_like(unit_code, tag, discussion_id, username)
        
        return jsonify(result)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    os.makedirs('static', exist_ok=True)
    app.run(debug=True, port=5001)
