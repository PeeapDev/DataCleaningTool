"""
Test data generator for Education Data Cleaning Tool.
Creates large sample datasets with controlled duplicates for testing.
"""

import pandas as pd
import numpy as np
import random
import datetime
import logging
from faker import Faker
import argparse
import os

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EducationDataGenerator:
    """Generate synthetic education data with controlled duplicates"""
    
    def __init__(self, locale='en_US'):
        """Initialize the data generator"""
        self.fake = Faker(locale)
        
        # Common academic years
        current_year = datetime.datetime.now().year
        self.academic_years = [str(year) for year in range(current_year-3, current_year+1)]
        
        # School IDs
        self.school_ids = [f"SCH{i:03d}" for i in range(1, 21)]
        
        # Grade levels
        self.grades = [str(i) for i in range(1, 13)]
    
    def generate_student(self):
        """Generate a single random student record"""
        first_name = self.fake.first_name()
        last_name = self.fake.last_name()
        
        # Generate date of birth for school-age children (5-18 years old)
        dob = self.fake.date_of_birth(minimum_age=5, maximum_age=18)
        
        # Select an academic year
        academic_year = random.choice(self.academic_years)
        
        # Create proper datetime objects for enrollment date
        year = int(academic_year)
        start_date = datetime.datetime(year, 8, 15)
        end_date = datetime.datetime(year, 9, 30)
        enrollment_date = self.fake.date_between_dates(start_date, end_date)
        
        return {
            'StudentName': f"{first_name} {last_name}",
            'DateOfBirth': dob.strftime('%Y-%m-%d'),
            'AcademicYear': academic_year,
            'Gender': random.choice(['M', 'F']),
            'Grade': random.choice(self.grades),
            'EnrollmentDate': enrollment_date.strftime('%Y-%m-%d'),
            'SchoolID': random.choice(self.school_ids)
        }
    
    def introduce_duplicates(self, df, duplicate_rate=0.15):
        """
        Introduce duplicates into the dataset
        
        Args:
            df: DataFrame to add duplicates to
            duplicate_rate: Percentage of records to duplicate (0.0-1.0)
            
        Returns:
            DataFrame with duplicates
        """
        num_records = len(df)
        num_duplicates = int(num_records * duplicate_rate)
        
        if num_duplicates == 0:
            return df
            
        # Select random records to duplicate
        indices = random.sample(range(num_records), num_duplicates)
        duplicates = df.iloc[indices].copy()
        
        # For some duplicates, introduce minor variations
        for i, row in duplicates.iterrows():
            if random.random() < 0.3:  # 30% chance of name variation
                name = row['StudentName']
                parts = name.split(' ')
                if random.random() < 0.5:  # Capitalization changes
                    if random.random() < 0.5:
                        duplicates.at[i, 'StudentName'] = name.upper()
                    else:
                        duplicates.at[i, 'StudentName'] = name.lower()
                else:  # Typo in name
                    first = parts[0]
                    if len(parts) > 1:
                        if len(first) > 3 and random.random() < 0.5:
                            # Swap two adjacent characters
                            pos = random.randint(0, len(first)-2)
                            first = first[:pos] + first[pos+1] + first[pos] + first[pos+2:]
                            duplicates.at[i, 'StudentName'] = f"{first} {' '.join(parts[1:])}"
            
            # Randomly change enrollment date for some duplicates
            if random.random() < 0.4:
                base_date = datetime.datetime.strptime(row['EnrollmentDate'], '%Y-%m-%d')
                days_diff = random.randint(1, 30)
                new_date = base_date + datetime.timedelta(days=days_diff)
                duplicates.at[i, 'EnrollmentDate'] = new_date.strftime('%Y-%m-%d')
        
        # Combine original data with duplicates
        result = pd.concat([df, duplicates], ignore_index=True)
        
        # Shuffle the records
        return result.sample(frac=1).reset_index(drop=True)
    
    def generate_dataset(self, num_records, duplicate_rate=0.15):
        """
        Generate a dataset with the specified number of records
        
        Args:
            num_records: Number of unique records to generate
            duplicate_rate: Percentage of records to duplicate
            
        Returns:
            DataFrame with generated data
        """
        # Generate the base dataset
        data = []
        for _ in range(num_records):
            data.append(self.generate_student())
        
        df = pd.DataFrame(data)
        
        # Add duplicates if requested
        if duplicate_rate > 0:
            df = self.introduce_duplicates(df, duplicate_rate)
        
        return df


def generate_education_data(output_path, num_records=1000, duplicate_rate=0.1, format="csv"):
    """Generate synthetic education data with controlled duplicates
    
    Args:
        output_path: Path to save the output data file
        num_records: Number of original records to generate
        duplicate_rate: Approximate percentage of duplicates to introduce
        format: Output format ('csv' or 'excel')
        
    Returns:
        Path to the generated file
    """
    generator = EducationDataGenerator()
    df = generator.generate_dataset(num_records, duplicate_rate)
    
    # Create directory if needed
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Save to selected format
    if format.lower() == "excel" or output_path.lower().endswith((".xlsx", ".xls")):
        engine = 'openpyxl' if output_path.lower().endswith(".xlsx") else 'xlwt'
        df.to_excel(output_path, index=False, engine=engine)
        logger.info(f"Saved data in Excel format to {output_path}")
    else:  # Default to CSV
        df.to_csv(output_path, index=False)
        logger.info(f"Saved data in CSV format to {output_path}")
    
    logger.info(f"Generated {len(df)} records with approximately {int(num_records * duplicate_rate)} duplicates")
    return output_path


def main():
    """Main function for command line usage"""
    parser = argparse.ArgumentParser(description="Generate synthetic education data.")
    parser.add_argument('--records', type=int, default=1000, help="Number of unique records")
    parser.add_argument('--duplicates', type=float, default=0.15, help="Duplicate rate (0.0-1.0)")
    parser.add_argument('--output', type=str, default="generated_data.csv", help="Output file name")
    parser.add_argument('--format', type=str, default="csv", help="Output format (csv or excel)")
    parser.add_argument('--seed', type=int, default=None, help="Random seed for reproducibility")
    
    args = parser.parse_args()
    
    # Set random seed if specified
    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)
    
    # Generate data
    output_path = generate_education_data(args.output, args.records, args.duplicates, args.format)
    print(f"Generated {args.records} records (with approximately {int(args.records * args.duplicates)} duplicates)")
    print(f"Saved to {os.path.abspath(output_path)}")


if __name__ == "__main__":
    main()
