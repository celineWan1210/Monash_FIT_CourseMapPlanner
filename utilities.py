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

# utilities.py
def initialize_user(data):
    """
    Helper function to initialize user info, core planner, and elective planner
    """
    # Import here to avoid circular import
    from core_planner import PlannerForCore, UserInfo
    from elective_planner import PlannerForElective
    from pass_info import PreviousDetails
    from update_result import UpdateResult
    
    username = data.get('username')
    intake = data.get('intake')
    stream = data.get('stream')
    year = data.get('year')
    sem = data.get('semester')

    # Initialize UserInfo
    user_info = UserInfo()
    user_info.user_basic_info_web(username, stream, year, sem, intake)

    print(f"Received user info: username='{user_info.username}', intake={user_info.intake}, "
          f"stream={user_info.stream}, year={user_info.year}, sem={user_info.sem}")

    # Initialize PreviousDetails (pass_info)
    update_result = UpdateResult()
    pass_info = PreviousDetails(user_info, update_result)
    pass_info.check_previous_record()

    # Initialize Core Planner
    core_planner = PlannerForCore(user_info, pass_info)
    core_planner.read_core_unit()
    core_planner.save_user_core()

    # Set current semester
    if user_info.intake == 2 and user_info.sem == 1:
        core_planner.current_sem = 2
    elif user_info.intake == 2 and user_info.sem == 2:
        core_planner.current_sem = 1
    elif user_info.intake == 1 and user_info.sem == 1:
        core_planner.current_sem = 1
    elif user_info.intake == 1 and user_info.sem == 2:
        core_planner.current_sem = 2

    # Initialize Elective Planner
    elective_planner = PlannerForElective(user_info, core_planner)
    elective_planner.read_elective()
    elective_planner.save_user_elective()

    return user_info, core_planner, elective_planner