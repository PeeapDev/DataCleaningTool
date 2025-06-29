"""
User satisfaction tracking and analysis for the Education Data Cleaning Tool.
"""

import os
import json
import datetime
import logging
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Any, List, Optional

from app.utils.config import Config
from app.utils.reporting import CleaningReport


class SatisfactionTracker:
    """Tracks and analyzes user satisfaction with the data cleaning tool"""
    
    def __init__(self):
        """Initialize the satisfaction tracker"""
        self.config = Config()
        self.data_file = os.path.join(self.config._get_config_dir(), "satisfaction_data.json")
        self.satisfaction_data = self._load_data()
        
    def _load_data(self) -> Dict[str, Any]:
        """Load satisfaction data from file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Failed to load satisfaction data: {str(e)}")
                
        # Return empty data structure if file doesn't exist or loading fails
        return {
            "ratings": [],
            "comments": [],
            "features": {},
            "metrics": {}
        }
    
    def _save_data(self):
        """Save satisfaction data to file"""
        try:
            with open(self.data_file, "w") as f:
                json.dump(self.satisfaction_data, f, indent=2)
                
        except Exception as e:
            logging.error(f"Failed to save satisfaction data: {str(e)}")
    
    def record_satisfaction(self, rating: int, comments: Optional[str] = None, 
                           cleaning_result: Optional[Dict[str, Any]] = None):
        """
        Record user satisfaction with the data cleaning results
        
        Args:
            rating: User rating (1-5 scale)
            comments: Optional user comments
            cleaning_result: Optional cleaning results stats
        """
        # Check if user has opted out of data collection
        if not self.config.get("collect_feedback", True):
            return
            
        # Create rating entry
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "rating": rating,
            "comments": comments if comments else ""
        }
        
        # Add cleaning results if provided
        if cleaning_result:
            entry["total_records"] = cleaning_result.get("total_records", 0)
            entry["duplicates_found"] = cleaning_result.get("duplicate_records", 0)
            entry["clean_records"] = cleaning_result.get("clean_records", 0)
            entry["fuzzy_matching_used"] = cleaning_result.get("fuzzy_matching_used", False)
            entry["processing_time"] = cleaning_result.get("processing_time", 0)
        
        # Add to data
        self.satisfaction_data["ratings"].append(entry)
        
        if comments:
            self.satisfaction_data["comments"].append({
                "timestamp": entry["timestamp"],
                "comment": comments,
                "rating": rating
            })
            
        # Update metrics
        self._update_metrics()
        
        # Save data
        self._save_data()
        
        # Add to current report if available
        if cleaning_result and "report" in cleaning_result:
            report = cleaning_result["report"]
            if isinstance(report, CleaningReport):
                report.add_user_satisfaction_data(rating, comments)
    
    def record_feature_usage(self, feature: str):
        """
        Record usage of a specific feature
        
        Args:
            feature: Name of the feature used
        """
        # Check if user has opted out of data collection
        if not self.config.get("usage_tracking", True):
            return
            
        # Initialize feature if not present
        if feature not in self.satisfaction_data["features"]:
            self.satisfaction_data["features"][feature] = 0
            
        # Increment usage count
        self.satisfaction_data["features"][feature] += 1
        
        # Save data
        self._save_data()
    
    def _update_metrics(self):
        """Update satisfaction metrics based on collected data"""
        ratings = [entry["rating"] for entry in self.satisfaction_data["ratings"]]
        
        if not ratings:
            return
            
        # Calculate metrics
        self.satisfaction_data["metrics"] = {
            "count": len(ratings),
            "average_rating": sum(ratings) / len(ratings),
            "distribution": {str(i): ratings.count(i) for i in range(1, 6)},
            "last_updated": datetime.datetime.now().isoformat()
        }
    
    def get_average_rating(self) -> float:
        """Get the average satisfaction rating"""
        metrics = self.satisfaction_data.get("metrics", {})
        return metrics.get("average_rating", 0.0)
    
    def get_rating_count(self) -> int:
        """Get the total number of ratings"""
        metrics = self.satisfaction_data.get("metrics", {})
        return metrics.get("count", 0)
    
    def generate_satisfaction_report(self, output_file: Optional[str] = None) -> str:
        """
        Generate a report on user satisfaction
        
        Args:
            output_file: Optional file path to save the report
            
        Returns:
            Path to the saved report file
        """
        # Create report
        report = []
        report.append("=" * 60)
        report.append("USER SATISFACTION REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary section
        metrics = self.satisfaction_data.get("metrics", {})
        report.append("SUMMARY")
        report.append("-" * 60)
        report.append(f"Total ratings: {metrics.get('count', 0)}")
        report.append(f"Average rating: {metrics.get('average_rating', 0.0):.1f} / 5.0")
        report.append("")
        
        # Distribution
        report.append("RATING DISTRIBUTION")
        report.append("-" * 60)
        distribution = metrics.get("distribution", {})
        for i in range(5, 0, -1):
            count = distribution.get(str(i), 0)
            percentage = (count / metrics.get("count", 1)) * 100 if metrics.get("count", 0) > 0 else 0
            stars = "★" * i + "☆" * (5 - i)
            report.append(f"{stars} ({i}): {count} ({percentage:.1f}%)")
        report.append("")
        
        # Feature usage
        report.append("FEATURE USAGE")
        report.append("-" * 60)
        features = self.satisfaction_data.get("features", {})
        for feature, count in sorted(features.items(), key=lambda x: x[1], reverse=True):
            report.append(f"{feature}: {count}")
        report.append("")
        
        # Recent comments
        report.append("RECENT COMMENTS")
        report.append("-" * 60)
        comments = self.satisfaction_data.get("comments", [])
        for i, comment in enumerate(reversed(comments)):
            if i >= 5:  # Only show 5 most recent comments
                break
                
            timestamp = datetime.datetime.fromisoformat(comment["timestamp"]).strftime("%Y-%m-%d")
            stars = "★" * comment["rating"] + "☆" * (5 - comment["rating"])
            report.append(f"[{timestamp}] {stars}")
            report.append(f"\"{comment['comment']}\"")
            report.append("")
        
        # Compile report
        report_text = "\n".join(report)
        
        # Save to file if specified
        if output_file:
            try:
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                with open(output_file, "w") as f:
                    f.write(report_text)
            except Exception as e:
                logging.error(f"Failed to save satisfaction report: {str(e)}")
                
        return report_text
    
    def generate_satisfaction_charts(self, output_dir: Optional[str] = None) -> List[str]:
        """
        Generate charts visualizing satisfaction data
        
        Args:
            output_dir: Optional directory to save charts
            
        Returns:
            List of paths to generated chart files
        """
        if not output_dir:
            output_dir = os.path.join(self.config._get_config_dir(), "reports")
            
        os.makedirs(output_dir, exist_ok=True)
        
        # Create DataFrame from ratings
        ratings = self.satisfaction_data.get("ratings", [])
        if not ratings:
            return []
            
        df = pd.DataFrame(ratings)
        
        # Convert timestamp to datetime
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df["date"] = df["timestamp"].dt.date
            
        chart_files = []
        
        try:
            # Rating distribution pie chart
            plt.figure(figsize=(8, 6))
            ratings_count = df["rating"].value_counts().sort_index()
            plt.pie(ratings_count, labels=[f"{i} Stars" for i in ratings_count.index], 
                    autopct="%1.1f%%", startangle=90)
            plt.title("User Satisfaction Rating Distribution")
            pie_file = os.path.join(output_dir, "rating_distribution.png")
            plt.savefig(pie_file)
            plt.close()
            chart_files.append(pie_file)
            
            # Rating over time line chart
            if len(df) > 1 and "date" in df.columns:
                plt.figure(figsize=(10, 6))
                df_grouped = df.groupby("date")["rating"].mean()
                plt.plot(df_grouped.index, df_grouped.values, marker="o")
                plt.title("Average Rating Over Time")
                plt.xlabel("Date")
                plt.ylabel("Average Rating")
                plt.grid(True, linestyle="--", alpha=0.7)
                plt.ylim(0.5, 5.5)
                plt.yticks(range(1, 6))
                line_file = os.path.join(output_dir, "rating_trend.png")
                plt.savefig(line_file)
                plt.close()
                chart_files.append(line_file)
                
            # Feature usage bar chart
            features = self.satisfaction_data.get("features", {})
            if features:
                plt.figure(figsize=(10, 6))
                feature_names = list(features.keys())
                feature_counts = list(features.values())
                
                # Sort by count
                sorted_indices = sorted(range(len(feature_counts)), 
                                        key=lambda i: feature_counts[i], 
                                        reverse=True)
                sorted_names = [feature_names[i] for i in sorted_indices]
                sorted_counts = [feature_counts[i] for i in sorted_indices]
                
                plt.barh(sorted_names, sorted_counts)
                plt.title("Feature Usage")
                plt.xlabel("Usage Count")
                plt.tight_layout()
                feature_file = os.path.join(output_dir, "feature_usage.png")
                plt.savefig(feature_file)
                plt.close()
                chart_files.append(feature_file)
                
        except Exception as e:
            logging.error(f"Failed to generate satisfaction charts: {str(e)}")
            
        return chart_files
