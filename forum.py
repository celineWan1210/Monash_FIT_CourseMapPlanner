import json
import os
from pathlib import Path
from datetime import datetime


class ForumManager:
    """
    Manages the community forum functionality for unit discussions.
    Handles loading units, managing discussion threads, and user permissions.
    """
    
    def __init__(self, username):
        """
        Initialize ForumManager for a specific user
        
        Args:
            username (str): The current user's username
            folder path for forum data (public) and private discussion (individual)
        """
        self.username = username
        self.user_folder = Path(f"user_info/{username}")
        self.forum_folder = Path("forum_data")
        self.private_folder = self.user_folder / "private_discussions"
        
        # Ensure directories exist
        self.forum_folder.mkdir(parents=True, exist_ok=True)
        self.private_folder.mkdir(parents=True, exist_ok=True)
    
    def load_all_units(self):
        """
        Load all available units (both core and elective) for the user
        
        @return Dictionary of all units with their information
        """
        all_units = {}
        
        # Load core units
        core_path = self.user_folder / "core_units.json"
        if core_path.exists():
            with open(core_path, 'r', encoding='utf-8') as f:
                core_data = json.load(f)
                for code, info in core_data.items():
                    all_units[code] = {
                        'code': code,
                        'name': info.get('unit_name', code),
                        'description': info.get('description', 'No description available'),
                        'type': 'core'
                    }
        
        # Load elective units
        elective_path = self.user_folder / "elective_units.json"
        if elective_path.exists():
            with open(elective_path, 'r', encoding='utf-8') as f:
                elective_data = json.load(f)
                for code, info in elective_data.items():
                    if code not in all_units:  # Avoid duplicates
                        all_units[code] = {
                            'code': code,
                            'name': info.get('unit_name', code),
                            'description': info.get('description', 'No description available'),
                            'type': 'elective'
                        }
        
        return all_units
    
    def get_unit_discussions(self, unit_code, tag):
        """
        Get all discussions for a specific unit and tag
        
        @param unit_code (str): The unit code 
        @param tag (str): Discussion tag ('general', 'resources', or 'private')
        
        Returns:
            list: List of discussion threads
        """
        if tag == 'private':
            # Load from user's private folder
            file_path = self.private_folder / f"{unit_code}_private.json"
        else:
            # Load from public forum folder
            file_path = self.forum_folder / f"{unit_code}_{tag}.json"
        
        if not file_path.exists():
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                discussions = json.load(f)
                return discussions
        except json.JSONDecodeError:
            return []
    
    def add_discussion(self, unit_code, tag, title, content):
        """
        Add a new discussion thread
        
        @param unit code
        @param discussion tag
        @param discussion title
        @param discussion content
        
        @return dict: The created discussion with success status
        """
        if tag == 'private':
            file_path = self.private_folder / f"{unit_code}_private.json"
        else:
            file_path = self.forum_folder / f"{unit_code}_{tag}.json"
        
        # Load existing discussions
        discussions = []
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    discussions = json.load(f)
                except json.JSONDecodeError:
                    discussions = []
        
        # Create new discussion
        new_discussion = {
            'id': len(discussions) + 1,
            'username': self.username,
            'title': title,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'likes': [],
            'replies': []
        }
        
        discussions.append(new_discussion)
        
        # Save discussions
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(discussions, f, indent=4)
        
        return {
            'success': True,
            'discussion': new_discussion
        }
    
    def add_reply(self, unit_code, tag, discussion_id, content):
        """
        Add a reply to an existing discussion
        
        @param unit_code (str): The unit code
        @param tag (str): Discussion tag
        @param discussion_id (int): ID of the discussion to reply to
        @param content (str): Reply content
        
        @return dict: Result with success status
        """
        if tag == 'private':
            file_path = self.private_folder / f"{unit_code}_private.json"
        else:
            file_path = self.forum_folder / f"{unit_code}_{tag}.json"
        
        if not file_path.exists():
            return {'success': False, 'error': 'Discussion not found'}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            discussions = json.load(f)
        
        # Find the discussion
        discussion_found = False
        for discussion in discussions:
            if discussion['id'] == discussion_id:
                new_reply = {
                    'username': self.username,
                    'content': content,
                    'timestamp': datetime.now().isoformat()
                }
                discussion['replies'].append(new_reply)
                discussion_found = True
                break
        
        if not discussion_found:
            return {'success': False, 'error': 'Discussion ID not found'}
        
        # Save updated discussions
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(discussions, f, indent=4)
        
        return {'success': True, 'message': 'Reply added successfully'}
    
    def get_discussion_stats(self, unit_code):
        """
        Get statistics about discussions for a unit
        
        @param unit_code (str): The unit code
        
        @return dict: Statistics including count per tag
        """
        stats = {
            'general': 0,
            'resources': 0,
            'private': 0
        }
        
        for tag in ['general', 'resources', 'private']:
            discussions = self.get_unit_discussions(unit_code, tag)
            stats[tag] = len(discussions)
        
        return stats
    
    def can_access_discussion(self, unit_code, tag, request_username):
        """
        Check if a user can access a specific discussion
        
        @param unit_code (str): The unit code
        @param tag (str): Discussion tag
        @param request_username (str): Username trying to access
        
        @return bool: True if user can access, False otherwise
        """
        # Private discussions can only be accessed by the owner
        if tag == 'private':
            return request_username == self.username
        
        # Public discussions (general, resources) are accessible to all
        return True
    
    def delete_discussion(self, unit_code, tag, discussion_id):
        """
        Delete a discussion (only by the creator)
        
        @param unit_code (str): The unit code
        @param tag (str): Discussion tag
        @param iscussion_id (int): ID of discussion to delete
        
        @return dict: Result with success status
        """
        if tag == 'private':
            file_path = self.private_folder / f"{unit_code}_private.json"
        else:
            file_path = self.forum_folder / f"{unit_code}_{tag}.json"
        
        if not file_path.exists():
            return {'success': False, 'error': 'Discussion not found'}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            discussions = json.load(f)
        
        # Find and remove the discussion
        discussion_found = False
        for i, discussion in enumerate(discussions):
            if discussion['id'] == discussion_id:
                # Check if user is the creator
                if discussion['username'] != self.username:
                    return {'success': False, 'error': 'You can only delete your own discussions'}
                discussions.pop(i)
                discussion_found = True
                break
        
        if not discussion_found:
            return {'success': False, 'error': 'Discussion ID not found'}
        
        # Save updated discussions
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(discussions, f, indent=4)
        
        return {'success': True, 'message': 'Discussion deleted successfully'}
    
    def toggle_like(self, unit_code, tag, discussion_id, username):
        """
        Toggle like on a discussion (add if not liked, remove if already liked)

        @param unit_code (str): The unit code
        @param tag (str): Discussion tag
        @param discussion_id (int): ID of discussion to delete
        @param username(str): navigate correct user
        
        @return dict: {'success': bool, 'liked': bool, 'like_count': int}
        """
        if tag == 'private':
            file_path = self.private_folder / f"{unit_code}_private.json"
        else:
            file_path = self.forum_folder / f"{unit_code}_{tag}.json"
        
        if not file_path.exists():
            return {'success': False, 'error': 'Discussion not found'}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            discussions = json.load(f)
        
        # Find the discussion
        for discussion in discussions:
            if discussion['id'] == discussion_id:
                # Initialize likes list if it doesn't exist (for old discussions)
                if 'likes' not in discussion:
                    discussion['likes'] = []
                
                # Toggle like
                if username in discussion['likes']:
                    discussion['likes'].remove(username)
                    liked = False
                else:
                    discussion['likes'].append(username)
                    liked = True
                
                # Save
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(discussions, f, indent=4)
                
                return {
                    'success': True,
                    'liked': liked,
                    'like_count': len(discussion['likes'])
                }
        
        return {'success': False, 'error': 'Discussion not found'}