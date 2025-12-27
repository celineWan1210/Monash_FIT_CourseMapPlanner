from sentiment_analyzer import SentimentDifficultyAnalyzer
from pathlib import Path
import json

class SemesterReadinessAnalyzer:
    """
    Analyzes if a student is ready to take specific units
    based on past performance, prerequisites, and community data
    """
    
    def __init__(self, username):
        self.username = username
        self.sentiment_analyzer = SentimentDifficultyAnalyzer()
    
    def get_past_grades(self):
        """
        Load all past grades from ALL Y{X}S{Y}_units.json files
        Returns: {unit_code: grade_status}
        """
        user_folder = Path(f"user_info/{self.username}")
        all_grades = {}
        
        if not user_folder.exists():
            return {}
        
        # Find ALL semester files dynamically
        semester_files = list(user_folder.glob("Y*S*_units.json"))
        
        for file in semester_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    semester_data = json.load(f)
                    # Update grades dictionary
                    all_grades.update(semester_data)
            except Exception as e:
                print(f"Warning: Could not read {file.name}: {e}")
                continue
        
        return all_grades
    
    def get_completed_units(self):
        """
        Get only PASSED units (filter out 'planned', 'N', 'Fail')
        Returns: list of unit codes
        """
        all_grades = self.get_past_grades()
        
        # Statuses that count as "completed"
        passing_statuses = ['HD', 'D', 'C', 'P', 
                           'High Distinction', 'Distinction', 'Credit', 'Pass']
        
        completed = [
            code for code, status in all_grades.items()
            if status in passing_statuses
        ]
        
        return completed
    
    def analyze_prerequisite_strength(self, unit_code, core_units_data):
        """
        Check how strong user background is based  on their passed performance
        @returns (fulfilled, strength_score, details)
        """
        prereq_str = core_units_data.get(unit_code, {}).get('prereq', 'NONE')
        
        if prereq_str == 'NONE' or not prereq_str:
            return (True, 100, "No prerequisites required")
        
        past_grades = self.get_past_grades()
        completed_units = self.get_completed_units()
        
        # Grade value mapping
        grade_map = {
            'HD': 100, 'High Distinction': 100,
            'D': 80, 'Distinction': 80,
            'C': 70, 'Credit': 70,
            'P': 50, 'Pass': 50,
            'N': 0, 'Fail': 0,
            'planned': 0
        }
        
        # Parse prerequisite codes
        prereq_codes = []
        prereq_type = 'all'  # or 'one'
        
        if prereq_str.startswith('a;'):
            prereq_type = 'all'
            prereq_codes = [u.strip().upper() for u in prereq_str[2:].split(';') if u.strip()]
        elif prereq_str.startswith('o;'):
            prereq_type = 'one'
            prereq_codes = [u.strip().upper() for u in prereq_str[2:].split(';') if u.strip()]
        elif prereq_str == '12':
            # Need any 12 credit points (2 units)
            if len(completed_units) >= 2:
                return (True, 100, f"Completed {len(completed_units)} units (12CP met)")
            else:
                return (False, 0, f"Need 2 units, only completed {len(completed_units)}")
        elif prereq_str == '72':
            # Need 72 credit points (12 units)
            if len(completed_units) >= 12:
                return (True, 100, f"Completed {len(completed_units)} units (72CP met)")
            else:
                return (False, 0, f"Need 12 units, only completed {len(completed_units)}")
        else:
            prereq_type = 'single'
            prereq_codes = [prereq_str.strip().upper()]
        
        # Normalize unit codes (ensure FIT prefix)
        def normalize_code(code):
            code = code.upper().strip()
            if not code.startswith('FIT'):
                code = 'FIT' + code
            return code
        
        prereq_codes = [normalize_code(c) for c in prereq_codes]
        
        # Check fulfillment
        if prereq_type == 'all':
            fulfilled = all(code in completed_units for code in prereq_codes)
        elif prereq_type == 'one':
            fulfilled = any(code in completed_units for code in prereq_codes)
        else:  # single
            fulfilled = prereq_codes[0] in completed_units
        
        if not fulfilled:
            missing = [c for c in prereq_codes if c not in completed_units]
            return (False, 0, f"Missing: {', '.join(missing)}")
        
        # Calculate strength based on grades
        prereq_grades = []
        for code in prereq_codes:
            if code in past_grades:
                grade = past_grades[code]
                grade_value = grade_map.get(grade, 50)
                prereq_grades.append((code, grade, grade_value))
        
        if not prereq_grades:
            return (True, 100, "Prerequisites met")
        
        avg_strength = sum(g[2] for g in prereq_grades) / len(prereq_grades)
        
        # Build details string
        details = "\n".join([f"  {code}: {grade}" for code, grade, _ in prereq_grades])
        
        return (fulfilled, int(avg_strength), details)
    
    def analyze_unit_readiness(self, username, unit_code, current_year, current_sem, 
                                stream, intake, planned_units=[]):
        """
        Main analysis function
        @returns comprehensive readiness report
        """
        # Load core units
        core_path = f"user_info/{username}/core_units.json"
        elective_path = f"user_info/{username}/elective_units.json"
        
        all_units = {}
        
        if Path(core_path).exists():
            with open(core_path, 'r', encoding='utf-8') as f:
                all_units.update(json.load(f))
        
        if Path(elective_path).exists():
            with open(elective_path, 'r', encoding='utf-8') as f:
                all_units.update(json.load(f))
        
        if not all_units:
            return {"error": "No unit data found for user"}
        
        unit_data = all_units.get(unit_code)
        if not unit_data:
            return {"error": f"{unit_code} not found in your units"}
        
        # 1. Check prerequisites
        prereq_fulfilled, prereq_strength, prereq_details = \
            self.analyze_prerequisite_strength(unit_code, all_units)
        
        # 2. Get community sentiment
        sentiment = self.sentiment_analyzer.analyze_unit(unit_code)
        
        # 3. Analyze current workload
        current_workload = self._calculate_current_workload(
            username, planned_units, unit_code, all_units
        )
        
        # 4. Calculate readiness score
        readiness_score = self._calculate_readiness_score(
            prereq_fulfilled, prereq_strength, sentiment, current_workload
        )
        
        # 5. Generate recommendations
        recommendations = self._generate_recommendations(
            readiness_score, prereq_strength, sentiment, current_workload, unit_code
        )
        
        return {
            'unit_code': unit_code,
            'unit_name': unit_data['unit_name'],
            'readiness_score': readiness_score,
            'prerequisites': {
                'fulfilled': prereq_fulfilled,
                'strength': prereq_strength,
                'details': prereq_details
            },
            'community_feedback': {
                'difficulty_score': sentiment.get('difficulty_score', 50) if sentiment['status'] == 'success' else 50,
                'struggling_percent': sentiment.get('struggling_percent', '0%') if sentiment['status'] == 'success' else '0%',
                'pain_points': sentiment.get('pain_points', [])[:3] if sentiment['status'] == 'success' else []
            },
            'workload': current_workload,
            'recommendations': recommendations
        }
    
    def _calculate_current_workload(self, username, planned_units, new_unit, all_units):
        """
        Calculate workload for the semester.
        
        Two scenarios:
        1. new_unit IN planned_units: Analyzing a semester (show total workload)
        2. new_unit NOT in planned_units: Adding a unit (show before/after)
        """
        def count_workload(unit_codes):
            """Helper to count assignments/tests for a list of units"""
            assignments = 0
            tests = 0
            for unit_code in unit_codes:
                unit_data = all_units.get(unit_code, {})
                assign = unit_data.get('assign', 'NONE')
                test = unit_data.get('test', 'NONE')
                
                if assign and assign != 'NONE':
                    assignments += len(assign.split(';'))
                if test and test != 'NONE':
                    tests += len(test.split(';'))
            
            return assignments, tests
        
        # Check if we're analyzing an existing semester or adding a new unit
        is_adding_new = new_unit not in planned_units
        
        if is_adding_new:
            # Scenario 2: Adding a new unit
            base_assignments, base_tests = count_workload(planned_units)
            total_assignments, total_tests = count_workload(planned_units + [new_unit])
            total_units = len(planned_units) + 1
        else:
            # Scenario 1: Analyzing existing semester
            total_assignments, total_tests = count_workload(planned_units)
            
            # Calculate "base" as semester without this unit (for context)
            other_units = [u for u in planned_units if u != new_unit]
            base_assignments, base_tests = count_workload(other_units)
            total_units = len(planned_units)
        
        # Status calculation
        if total_assignments > 16 or total_tests > 8:
            status = 'overwhelming'
        elif total_assignments > 12 or total_tests > 6:
            status = 'heavy'
        elif total_assignments > 8 or total_tests > 4:
            status = 'moderate'
        else:
            status = 'light'
        
        return {
            'total_units': total_units,
            'total_assignments': total_assignments,
            'total_tests': total_tests,
            'base_assignments': base_assignments,
            'base_tests': base_tests,
            'new_unit_adds': {
                'assignments': total_assignments - base_assignments,
                'tests': total_tests - base_tests
            },
            'is_adding_new': is_adding_new,
            'status': status
        }
    
    def _calculate_readiness_score(self, prereq_fulfilled, prereq_strength, sentiment, workload):
        """
        Calculate 0-100 readiness score 

        @returns
        - 0-40 = Not ready
        - 41-65 = Somewhat ready
        - 66-85 = Ready
        - 86-100 = Very ready
        """
        #If prerequisites not fulfilled at all, instant 0
        if not prereq_fulfilled:
            return 0
        
        # ===== COMPONENT 1: PREREQUISITE SCORE (50% weight) =====
        # This is the MOST important factor
        prereq_score = prereq_strength  # Already 0-100
        
        # ===== COMPONENT 2: DIFFICULTY-ADJUSTED SCORE (25% weight) =====
        # Instead of inverting, we adjust based on prerequisite strength
        # Logic: Strong prereqs + hard unit = still ready
        #        Weak prereqs + hard unit = not ready
        
        diff_score = sentiment.get('difficulty_score', 50) if sentiment['status'] == 'success' else 50
        
        if prereq_strength >= 85:  # Strong foundation (HD/D)
            # You can handle difficult units
            if diff_score >= 70:  # Hard unit
                difficulty_adjusted = 85  # Still well-prepared
            elif diff_score >= 50:  # Medium unit
                difficulty_adjusted = 90
            else:  # Easy unit
                difficulty_adjusted = 95
        
        elif prereq_strength >= 70:  # Moderate foundation (C)
            # Be cautious with hard units
            if diff_score >= 70:  # Hard unit
                difficulty_adjusted = 60  # Risky
            elif diff_score >= 50:  # Medium unit
                difficulty_adjusted = 75
            else:  # Easy unit
                difficulty_adjusted = 85
        
        elif prereq_strength >= 50:  # Weak foundation (P)
            # Hard units are very risky
            if diff_score >= 70:  # Hard unit
                difficulty_adjusted = 30  # High risk
            elif diff_score >= 50:  # Medium unit
                difficulty_adjusted = 50  # Moderate risk
            else:  # Easy unit
                difficulty_adjusted = 65
        
        else:  # Very weak/no prereq data
            # Even easy units might be challenging
            if diff_score >= 70:
                difficulty_adjusted = 20
            elif diff_score >= 50:
                difficulty_adjusted = 40
            else:
                difficulty_adjusted = 55
        
        # ===== COMPONENT 3: WORKLOAD SCORE (25% weight) =====
        # More granular than binary heavy/manageable
        
        total_assignments = workload['total_assignments']
        total_tests = workload['total_tests']
        total_units = workload['total_units']
        
        # Calculate workload pressure
        if total_assignments <= 8 and total_tests <= 4:
            workload_score = 90  # Light semester
        elif total_assignments <= 12 and total_tests <= 6:
            workload_score = 75  # Moderate semester
        elif total_assignments <= 16 and total_tests <= 8:
            workload_score = 55  # Heavy semester
        else:
            workload_score = 35  # Overwhelming semester
        
        # Adjust for unit count (4 units is standard)
        if total_units > 4:
            workload_score = max(30, workload_score - (total_units - 4) * 10)
        
        # ===== FINAL CALCULATION =====
        # Weighted average with emphasis on prerequisites
        total_score = (
            prereq_score * 0.50 +           # 50% weight
            difficulty_adjusted * 0.25 +    # 25% weight
            workload_score * 0.25           # 25% weight
        )
        
        return int(total_score)

    def _generate_recommendations(self, score, prereq_strength, sentiment, workload, unit_code):
        """
        Generate more specific recommendations based on what's actually wrong
        """
        recommendations = []
        
        # ===== RISK LEVEL WITH CONTEXT =====
        if score >= 80:
            risk = "READY - Strong foundation and manageable workload"
        elif score >= 65:
            risk = "READY WITH PREP - Good foundation, some preparation recommended"
        elif score >= 50:
            risk = "MODERATE RISK - Proceed carefully, extra study needed"
        elif score >= 35:
            risk = "HIGH RISK - Consider deferring or expect significant challenge"
        else:
            risk = "NOT RECOMMENDED - Prerequisites or workload concerns"
        
        recommendations.append(risk)
        
        # ===== PREREQUISITE-SPECIFIC ADVICE =====
        if prereq_strength < 50:
            recommendations.append(
                "CRITICAL: Your prerequisite grades are too weak. "
                "Strongly consider retaking prerequisite units or defer this unit."
            )
        elif prereq_strength < 70:
            recommendations.append(
                "Prerequisite foundation is shaky. "
                "Dedicate 2-3 weeks before semester starts to review key concepts."
            )
        elif prereq_strength < 85:
            recommendations.append(
                "Prerequisites met but not mastered. "
                "Do a quick refresher in Week 1 to strengthen fundamentals."
            )
        
        # ===== DIFFICULTY-BASED ADVICE =====
        if sentiment['status'] == 'success':
            diff_score = sentiment.get('difficulty_score', 50)
            pain_points = sentiment.get('pain_points', [])
            
            if diff_score > 75:
                recommendations.append(
                    f"{unit_code} is rated VERY DIFFICULT by the community. "
                    f"Expect to spend 12-15 hours/week on this unit."
                )
                if pain_points:
                    top_issue = pain_points[0]['category']
                    recommendations.append(
                        f"Students commonly struggle with {top_issue}. "
                        f"Find resources on this topic BEFORE Week 3."
                    )
            elif diff_score > 60:
                recommendations.append(
                    f"Moderately challenging unit. Budget 10-12 hours/week."
                )
        
        # ===== WORKLOAD-SPECIFIC ADVICE =====
        total_assignments = workload['total_assignments']
        total_tests = workload['total_tests']
        is_adding = workload.get('is_adding_new', False)
        
        if is_adding:
            # Show impact of adding this unit
            new_adds = workload['new_unit_adds']
            if new_adds['assignments'] >= 4:
                recommendations.append(
                    f"Adding {unit_code} will add {new_adds['assignments']} assignments "
                    f"and {new_adds['tests']} tests to your workload."
                )
        
        if total_assignments > 16:
            recommendations.append(
                f"WORKLOAD WARNING: {total_assignments} assignments this semester is EXTREME. "
                f"Drop 1 unit or expect burnout."
            )
        elif total_assignments > 12:
            recommendations.append(
                f"Heavy semester: {total_assignments} assignments. "
                f"Start assignments early and use a planner."
            )
        
        if total_tests > 6:
            recommendations.append(
                f"{total_tests} tests/quizzes is demanding. "
                f"Create a study schedule to avoid cramming."
            )
        
        # ===== STRATEGIC ADVICE =====
        if score < 65 and workload['total_units'] >= 4:
            recommendations.append(
                "STRATEGY: Consider taking only 3 units this semester instead of 4 "
                "to reduce pressure and improve performance."
            )
        
        return recommendations
 