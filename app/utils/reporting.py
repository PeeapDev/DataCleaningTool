"""
Reporting utilities for the Education Data Cleaning Tool.
Generates reports and visualizations on data cleaning results.
"""

import os
import pandas as pd
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import matplotlib.pyplot as plt
from matplotlib.figure import Figure


class CleaningReport:
    """Generates reports on data cleaning results"""
    
    def __init__(self, output_dir: str = None):
        """
        Initialize the reporting module
        
        Args:
            output_dir: Directory to save reports (defaults to current directory)
        """
        self.output_dir = output_dir or "reports"
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            try:
                os.makedirs(self.output_dir)
            except Exception as e:
                logging.error(f"Failed to create reports directory: {str(e)}")
                self.output_dir = "."
        
        # Report data
        self.report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {},
            "details": {}
        }
    
    def set_summary_stats(self, stats: Dict[str, Any]):
        """
        Set summary statistics for the report
        
        Args:
            stats: Dictionary of summary statistics
        """
        self.report_data["summary"] = stats
    
    def add_detail_section(self, section_name: str, data: Any):
        """
        Add a section to the detailed report
        
        Args:
            section_name: Name of the section
            data: Data for the section
        """
        self.report_data["details"][section_name] = data
    
    def generate_text_report(self, output_file: str = None) -> str:
        """
        Generate a text report of the cleaning results
        
        Args:
            output_file: File to save the report to (optional)
            
        Returns:
            Text report as a string
        """
        timestamp = datetime.fromisoformat(self.report_data["timestamp"])
        
        # Build the report text
        report = []
        report.append("=" * 60)
        report.append("EDUCATION DATA CLEANING REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary section
        report.append("SUMMARY")
        report.append("-" * 60)
        
        summary = self.report_data["summary"]
        for key, value in summary.items():
            report.append(f"{key}: {value}")
        report.append("")
        
        # Details sections
        report.append("DETAILS")
        report.append("-" * 60)
        
        for section, data in self.report_data["details"].items():
            report.append(f"{section}:")
            
            # Format based on data type
            if isinstance(data, dict):
                for k, v in data.items():
                    report.append(f"  {k}: {v}")
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            report.append(f"  {k}: {v}")
                        report.append("")
                    else:
                        report.append(f"  {item}")
            else:
                report.append(f"  {data}")
            report.append("")
        
        # User satisfaction section if available
        if "user_satisfaction" in self.report_data["details"]:
            report.append("USER SATISFACTION")
            report.append("-" * 60)
            satisfaction = self.report_data["details"]["user_satisfaction"]
            for key, value in satisfaction.items():
                report.append(f"{key}: {value}")
            report.append("")
        
        # Compile final report
        report_text = "\n".join(report)
        
        # Save to file if specified
        if output_file:
            try:
                with open(os.path.join(self.output_dir, output_file), 'w') as f:
                    f.write(report_text)
            except Exception as e:
                logging.error(f"Failed to save report: {str(e)}")
        
        return report_text
    
    def save_json_report(self, output_file: str = None) -> str:
        """
        Save report data as JSON
        
        Args:
            output_file: File to save the report to (optional)
            
        Returns:
            Path to saved file or empty string if not saved
        """
        if not output_file:
            output_file = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
        output_path = os.path.join(self.output_dir, output_file)
        
        try:
            with open(output_path, 'w') as f:
                json.dump(self.report_data, f, indent=2)
            return output_path
        except Exception as e:
            logging.error(f"Failed to save JSON report: {str(e)}")
            return ""
    
    def generate_summary_chart(self, chart_type: str, output_file: str = None) -> Optional[Figure]:
        """
        Generate a chart visualization of cleaning results
        
        Args:
            chart_type: Type of chart ('pie', 'bar', etc.)
            output_file: File to save the chart to (optional)
            
        Returns:
            Matplotlib figure object or None if failed
        """
        try:
            # Create figure
            fig, ax = plt.subplots(figsize=(8, 6))
            
            summary = self.report_data["summary"]
            
            if chart_type == "pie" and "total_records" in summary and "duplicates_found" in summary:
                # Data for pie chart
                labels = ['Clean Records', 'Duplicates']
                clean = summary["total_records"] - summary["duplicates_found"]
                sizes = [clean, summary["duplicates_found"]]
                
                ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
                ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
                plt.title("Clean vs Duplicate Records")
                
            elif chart_type == "bar":
                # Example bar chart
                cats = []
                values = []
                
                # Get numeric values from summary for bar chart
                for key, value in summary.items():
                    if isinstance(value, (int, float)) and key != "processing_time":
                        cats.append(key)
                        values.append(value)
                
                ax.bar(cats, values)
                plt.title("Data Cleaning Summary")
                plt.xticks(rotation=45, ha="right")
                
            # Save if output file specified
            if output_file:
                plt.tight_layout()
                plt.savefig(os.path.join(self.output_dir, output_file))
            
            return fig
            
        except Exception as e:
            logging.error(f"Failed to generate chart: {str(e)}")
            return None
    
    def add_user_satisfaction_data(self, rating: int, comments: str = None):
        """
        Add user satisfaction data to the report
        
        Args:
            rating: User rating (1-5)
            comments: Optional user comments
        """
        satisfaction = {
            "rating": rating,
            "timestamp": datetime.now().isoformat()
        }
        
        if comments:
            satisfaction["comments"] = comments
        
        self.add_detail_section("user_satisfaction", satisfaction)
    
    def get_report_list(self) -> List[str]:
        """
        Get a list of existing reports in the output directory
        
        Returns:
            List of report file paths
        """
        reports = []
        try:
            for file in os.listdir(self.output_dir):
                if file.endswith((".json", ".txt", ".pdf", ".png")):
                    reports.append(os.path.join(self.output_dir, file))
        except Exception as e:
            logging.error(f"Failed to list reports: {str(e)}")
        
        return reports
