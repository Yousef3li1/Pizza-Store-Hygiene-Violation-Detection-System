"""
ROI (Region of Interest) Manager
Handles ROI configuration and intersection calculations
"""
import cv2
import numpy as np
import json
from pathlib import Path


class ROIManager:
    """
    Manages Regions of Interest for violation detection
    """
    
    def __init__(self, rois=None):
        """
        Initialize ROI Manager
        
        Args:
            rois: List of ROI dictionaries with 'name', 'coords', 'color'
        """
        self.rois = rois or []
    
    def add_roi(self, name, coords, color=(0, 255, 0)):
        """
        Add a new ROI
        
        Args:
            name: ROI name
            coords: [x1, y1, x2, y2]
            color: BGR color tuple for visualization
        """
        self.rois.append({
            'name': name,
            'coords': coords,
            'color': color
        })
    
    def load_from_file(self, filepath):
        """Load ROIs from JSON file"""
        with open(filepath, 'r') as f:
            self.rois = json.load(f)
    
    def save_to_file(self, filepath):
        """Save ROIs to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.rois, f, indent=2)
    
    def calculate_iou(self, box1, box2):
        """
        Calculate Intersection over Union (IoU) between two boxes
        
        Args:
            box1, box2: [x1, y1, x2, y2]
        
        Returns:
            IoU value (0-1)
        """
        x1_inter = max(box1[0], box2[0])
        y1_inter = max(box1[1], box2[1])
        x2_inter = min(box1[2], box2[2])
        y2_inter = min(box1[3], box2[3])
        
        if x2_inter < x1_inter or y2_inter < y1_inter:
            return 0.0
        
        intersection = (x2_inter - x1_inter) * (y2_inter - y1_inter)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def is_hand_in_roi(self, hand_bbox, roi_coords, threshold=0.3):
        """
        Check if hand bbox intersects with ROI
        
        Args:
            hand_bbox: [x1, y1, x2, y2]
            roi_coords: [x1, y1, x2, y2]
            threshold: Minimum IoU to consider hand in ROI
        
        Returns:
            Boolean
        """
        iou = self.calculate_iou(hand_bbox, roi_coords)
        return iou >= threshold
    
    def get_hand_roi_intersections(self, hand_bbox, threshold=0.3):
        """
        Get all ROIs that intersect with the hand
        
        Args:
            hand_bbox: [x1, y1, x2, y2]
            threshold: Minimum IoU threshold
        
        Returns:
            List of ROI dictionaries that intersect
        """
        intersecting_rois = []
        for roi in self.rois:
            if self.is_hand_in_roi(hand_bbox, roi['coords'], threshold):
                intersecting_rois.append(roi)
        
        return intersecting_rois
    
    def draw_rois(self, frame):
        """
        Draw ROIs on frame
        
        Args:
            frame: OpenCV image
        
        Returns:
            Frame with ROIs drawn
        """
        frame_copy = frame.copy()
        
        for roi in self.rois:
            x1, y1, x2, y2 = roi['coords']
            color = roi['color']
            
            # Draw rectangle
            cv2.rectangle(frame_copy, (x1, y1), (x2, y2), color, 2)
            
            # Draw label
            label = roi['name']
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            thickness = 2
            
            (text_width, text_height), baseline = cv2.getTextSize(
                label, font, font_scale, thickness
            )
            
            # Background for text
            cv2.rectangle(
                frame_copy,
                (x1, y1 - text_height - baseline - 5),
                (x1 + text_width, y1),
                color,
                -1
            )
            
            # Text
            cv2.putText(
                frame_copy,
                label,
                (x1, y1 - 5),
                font,
                font_scale,
                (0, 0, 0),
                thickness
            )
        
        return frame_copy




