from utilities import initialize_user  
from sentiment_analyzer import SentimentDifficultyAnalyzer
from resources_rec import SimpleResourceRecommender
from performance import SemesterReadinessAnalyzer 
import google.generativeai as genai
import os, json

class UnitAdvisorAI:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
        self.os = os
        self.json = json

    def load_unit_data(self, username, unit_code):
        """Load data for a specific unit"""
        core_path = f"user_info/{username}/core_units.json"
        elective_path = f"user_info/{username}/elective_units.json"

        for path in [core_path, elective_path]:
            if self.os.path.exists(path):
                with open(path, 'r') as f:
                    data = self.json.load(f)
                    if unit_code in data:
                        return data[unit_code]
        return None
    
    def load_core_units(self, username):
        """Load core units"""
        core_units = {}
        elective_path = f"user_info/{username}/core_units.json"
        if self.os.path.exists(elective_path):
            with open(elective_path, 'r') as f:
                core_units.update(self.json.load(f))
        return core_units

    def load_elective_units(self, username):
        """Load elective units, excluding any that are already in core units"""
        elective_units = {}
        elective_path = f"user_info/{username}/elective_units.json"
        core_units = self.load_core_units(username)

        if self.os.path.exists(elective_path):
            with open(elective_path, 'r') as f:
                all_electives = self.json.load(f)
                for code, data in all_electives.items():
                    if code not in core_units:
                        elective_units[code] = data
        return elective_units

    def load_all_units(self, username):
        """Load all available units"""
        all_units = {}
        core_path = f"user_info/{username}/core_units.json"
        elective_path = f"user_info/{username}/elective_units.json"

        if self.os.path.exists(core_path):
            with open(core_path, 'r') as f:
                all_units.update(self.json.load(f))
        if self.os.path.exists(elective_path):
            with open(elective_path, 'r') as f:
                all_units.update(self.json.load(f))
        return all_units

    def load_planned_units(self, username, year, semester):
        """Load planned units for a specific semester"""
        planned_path = f"user_info/{username}/Y{year}S{semester}_units.json"
        if self.os.path.exists(planned_path):
            with open(planned_path, 'r') as f:
                return self.json.load(f)
        return {}
    
    def recommend_units(self, username, intake, stream, year, semester, interest):
        """
        @param username, intake, stream, year, semester - basic information of user 
        @param user interest
        Recommend elective by providng Gemini a list of correct list of available elective and interest of user

        The final list only contain elective that is 
        - not a core and havent been chosen as a elective
        - available that sem 
        - pass the prerequiste

        Then prompt the AI to explain why it matches the interest
        @returns final response and fhe final recommendation with the reason
        """
        data = {
            'username': username,
            'intake': intake,
            'stream': stream,
            'year': year,
            'semester': semester
        }
        
        #initialize user to load all information 
        user_info, core_planner, elective_planner = initialize_user(data)
        all_units = elective_planner.all_electives_dict
        if not all_units:
            return "I couldn't find any available elective units for your profile."

        #check if user mention about any level
        level_requested = None
        for lvl in ['1', '2', '3']:
            if f"level {lvl}" in interest.lower() or f"year {lvl}" in interest.lower():
                level_requested = lvl
                break
        
        #filter the units
        #only return if unit is not a core / havent chose / pass prerequisite / is available that sem 
        available_units = {}
        for code, data in all_units.items():
            if code in core_planner.core_units_all or code in elective_planner.final_elective:
                continue
            if level_requested and code[3] != level_requested:
                continue
            if not elective_planner.check_elective_preq(code):
                continue
            if not elective_planner.check_elective_available_sem(code):
                continue
            available_units[code] = data

        if not available_units:
            return "None of the electives are currently available based on your prerequisites and semester offering."

        #format as as string that list unit code, name and description
        units_list = "\n".join([
            f"- {code}: {data['unit_name']} - {data['description']}"
            for code, data in available_units.items()
        ])

        prompt = f"""You are a helpful course advisor for Monash students.

        The student is interested in: "{interest}"

        Below are the electives that are AVAILABLE and meet prerequisite/semester conditions:
        {units_list}

        Recommend 3–5 electives that best match the student's interest.
        For each elective, include:
        1. Unit code and name (exactly as listed)
        2. A short explanation (1–2 sentences) of why it suits their interest.
        IMPORTANT: Only recommend from the list above. Do not invent new units."""

        response = self.model.generate_content(prompt)
        return f"The following electives are suitable and available:\n\n{response.text.strip()}"
    
    def calculate_workload(self, username, planned_units):
        """
        @param username to get the corrct database
        @param planned_unit get the units that user have planned
        Calculate workload based on planned units

        Initialize the count of assignment test and final as 0 and add 1 if its does not show as NONE
        @returns dictionary contain total count
        """
        # Initialize the counter 
        total_assignments = 0
        total_tests = 0
        total_final = 0
        unit_count = len(planned_units)
        workload_details = []

        # loop through plan unit and get the unit detials
        # count the assignment, test and finals
        for unit_code in planned_units.keys():
            unit_data = self.load_unit_data(username, unit_code)
            if unit_data:
                assign = unit_data.get('assign', 'NONE')
                test = unit_data.get('test', 'NONE')
                final = unit_data.get('final', '0')

                if assign != 'NONE':
                    total_assignments += len(assign.split(';'))
                if test != 'NONE':
                    total_tests += len(test.split(';'))
                if final != 'NONE':
                    total_final += 1

                workload_details.append({
                    'code': unit_code,
                    'name': unit_data['unit_name'],
                    'assign': assign,
                    'test': test,
                    'final': final
                })

        # return the information in a dictionary
        return {
            'unit_count': unit_count,
            'total_assignments': total_assignments,
            'total_tests': total_tests,
            'total_finals': total_final,
            'details': workload_details
        }

    def check_workload_heavy(self, workload):
        """Check if workload is too heavy"""
        warnings = []
        if workload['total_assignments'] >= 12:
            warnings.append(f"{workload['total_assignments']} total assignments might be overwhelming")
        if workload['total_tests'] >= 6:
            warnings.append(f"{workload['total_tests']} tests/quizzes is very demanding")
        if workload['total_finals'] >= 3:
            warnings.append(f"{workload['total_finals']} final exams during exam period is tough")
        return warnings

    def format_workload_breakdown(self, workload):
        """Nicely format workload with each assessment on its own line"""
        lines = []
        for detail in workload['details']:
            lines.append(f"{detail['code']} - {detail['name']}")
            
            assign = detail['assign']
            if assign != 'NONE':
                for i, a in enumerate(assign.split(';'), 1):
                    lines.append(f"   • Assignment {i}: {a}%")
            
            test = detail['test']
            if test != 'NONE':
                for i, t in enumerate(test.split(';'), 1):
                    lines.append(f"   • Test {i}: {t}%")
            
            final = detail['final']
            if final != 'NONE' and final != '0':
                lines.append(f"   • Final Exam: {final}%")
            
            lines.append("")
        return "\n".join(lines)
    
    def show_workload(self, username, year, semester, planned_units):
        """
        return message in a string to be output directly 
        """
        workload = self.calculate_workload(username, planned_units)
        warnings = self.check_workload_heavy(workload)
        breakdown = self.format_workload_breakdown(workload)
        response = (
            f"📊 **Workload Summary — Y{year}S{semester}**\n\n"
            f"- Total Units: {workload['unit_count']}\n"
            f"- Assignments: {workload['total_assignments']}\n"
            f"- Tests: {workload['total_tests']}\n"
            f"- Finals: {workload['total_finals']}\n\n"
            f"📋 **Breakdown:**\n{breakdown}\n"
        )
        response += "\n⚠️ " + "\n⚠️ ".join(warnings) if warnings else "\n✅ Looks manageable!"
        return response
    
    def show_all_semesters_with_info(self, username):
        """
        Load all the units and save all the available planner in a list
        Loop throught the list and to get the information using the all units dictionary 

        @param username to get the correct database
        @return unit code and unit name of all plans
        """
        user_folder = f"user_info/{username}"
        if not self.os.path.exists(user_folder):
            return f"User {username} not found."

        all_units = self.load_all_units(username)
        if not all_units:
            return f"No core/elective units found for {username}."

        sem_files = [f for f in self.os.listdir(user_folder) if f.startswith("Y") and f.endswith("_units.json")]
        if not sem_files:
            return "No semester unit files found."

        sem_files.sort()
        output_lines = []
        for sem_file in sem_files:
            sem_path = self.os.path.join(user_folder, sem_file)
            with open(sem_path, 'r') as f:
                semester_units = self.json.load(f)

            semester_name = sem_file.replace("_units.json", "")
            output_lines.append(f"📘 {semester_name} Units:")
            for code, status in semester_units.items():
                unit_data = all_units.get(code)
                if unit_data:
                    output_lines.append(f"   - {code}: {unit_data['unit_name']}")
                else:
                    output_lines.append(f"   - {code}: Unknown Unit")
            output_lines.append("")

        return "\n".join(output_lines)

    def summarize_unit_sentiment(self, unit_code):
        """
        @param unit_code 
        
        Generate detailed AI summary using student quotes from sentiment analysis
        @return generated content of reason 
        """
        try:
            analyzer = SentimentDifficultyAnalyzer()
            analysis = analyzer.analyze_unit(unit_code)
        except Exception as e:
            return f"Sorry, I couldn't analyze feedback for {unit_code}. ({e})"
        
        if analysis['status'] == 'no_data':
            return f"No community feedback available for {unit_code} yet."
        
        easy_examples = "\n".join([
            f"- \"{reason['reason']}\"" 
            for reason in analysis['easy_reasons'][:3]
        ]) if analysis['easy_reasons'] else "None mentioned"
        
        hard_examples = "\n".join([
            f"- \"{reason['reason']}\"" 
            for reason in analysis['hard_reasons'][:3]
        ]) if analysis['hard_reasons'] else "None mentioned"
        
        pain_details = "\n".join([
            f"- {p['category'].title()}: {p['count']} mentions (e.g., \"{p['example']}\")"
            for p in analysis['pain_points'][:3]
        ]) if analysis['pain_points'] else "No specific pain points identified"
        
        prompt = f"""You are a university advisor helping students understand community feedback for {unit_code}.

        DIFFICULTY METRICS:
        - Difficulty Score: {analysis['difficulty_score']}/100
        - Students Struggling: {analysis['struggling_percent']}
        - Overall Sentiment: {analysis['dominant_opinion']}
        - Total Comments Analyzed: {analysis['total_comments']}

        WHY STUDENTS FIND IT EASY:
        {easy_examples}

        WHY STUDENTS FIND IT HARD:
        {hard_examples}

        COMMON PAIN POINTS:
        {pain_details}

        TASK: Write a 4-5 sentence summary that:
        1. You are talking to that student only not everyone
        2. Gives an honest assessment of difficulty based on actual student experiences
        3. Highlights the main challenges students face (use their words)
        4. Mentions any reasons why some find it manageable
        5. Ends with actionable advice or perspective

        Be conversational, specific, and helpful. Use the actual student quotes to support your points."""
                
        response = self.model.generate_content(prompt)
        return response.text.strip()
    
       
    def get_unit_info(self, username, unit_code):
        """Fetch unit's info."""
        all_units = self.load_all_units(username)
        return all_units.get(unit_code)
    
    def summarize_unit_overview(self, username, unit_code):
        """Introduce the unit the unit with practical advice."""
        try:
            unit_data = self.get_unit_info(username, unit_code)
            if not unit_data:
                return f"No details available for {unit_code}."

            recommender = SimpleResourceRecommender()
            top_resources = recommender.recommend(unit_code)
        except Exception as e:
            return f"Sorry, something went wrong while generating advice for {unit_code}. ({e})"

        prompt = f"""You are a helpful university advisor introducing a student to {unit_code}.

        Unit Code: {unit_code}
        Unit Name: {unit_data.get('unit_name', 'N/A')}
        Description: {unit_data.get('description', 'No description available.')}

        Recommended Resources (from student community):
        {top_resources}

        TASK: Write a 4-5 sentence advisory summary that:
        1. Briefly introduces what the unit covers.
        2. Mentions useful learning resources or study materials from the list above.
        3. Offers practical advice on how students can prepare or study effectively.
        4. Keep the tone friendly, supportive, and encouraging — no need to discuss challenges or difficulties."""

        response = self.model.generate_content(prompt)
        return response.text.strip()
    
    def analyze_unit_readiness_single(self, username, unit_code, year, semester, stream, intake):
        """
        Deep-dive analysis for a single unit with AI-enhanced advice.
        """
        # Load planned units to calculate workload context
        planned_units_dict = self.load_planned_units(username, year, semester)
        planned_units = list(planned_units_dict.keys()) if planned_units_dict else []
        
        # Initialize analyzer
        analyzer = SemesterReadinessAnalyzer(username)
        
        # Analyze the unit
        result = analyzer.analyze_unit_readiness(
            username=username,
            unit_code=unit_code,
            current_year=year,
            current_sem=semester,
            stream=stream,
            intake=intake,
            planned_units=planned_units
        )
        
        if 'error' in result:
            return result['error']
        
        #generate the content based on result
        return self._generate_ai_unit_deep_dive(result)
    
    def _generate_ai_unit_deep_dive(self, result):
        """Generate detailed AI analysis for a single unit"""
        
        unit_code = result['unit_code']
        unit_name = result['unit_name']
        score = result['readiness_score']
        prereq = result['prerequisites']
        community = result['community_feedback']
        workload = result['workload']
        recommendations = result['recommendations']
        
        # Build detailed context
        prompt = f"""You are a university advisor conducting a detailed readiness assessment for {unit_code}.

        UNIT: {unit_code} - {unit_name}
        OVERALL READINESS SCORE: {score}/100

        PREREQUISITE ANALYSIS:
        - Fulfilled: {'Yes ✅' if prereq['fulfilled'] else 'No ❌'}
        - Strength: {prereq['strength']}/100
        - Details: {prereq['details'] if prereq['details'] else 'No prerequisite grades on record'}

        COMMUNITY FEEDBACK:
        - Difficulty Rating: {community['difficulty_score']}/100
        - Students Struggling: {community['struggling_percent']}
        - Common Pain Points: {', '.join([p['category'] for p in community['pain_points']]) if community['pain_points'] else 'None reported'}

        WORKLOAD CONTEXT:
        - Total Units This Semester: {workload['total_units']}
        - Total Assignments: {workload['total_assignments']}
        - Total Tests: {workload['total_tests']}
        - Workload Status: {workload['status'].title()}

        AUTOMATED RECOMMENDATIONS:
        {chr(10).join(['• ' + r for r in recommendations])}

        TASK: Write a detailed 8-10 sentence advisory that:
        1. Opens with a clear verdict on readiness (e.g., "You're well-prepared for {unit_code}" or "I have concerns about your readiness for {unit_code}")
        2. Explains WHY based on prerequisite performance and community data
        3. Addresses the specific pain points students commonly face in this unit
        4. Discusses how this unit fits into their overall semester workload
        5. Provides 3-4 CONCRETE action items (e.g., "Review recursion concepts from FIT2004 in Week 1-2" or "Allocate 12-15 hours/week for this unit")
        6. Ends with realistic expectations and encouragement

        Be specific, actionable, and honest. Reference actual course concepts where possible based on the pain points."""

        response = self.model.generate_content(prompt)
        
        # Add structured data footer
        footer = f"\n\n📋 **Key Metrics:**"
        footer += f"\n• Readiness Score: {score}/100"
        footer += f"\n• Prerequisites: {'✅ Met' if prereq['fulfilled'] else '❌ Not Met'} ({prereq['strength']}% strength)"
        footer += f"\n• Community Difficulty: {community['difficulty_score']}/100"
        footer += f"\n• Semester Workload: {workload['total_assignments']} assignments, {workload['total_tests']} tests"
        
        return response.text.strip() + footer
    
       
    def analyze_adding_unit(self, username, new_unit_code, year, semester, stream, intake):
        """
        Analyze the impact of ADDING a new unit to an existing semester plan.
        Shows before/after workload comparison.
        """
        from pathlib import Path
        
        # Load existing semester plan
        sem_file = Path(f"user_info/{username}/Y{year}S{semester}_units.json")
        
        if not sem_file.exists():
            return f"❌ No semester plan found for Y{year}S{semester}. Please create it first."
        
        with open(sem_file, 'r') as f:
            existing_semester = self.json.load(f)
            existing_units = list(existing_semester.keys())
        
        # Check if unit is already in the plan
        if new_unit_code in existing_units:
            return f"⚠️ {new_unit_code} is already in your Y{year}S{semester} plan!"
        
        # Analyze readiness WITH the new unit added
        analyzer = SemesterReadinessAnalyzer(username)
        result = analyzer.analyze_unit_readiness(
            username=username,
            unit_code=new_unit_code,
            current_year=year,
            current_sem=semester,
            stream=stream,
            intake=intake,
            planned_units=existing_units  # Pass WITHOUT the new unit
        )
        
        if 'error' in result:
            return f"❌ {result['error']}"
        
        # Extract data
        workload = result['workload']
        score = result['readiness_score']
        prereqs = result['prerequisites']
        community = result['community_feedback']
        recommendations = result['recommendations']
        
        # Build AI-enhanced response
        return self._generate_ai_adding_unit_response(
            new_unit_code, 
            result, 
            existing_units
        )

    def _generate_ai_adding_unit_response(self, unit_code, result, existing_units):
        """Generate AI analysis for adding a unit to existing semester"""
        
        workload = result['workload']
        score = result['readiness_score']
        prereqs = result['prerequisites']
        community = result['community_feedback']
        recommendations = result['recommendations']
        
        prompt = f"""You are a university advisor helping a student decide whether to ADD {unit_code} to their existing semester.

        CURRENT SEMESTER PLAN: {', '.join(existing_units)} ({len(existing_units)} units)

        PROPOSED ADDITION: {unit_code} - {result['unit_name']}

        READINESS SCORE: {score}/100

        PREREQUISITES:
        - Met: {'Yes ✅' if prereqs['fulfilled'] else 'No ❌'}
        - Strength: {prereqs['strength']}/100
        - Details: {prereqs['details']}

        WORKLOAD IMPACT:
        - Before Adding: {workload['base_assignments']} assignments, {workload['base_tests']} tests
        - After Adding: {workload['total_assignments']} assignments, {workload['total_tests']} tests
        - This Unit Adds: +{workload['new_unit_adds']['assignments']} assignments, +{workload['new_unit_adds']['tests']} tests
        - New Status: {workload['status'].title()}

        COMMUNITY FEEDBACK:
        - Difficulty: {community['difficulty_score']}/100
        - Struggling: {community['struggling_percent']}

        AUTOMATED ADVICE:
        {chr(10).join(['• ' + r for r in recommendations])}

        TASK: Write a 6-7 sentence advisory that:
        1. Opens with clear verdict: "I recommend adding {unit_code}" or "I advise against adding {unit_code}"
        2. Explains WHY based on readiness score and workload impact
        3. Discusses the specific workload increase (be specific about the +X assignments/tests)
        4. Addresses prerequisite readiness concerns if any
        5. Mentions if this creates an overwhelming vs manageable semester
        6. Provides 2-3 specific action items if they decide to add it
        7. Ends with a clear recommendation (add now, add later, or skip)

        Be direct, honest, and practical. Help them make a confident decision."""

        response = self.model.generate_content(prompt)
        
        # Add structured metrics
        footer = f"\n\n📊 **Impact Summary:**"
        footer += f"\n• Readiness: {score}/100 ({'✅ Ready' if score >= 75 else '⚠️ Moderate' if score >= 50 else '❌ Not Ready'})"
        footer += f"\n• Prerequisites: {'✅ Met' if prereqs['fulfilled'] else '❌ Not Met'} ({prereqs['strength']}% strength)"
        footer += f"\n• Workload Before: {workload['base_assignments']} assignments, {workload['base_tests']} tests"
        footer += f"\n• Workload After: {workload['total_assignments']} assignments, {workload['total_tests']} tests"
        footer += f"\n• Impact: +{workload['new_unit_adds']['assignments']} assignments, +{workload['new_unit_adds']['tests']} tests"
        footer += f"\n• New Semester Status: {workload['status'].title()}"
        
        return response.text.strip() + footer
    
    def analyze_semester_readiness(self, username, year, semester, stream, intake):
        """
        Analyze readiness for all units in a planned semester.
        Returns AI-enhanced summary with actionable advice.
        """
        # Load planned units
        planned_units_dict = self.load_planned_units(username, year, semester)
        if not planned_units_dict:
            return f"No units found for Y{year}S{semester}. Have you planned this semester yet?"
        
        planned_units = list(planned_units_dict.keys())
        
        # Initialize analyzer
        analyzer = SemesterReadinessAnalyzer(username)
        
        # Analyze each unit
        results = {}
        for unit_code in planned_units:
            result = analyzer.analyze_unit_readiness(
                username=username,
                unit_code=unit_code,
                current_year=year,
                current_sem=semester,
                stream=stream,
                intake=intake,
                planned_units=planned_units
            )
            results[unit_code] = result

        return self._generate_ai_semester_summary(results, year, semester)
    
    def _generate_ai_semester_summary(self, results, year, semester):
        """Generate conversational AI summary of semester readiness"""
        
        # Prepare structured data for AI
        units_summary = []
        for unit_code, data in results.items():
            score = data.get('readiness_score', 0)
            prereq_info = data.get('prerequisites', {})
            community = data.get('community_feedback', {})
            
            status = "✅ Ready" if score >= 75 else ("⚠️ Moderate Risk" if score >= 50 else "❌ High Risk")
            
            units_summary.append({
                'code': unit_code,
                'name': data.get('unit_name', ''),
                'score': score,
                'status': status,
                'prereq_fulfilled': prereq_info.get('fulfilled', True),
                'prereq_strength': prereq_info.get('strength', 100),
                'prereq_details': prereq_info.get('details', ''),
                'difficulty': community.get('difficulty_score', 50),
                'struggling_percent': community.get('struggling_percent', '0%'),
                'pain_points': community.get('pain_points', []),
                'recommendations': data.get('recommendations', [])
            })
        
        # Build AI prompt
        units_text = "\n\n".join([
            f"**{u['code']} - {u['name']}**\n"
            f"Readiness Score: {u['score']}/100 ({u['status']})\n"
            f"Prerequisites: {'✅ Met' if u['prereq_fulfilled'] else '❌ Not Met'} (Strength: {u['prereq_strength']}%)\n"
            f"Community Difficulty: {u['difficulty']}/100 ({u['struggling_percent']} struggling)\n"
            f"Top Issues: {', '.join([p['category'] for p in u['pain_points'][:2]]) if u['pain_points'] else 'None reported'}\n"
            f"Specific Advice:\n" + "\n".join([f"  • {rec}" for rec in u['recommendations']])
            for u in units_summary
        ])
        
        prompt = f"""You are a university course advisor helping a student plan Y{year}S{semester}.

        SEMESTER ANALYSIS:
        {units_text}

        TASK: Write a comprehensive yet friendly 6-8 sentence advisory that:
        1. Starts with overall semester assessment (e.g., "Looking at your Y{year}S{semester} plan...")
        2. Identifies which units are safe vs risky based on readiness scores
        3. Highlights the MAIN challenge or concern (e.g., prerequisite gaps, high difficulty units, workload)
        4. Gives 2-3 SPECIFIC, actionable recommendations (e.g., "Review FIT2004 algorithms before Week 3" or "Consider deferring FIT3155 to next semester")
        5. Ends with an encouraging but realistic note about managing the semester

        Be conversational, practical, and reference specific unit codes. Don't just repeat the scores — synthesize insights and provide strategic advice."""

        response = self.model.generate_content(prompt)
        
        # Add score table after AI summary
        score_table = "\n\n📊 **Quick Reference:**\n"
        score_table += "─" * 10 + "\n"
        for u in sorted(units_summary, key=lambda x: x['score'], reverse=True):
            score_table += f"{u['code']:10} → {u['score']:3}% ({u['status']})\n"
        score_table += "─" * 10
        
        return response.text.strip() + score_table
    

    def compare_unit_readiness(self, username, unit_codes, year, semester, stream, intake, interest=""):
        """
        Compare readiness for 2+ units to help student decide which to take.
        Now includes user interest in the analysis.
        """
        if len(unit_codes) < 2:
            return "Please provide at least 2 unit codes to compare."
        
        # Load planned units
        planned_units_dict = self.load_planned_units(username, year, semester)
        planned_units = list(planned_units_dict.keys()) if planned_units_dict else []
        
        # Load all units for descriptions
        all_units = self.load_all_units(username)
        
        # Initialize analyzer
        analyzer = SemesterReadinessAnalyzer(username)
        
        # Analyze each unit
        results = {}
        for unit_code in unit_codes:
            unit_upper = unit_code.upper()
            result = analyzer.analyze_unit_readiness(
                username=username,
                unit_code=unit_upper,
                current_year=year,
                current_sem=semester,
                stream=stream,
                intake=intake,
                planned_units=planned_units
            )
            if 'error' not in result:
                # Add unit description and assessment info
                unit_data = all_units.get(unit_upper, {})
                result['description'] = unit_data.get('description', 'N/A')
                result['assignments'] = unit_data.get('assign', 'N/A')
                result['tests'] = unit_data.get('test', 'N/A')
                result['final_exam'] = unit_data.get('final', 'N/A')
                results[unit_upper] = result
        
        if not results:
            return "None of the specified units could be analyzed. Check unit codes."
        
        # Generate AI comparison with interest
        return self._generate_ai_comparison(results, interest)
    
    def _generate_ai_comparison(self, results, interest=""):
        """Generate AI-powered unit comparison with user interest consideration"""
        
        comparison_data = []
        for code, data in results.items():
            comparison_data.append({
                'code': code,
                'name': data['unit_name'],
                'description': data.get('description', 'N/A'),
                'score': data['readiness_score'],
                'prereq_strength': data['prerequisites']['strength'],
                'prereq_details': data['prerequisites']['details'],
                'difficulty': data['community_feedback']['difficulty_score'],
                'struggling': data['community_feedback']['struggling_percent'],
                'workload_status': data['workload']['status'],
                'total_assignments': data['workload']['total_assignments'],
                'assignments': data.get('assignments', 'N/A'),
                'tests': data.get('tests', 'N/A'),
                'final_exam': data.get('final_exam', 'N/A'),
                'recommendations': data['recommendations']
            })
        
        # Build comparison text
        units_text = "\n\n".join([
            f"**{u['code']} - {u['name']}**\n"
            f"Description: {u['description']}\n"
            f"• Readiness Score: {u['score']}/100\n"
            f"• Prerequisite Strength: {u['prereq_strength']}% ({u['prereq_details'] if u['prereq_details'] else 'No prereq grades'})\n"
            f"• Community Difficulty: {u['difficulty']}/100 ({u['struggling']} struggling)\n"
            f"• Workload Impact: {u['workload_status'].title()} ({u['total_assignments']} total assignments)\n"
            f"• Assessment: Assignments({u['assignments']}), Tests({u['tests']}), Final({u['final_exam']}%)\n"
            f"• Top Advice: {u['recommendations'][0] if u['recommendations'] else 'None'}"
            for u in comparison_data
        ])
        
        interest_context = f"\n**Student's Interest/Goals:** {interest}" if interest else ""
        
        prompt = f"""You are a university advisor helping a student choose between these units:{interest_context}

        {units_text}

        TASK: Write a 6-8 sentence comparative analysis that:
        1. **If student provided interest:** Evaluate which unit(s) align BEST with their stated interest/goals, referencing the unit descriptions
        2. Clearly states which unit(s) the student is MOST ready for (reference readiness scores)
        3. Compares the key differences (prerequisites, difficulty, workload, assessment style)
        4. Identifies which is the "safer" choice vs which is more challenging
        5. Recommends a strategic order (e.g., "Take {comparison_data[0]['code']} this semester, defer {comparison_data[1]['code']} to next semester")
        6. Explains the strategic reasoning combining BOTH interest alignment AND readiness (e.g., "While FIT2004 matches your AI interest better, your weak prerequisite grades suggest taking FIT1045 first to build foundations")
        7. Ends with a clear, actionable recommendation

        Be direct, practical, and reference specific metrics. Balance their interests with their actual readiness to help them make a confident, strategic decision."""

        response = self.model.generate_content(prompt)
        
        # Add comparison table
        output = "\n\n📊 **Score Comparison:**\n"
        for u in sorted(comparison_data, key=lambda x: x['score'], reverse=True):
            output += f"- **{u['code']}**: Readiness {u['score']}/100 | Difficulty {u['difficulty']}/100 | Prereq {u['prereq_strength']}% | Workload {u['workload_status'].title()}\n"
        
        return response.text.strip() + output

    def ask_ai_about_unit(self, unit_code, unit_data, question):
        if not unit_data:
            return f"Sorry, I couldn't find any information about {unit_code}. Please check the unit code again."

        def interpret(val):
            if val.lower() == 'o':
                return "Complete one of the listed units"
            elif val.lower() == 'a':
                return "Complete all of the listed units"
            elif val.isdigit():
                return f"Complete {val}/6 = {int(val)/6:.1f} units"
            else:
                return val

        assign_text = interpret(unit_data['prereq'])

        prompt = f"""You are a helpful university course advisor.

        Unit Code: {unit_code}
        Unit Name: {unit_data['unit_name']}
        Description: {unit_data['description']}
        Prerequisites: {assign_text}
        Semester Available: {unit_data['sem_available']}
        Assessment: Assignments({unit_data['assign']}), Tests({unit_data['test']}), Final({unit_data['final']}%)

        Student Question: {question}

        IMPORTANT: 
        - Only use the information provided above
        - Do NOT make assumptions or add information not listed
        - If the answer isn't in the data above, say "I don't have that information"
        - Answer helpfully in 2-4 sentences based ONLY on the facts above"""

        response = self.model.generate_content(prompt)
        return response.text.strip()

    def general_advice(self, username, question, interest=None):
        all_units = self.load_all_units(username)
        if not all_units:
            return "I couldn't find any units in your record. Please upload or sync your unit files first."
        
        interest_context = ""
        if interest:
            interest_context = f"The student is interested in {interest}."
        
        prompt = f"""You are a helpful university course advisor. {interest_context}

        Student Question: {question}

        IMPORTANT:
        - Provide practical, general study advice only
        - Do NOT recommend specific units
        - Do NOT make up course requirements or prerequisites
        - If you don't know something, say so
        - Keep response to 2-3 sentences

        Provide a direct, friendly response focusing on general study strategies or course planning tips."""
        
        response = self.model.generate_content(prompt)
        return response.text.strip()
 