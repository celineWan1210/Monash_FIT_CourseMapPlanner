import json
from pathlib import Path
from collections import Counter, defaultdict

class SimpleResourceRecommender:
    """
    Basic recommender that extracts and ranks commonly mentioned
    learning resources (websites, tools, books) from forum posts.
    """
    
    def __init__(self, resources_dir="forum_data"):
        self.resources_dir = Path(resources_dir)

    def load_resources(self, unit_code):
        """
        Load all saved discussion posts for a specific unit.

        @param unit_code (str): The unit code 

        @returns
            list[dict]: A list of posts, where each post is expected to have
            keys like "title" and "content". Returns an empty list if the
            resource file does not exist.
        """
        path = self.resources_dir / f"{unit_code}_resources.json"
        if not path.exists():
            return []
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def extract_links(self, content):
        """        
        Identify all URLs or website links mentioned in a post.

        @param content (str): The text content of a post.

        @returns list[str]: A list of detected URL"""
        words = content.split()
        return [w for w in words if w.startswith("http://") or w.startswith("https://") or "www." in w]

    def detect_common_sources(self, content):
        """      
        Detect mentions of popular learning platforms or resource keywords.

        @param content (str): The text content of a post.

        @returns list[str]: A list of recognized resource keywords found in the text.
        """
        content_lower = content.lower()
        tags = []
        keywords = [
            "kaggle", "visualgo", "geeksforgeeks", "leetcode", "freecodecamp",
            "youtube", "coursera", "udemy", "book", "tutorial"
        ]
        for k in keywords:
            if k in content_lower:
                tags.append(k)
        return tags

    def recommend(self, unit_code, top_n=5):
        """
        Provide a ranked summary of the most mentioned learning resources
        based on community posts for a given unit.

        @param 
            unit_code (str): The unit code (e.g., "FIT1058").
            top_n (int, optional): The number of top resources to display. Defaults to 5.

        @returns
            str: A formatted text summary showing the top resources and
            where they were mentioned.
        """
        posts = self.load_resources(unit_code)
        if not posts:
            return f"No community resources found for {unit_code}."

        # Track mentions
        counter = Counter()
        resources = defaultdict(list)

        for post in posts:
            links = self.extract_links(post["content"])
            tags = self.detect_common_sources(post["content"])
            all_refs = links + tags

            for ref in all_refs:
                counter[ref] += 1
                resources[ref].append(post["title"])

        if not counter:
            return f"No links or known resources detected for {unit_code}."

        # Get top ones
        top = counter.most_common(top_n)
        result = f"Top Learning Resources for {unit_code}:\n\n"
        for i, (res, count) in enumerate(top, 1):
            result += f"{i}. {res} — mentioned {count} times\n"
            examples = ", ".join(resources[res][:2])
            if examples:
                result += f"   Seen in: {examples}\n"
        return result
