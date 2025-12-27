"""
Object Tracking Utilities
Tracks hands and their interactions with ROIs and pizzas
"""
import numpy as np
from collections import defaultdict, deque
from datetime import datetime
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import (
    TRACKING_HISTORY_FRAMES,
    SCOOPER_NEAR_HAND_THRESHOLD,
    HAND_IN_ROI_THRESHOLD
)


class HandTracker:
    """
    Tracks hand movements and their interactions with ROIs and pizzas
    """
    
    def __init__(self, max_history=TRACKING_HISTORY_FRAMES):
        """
        Initialize hand tracker
        
        Args:
            max_history: Maximum number of frames to keep in history
        """
        self.max_history = max_history
        # Track hand states: {hand_id: deque of states}
        self.hand_states = defaultdict(lambda: deque(maxlen=max_history))
        self.next_hand_id = 0
        self.active_hands = {}  # {hand_id: last_bbox}
        
    def calculate_distance(self, bbox1, bbox2):
        """Calculate center-to-center distance between two bboxes"""
        center1 = [(bbox1[0] + bbox1[2]) / 2, (bbox1[1] + bbox1[3]) / 2]
        center2 = [(bbox2[0] + bbox2[2]) / 2, (bbox2[1] + bbox2[3]) / 2]
        
        return np.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)
    
    def calculate_iou(self, bbox1, bbox2):
        """Calculate IoU between two bboxes"""
        x1_inter = max(bbox1[0], bbox2[0])
        y1_inter = max(bbox1[1], bbox2[1])
        x2_inter = min(bbox1[2], bbox2[2])
        y2_inter = min(bbox1[3], bbox2[3])
        
        if x2_inter < x1_inter or y2_inter < y1_inter:
            return 0.0
        
        intersection = (x2_inter - x1_inter) * (y2_inter - y1_inter)
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def match_hands(self, current_hands):
        """
        Match current hand detections to tracked hands
        
        Args:
            current_hands: List of hand bboxes in current frame
        
        Returns:
            Dict mapping hand_id to bbox
        """
        matched_hands = {}
        unmatched_hands = current_hands.copy()
        
        # Try to match with existing active hands
        for hand_id, prev_bbox in self.active_hands.items():
            best_iou = 0
            best_match = None
            
            for hand_bbox in unmatched_hands:
                iou = self.calculate_iou(prev_bbox, hand_bbox)
                if iou > best_iou and iou > 0.3:
                    best_iou = iou
                    best_match = hand_bbox
            
            if best_match is not None:
                matched_hands[hand_id] = best_match
                unmatched_hands.remove(best_match)
        
        # Assign new IDs to unmatched hands
        for hand_bbox in unmatched_hands:
            hand_id = self.next_hand_id
            self.next_hand_id += 1
            matched_hands[hand_id] = hand_bbox
        
        # Update active hands
        self.active_hands = matched_hands.copy()
        
        return matched_hands
    
    def update_hand_state(self, hand_id, hand_bbox, in_roi, roi_name, 
                         has_scooper, near_pizza, frame_number):
        """
        Update the state of a tracked hand
        
        Args:
            hand_id: Unique hand identifier
            hand_bbox: Hand bounding box
            in_roi: Boolean, whether hand is in ROI
            roi_name: Name of ROI if in_roi is True
            has_scooper: Boolean, whether scooper is near hand
            near_pizza: Boolean, whether hand is near pizza
            frame_number: Current frame number
        """
        state = {
            'frame': frame_number,
            'bbox': hand_bbox,
            'in_roi': in_roi,
            'roi_name': roi_name,
            'has_scooper': has_scooper,
            'near_pizza': near_pizza,
            'timestamp': datetime.now().isoformat()
        }
        
        self.hand_states[hand_id].append(state)
    
    def detect_violation(self, hand_id):
        """
        Detect if a hand has committed a violation
        
        Logic:
        - Hand entered ROI without scooper
        - Hand then moved to pizza
        - This indicates picking up ingredient without scooper
        
        Args:
            hand_id: Hand to check
        
        Returns:
            violation_data dict or None
        """
        if hand_id not in self.hand_states:
            return None
        
        states = list(self.hand_states[hand_id])
        
        if len(states) < 3:
            return None
        
        # Look for pattern: in_roi (no scooper) -> near_pizza
        was_in_roi = False
        had_scooper = False
        roi_name = None
        roi_frame = None
        
        for i, state in enumerate(states):
            # Check if hand was in ROI
            if state['in_roi']:
                was_in_roi = True
                roi_name = state['roi_name']
                roi_frame = state['frame']
                
                # Check if scooper was present
                if state['has_scooper']:
                    had_scooper = True
            
            # Check if hand moved to pizza after being in ROI
            if was_in_roi and state['near_pizza']:
                # If no scooper was detected when in ROI, it's a violation
                if not had_scooper:
                    return {
                        'hand_id': hand_id,
                        'violation_type': 'no_scooper',
                        'roi_name': roi_name,
                        'roi_frame': roi_frame,
                        'pizza_frame': state['frame'],
                        'hand_bbox': state['bbox'],
                        'confidence': 0.8
                    }
                
                # Reset for next potential violation
                was_in_roi = False
                had_scooper = False
        
        return None
    
    def cleanup_inactive_hands(self, active_hand_ids):
        """
        Remove tracking data for hands that are no longer detected
        
        Args:
            active_hand_ids: Set of currently active hand IDs
        """
        # Remove inactive hands from tracking
        inactive_ids = set(self.hand_states.keys()) - set(active_hand_ids)
        for hand_id in inactive_ids:
            # Keep the history but remove from active
            if hand_id in self.active_hands:
                del self.active_hands[hand_id]




