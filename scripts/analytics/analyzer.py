"""
Analytics and data analysis utilities.

Place your analytics scripts here.
Example functions:
- calculate_price_trends(price_data)
- analyze_sentiment(text)
- compare_competitors(competitor_data)
"""

import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def calculate_trend(values, dates):
    """
    Calculate trend direction and strength.
    
    Args:
        values: List of numeric values
        dates: List of corresponding dates
    
    Returns:
        Dictionary with trend information
    """
    if len(values) < 2:
        return {'direction': 'stable', 'confidence': 0}
    
    try:
        # Simple linear regression
        x = np.arange(len(values))
        y = np.array(values)
        
        # Calculate slope
        slope = np.polyfit(x, y, 1)[0]
        
        # Determine direction
        if slope > 0.1:
            direction = 'up'
        elif slope < -0.1:
            direction = 'down'
        else:
            direction = 'stable'
        
        # Calculate confidence (R-squared)
        correlation = np.corrcoef(x, y)[0, 1]
        confidence = abs(correlation)
        
        return {
            'direction': direction,
            'confidence': confidence,
            'slope': slope
        }
    
    except Exception as e:
        logger.error(f"Error calculating trend: {str(e)}")
        return {'direction': 'stable', 'confidence': 0}


def calculate_change_percentage(old_value, new_value):
    """
    Calculate percentage change between two values.
    
    Args:
        old_value: Original value
        new_value: New value
    
    Returns:
        Percentage change
    """
    if old_value == 0:
        return 0
    
    return ((new_value - old_value) / old_value) * 100


# Add your existing analytics functions here
