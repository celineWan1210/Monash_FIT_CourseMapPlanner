import json
from pathlib import Path
from nltk.sentiment import SentimentIntensityAnalyzer
import nltk
from collections import Counter, defaultdict
import re

class SentimentDifficultyAnalyzer:
    """
    Analyze sentiment and difficulty with context-aware keyword detection
    and specific pain point extraction from general enquiries.
    """

    DIFFICULTY_KEYWORDS = {
        'very_hard': ['nightmare', 'impossible', 'brutal', 'hell', 'overwhelming', 'killer', 'insane'],
        'hard': ['hard', 'difficult', 'tough', 'challenging', 'struggle', 'struggling', 'confusing', 'complex'],
        'moderate': ['okay', 'manageable', 'average', 'decent', 'fair', 'alright'],
        'easy': ['easy', 'simple', 'straightforward', 'relaxed', 'chill', 'breeze'],
        'very_easy': ['wam booster', 'free marks', 'joke', 'too easy', 'no effort', 'piece of cake']
    }

    PAIN_POINT_PATTERNS = {
        'assignments': r'(assignment|assign|task|project)\s*(\d+|two|three|one)?',
        'exams': r'(final|exam|test|quiz|midsem|mid-sem|examination|mid sem)',
        'workload': r'(workload|time consuming|too much work|overload|hours|deadline)',
        'lectures': r'(lecture|lec|recording|slides?)\s*(unclear|confusing|bad|poor)?',
        'concepts': r'(recursion|algorithm|oop|pointer|thread|graph|tree|sorting|data structure)',
        'teaching': r'(lecturer|tutor|teacher|teaching|instructor)\s*(bad|poor|unclear|confusing)?',
        'understanding': r'(don\'t understand|hard to understand|confusing|unclear|lost)',
        'prerequisites': r'(prereq|prerequisite|assumed knowledge|need background|should have done)'
    }

    NEGATIONS = [
        'not', 'no', 'never', 'neither', 'nobody', 'nothing', 'nowhere',
        "n't", "isn't", "aren't", "wasn't", "weren't", "hasn't", "haven't",
        "hadn't", "won't", "wouldn't", "don't", "doesn't", "didn't", "can't",
        "couldn't", "shouldn't", "mightn't", "mustn't"
    ]

    def __init__(self):
        try:
            nltk.download('vader_lexicon', quiet=True)
            self.sid = SentimentIntensityAnalyzer()
        except:
            print("Warning: VADER lexicon download failed")
            self.sid = None

    def get_unit_comments(self, unit_code):
        """
        Load all comments and replies from forum_data/{unit_code}_general.json

        @param unit_code 

        @returns dictioanry of user comments
        """
        path = Path(f"forum_data/{unit_code}_general.json")
        if not path.is_file():
            return []
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        comments = []
        for post in data:
            comments.append({'text': post['content'], 'type': 'post'})
            for reply in post.get('replies', []):
                comments.append({'text': reply['content'], 'type': 'reply'})
        return comments

    def detect_keywords_with_context(self, text):
        """
        @param text of what user have written

        Detect difficulty keywords but check for negations
        not hard -> negated: True
        hard -> negated: False
        @return keyword, level of difficulty and negated (True/False) in a dictionary 
        """
        text_lower = text.lower()
        found_keywords = []
        
        for level, keywords in self.DIFFICULTY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    keyword_index = text_lower.find(keyword)
                    before_text = text_lower[:keyword_index].split()[-3:]
                    is_negated = any(neg in before_text for neg in self.NEGATIONS)
                    found_keywords.append({'word': keyword, 'level': level, 'negated': is_negated})
        return found_keywords

    def extract_pain_points(self, text):
        """
        @param text of what user have written

        Find specific things students complain about

        @returns the pain points
        """
        text_lower = text.lower()
        found_pain_points = []
        for category, pattern in self.PAIN_POINT_PATTERNS.items():
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                match_text = matches[0] if isinstance(matches[0], str) else ' '.join(str(m) for m in matches[0] if m)
                found_pain_points.append({'category': category, 'match': match_text})
        return found_pain_points

    def interpret_with_context(self, sentiment_score, keywords_with_context):
        """
        @param sentiment_score the base score
        @param keyword_with_context keywords mention in text
        Interpretation considering negations

        Used the compound sentiment score but merge with difficulty context

        @returns meaningful sentiment if keyword detected else the base sentiment
        """
        compound = sentiment_score["compound"]
        if compound >= 0.05:
            base_sentiment = "positive"
        elif compound <= -0.05:
            base_sentiment = "negative"
        else:
            base_sentiment = "neutral"

        difficulty_signals = []
        for kw in keywords_with_context:
            level = kw['level']
            negated = kw['negated']
            if negated:
                if level in ['very_hard', 'hard']:
                    difficulty_signals.append('easy')
                elif level in ['easy', 'very_easy']:
                    difficulty_signals.append('hard')
            else:
                if level in ['very_hard', 'hard']:
                    difficulty_signals.append('hard')
                elif level in ['easy', 'very_easy']:
                    difficulty_signals.append('easy')

        if 'hard' in difficulty_signals:
            if base_sentiment == "negative":
                return "perceived as hard"
            elif base_sentiment == "positive":
                return "challenging but valuable"
            else:
                return "likely hard but neutral tone"
        elif 'easy' in difficulty_signals:
            if base_sentiment == "positive":
                return "perceived as easy"
            elif base_sentiment == "negative":
                return "easy but disappointing"
            else:
                return "likely easy"
        else:
            return base_sentiment

    def extract_reasoning(self, text, opinion_type):
        """
        @param text entered by user
        @param opinion_type easy/hard

        Extract why someone thinks it's easy/hard
        Uses pattern matching
        @return the reason why people thinks its hard/easy
        """
        text_lower = text.lower()
        if opinion_type == 'easy':
            patterns = [
                r'(easy|simple|straightforward).{0,80}(because|since|as|due to)\s*(.{10,80})',
                r'(prior knowledge|experience|already know).{0,50}(help|made it|so it was)',
                r'(manageable|not too hard).{0,80}',
            ]
        elif opinion_type == 'hard':
            patterns = [
                r'(hard|difficult|tough|struggle).{0,80}(because|since|due to|as)\s*(.{10,80})',
                r'(workload|assignment|exam|test).{0,30}(too much|overwhelming|brutal|killer|insane)',
                r'(confusing|unclear).{0,50}',
            ]
        else:
            return None

        for pattern in patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                return match.group(0).strip('.,;!? ')[:120]
        return None

    def analyze_unit(self, unit_code):
        """
        @param unit_code that user wants to analyse

        Full analysis with reasoning extraction

        @return JSON structure output
        """
        comments = self.get_unit_comments(unit_code)
        if not comments:
            return {"unit": unit_code, "status": "no_data", "message": "No comments found"}

        results = []
        all_pain_points = defaultdict(list)
        difficulty_distribution = Counter()
        easy_reasons, hard_reasons = [], []

        for comment in comments:
            text = comment['text']
            sentiment = self.sid.polarity_scores(text) if self.sid else {"compound": 0, "pos": 0, "neg": 0, "neu": 1}
            keywords = self.detect_keywords_with_context(text)
            meaning = self.interpret_with_context(sentiment, keywords)
            pain_points = self.extract_pain_points(text)

            if 'easy' in meaning:
                reason = self.extract_reasoning(text, 'easy')
                if reason:
                    easy_reasons.append({'text': text, 'reason': reason})
            elif 'hard' in meaning:
                reason = self.extract_reasoning(text, 'hard')
                if reason:
                    hard_reasons.append({'text': text, 'reason': reason})

            results.append({
                "text": text,
                "compound": sentiment["compound"],
                "keywords": [k['word'] for k in keywords],
                "negations": [k['word'] for k in keywords if k['negated']],
                "meaning": meaning,
                "pain_points": [p['category'] for p in pain_points]
            })

            for pain in pain_points:
                all_pain_points[pain['category']].append(text[:150])
            difficulty_distribution[meaning] += 1

        avg_sentiment = sum(r["compound"] for r in results) / len(results)
        dominant_opinion = difficulty_distribution.most_common(1)[0][0]

        top_pain_points = [
            {"category": category, "count": len(mentions), "example": mentions[0]}
            for category, mentions in sorted(all_pain_points.items(), key=lambda x: len(x[1]), reverse=True)[:3]
        ]

        hard_count = sum(1 for r in results if 'hard' in r['meaning'])
        easy_count = sum(1 for r in results if 'easy' in r['meaning'])
        difficulty_score = int(((hard_count - easy_count) / len(results) + 1) * 50)
        negative_count = sum(1 for r in results if r['compound'] < -0.2)
        struggling_percent = int((negative_count / len(results)) * 100)

        return {
            "unit": unit_code,
            "status": "success",
            "average_sentiment": round(avg_sentiment, 3),
            "dominant_opinion": dominant_opinion,
            "difficulty_score": difficulty_score,
            "struggling_percent": f"{struggling_percent}%",
            "total_comments": len(results),
            "pain_points": top_pain_points,
            "difficulty_distribution": dict(difficulty_distribution),
            "easy_reasons": easy_reasons,
            "hard_reasons": hard_reasons,
            "details": results
        }