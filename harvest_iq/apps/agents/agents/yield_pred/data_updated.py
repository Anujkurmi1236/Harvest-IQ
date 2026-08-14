import pandas as pd
import os
import glob
from pathlib import Path
import json
from datetime import datetime

class IndiaDataExtractor:
    """Class to handle India-specific data extraction from FAOSTAT files"""
    
    def __init__(self, base_dir, output_dir):
        self.base_dir = base_dir
        self.output_dir = output_dir
        self.india_codes = [100, 356]  # Area codes for India
        self.india_name = 'India'
        
        # More flexible file patterns - can be partial names
        self.file_patterns = [
            "Environment_Temperature_change",
            "Environment_Soil_nutrient",
            "Inputs_FertilizersNutrient",
            "Production_Crops_Livestock",
            "Inputs_FertilizersProduct"
        ]
        
        # Create output directory
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
    
    def find_files(self, pattern):
        """Find files matching pattern with various extensions and locations"""
        found_files = []
        
        # Search patterns with different extensions
        extensions = ['*.csv', '*.CSV', '*.txt', '*.data', '*.dat']
        
        # Search in base directory and subdirectories
        search_dirs = [self.base_dir] + [os.path.join(self.base_dir, d) for d in os.listdir(self.base_dir) 
                                         if os.path.isdir(os.path.join(self.base_dir, d))]
        
        for search_dir in search_dirs:
            for ext in extensions:
                # Search for files that contain the pattern in their name
                search_pattern = os.path.join(search_dir, f"*{pattern}*{ext}")
                files = glob.glob(search_pattern)
                found_files.extend(files)
                
                # Also search for files without extension
                search_pattern = os.path.join(search_dir, f"*{pattern}*")
                files = glob.glob(search_pattern)
                # Filter out directories
                files = [f for f in files if os.path.isfile(f)]
                found_files.extend(files)
        
        # Remove duplicates
        found_files = list(set(found_files))
        
        return found_files
    
    def detect_file_format(self, file_path):
        """Detect the file format and read it accordingly"""
        try:
            # Try reading as CSV with different encodings and delimiters
            encodings = ['utf-8', 'latin1', 'ISO-8859-1', 'cp1252']
            delimiters = [',', ';', '\t', '|']
            
            for encoding in encodings:
                for delimiter in delimiters:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding, delimiter=delimiter)
                        if len(df.columns) > 1:  # Valid dataframe
                            return df
                    except:
                        continue
            
            # Try reading with automatic delimiter detection
            try:
                df = pd.read_csv(file_path, encoding='utf-8', sep=None, engine='python')
                return df
            except:
                pass
            
            # Try reading as Excel
            try:
                df = pd.read_excel(file_path)
                return df
            except:
                pass
            
            # Try reading as JSON
            try:
                df = pd.read_json(file_path)
                return df
            except:
                pass
            
            return None
            
        except Exception as e:
            print(f"   Error reading file: {str(e)}")
            return None
    
    def extract_india_data(self, df, filename):
        """Extract India-specific data from dataframe"""
        if df is None or len(df) == 0:
            return None
        
        india_data = None
        
        # Check what columns are available
        columns_lower = [col.lower() for col in df.columns]
        
        # Method 1: Area column with India
        if 'area' in columns_lower or 'Area' in df.columns:
            col_name = 'Area' if 'Area' in df.columns else 'area'
            india_data = df[df[col_name].astype(str).str.contains('India', case=False, na=False)]
        
        # Method 2: Area Code for India
        if (india_data is None or len(india_data) == 0):
            for col in ['Area Code', 'AreaCode', 'area_code', 'M49 Code', 'M49Code']:
                if col in df.columns:
                    india_data = df[df[col].isin(self.india_codes)]
                    if len(india_data) > 0:
                        break
        
        # Method 3: Check if 'Area' contains India code
        if (india_data is None or len(india_data) == 0):
            for col in ['Area', 'area']:
                if col in df.columns:
                    # Check for India codes in area column
                    india_data = df[df[col].astype(str).str.contains('100|356', na=False)]
                    if len(india_data) > 0:
                        break
        
        return india_data
    
    def process_file(self, pattern):
        """Process files matching a pattern"""
        print(f"\n🔍 Searching for files matching: {pattern}")
        
        files = self.find_files(pattern)
        
        if not files:
            print(f"⚠️  No files found for pattern: {pattern}")
            return
        
        print(f"   Found {len(files)} file(s)")
        
        for file_path in files:
            try:
                filename = os.path.basename(file_path)
                file_dir = os.path.dirname(file_path)
                print(f"\n📂 Processing: {filename}")
                print(f"   Location: {file_dir}")
                
                # Detect and read the file
                df = self.detect_file_format(file_path)
                
                if df is None:
                    print(f"   ❌ Could not read file")
                    continue
                
                print(f"   📊 File Info:")
                print(f"      - Total rows: {len(df)}")
                print(f"      - Columns: {len(df.columns)}")
                print(f"      - Column names: {', '.join(df.columns[:5])}...")
                
                if 'Year' in df.columns:
                    print(f"      - Year range: {df['Year'].min()}-{df['Year'].max()}")
                
                # Extract India data
                india_data = self.extract_india_data(df, filename)
                
                if india_data is None or len(india_data) == 0:
                    print(f"   ❌ No India data found in this file")
                    print(f"      Area values present: {df['Area'].unique()[:5] if 'Area' in df.columns else 'No Area column'}")
                    continue
                
                print(f"   ✅ Found {len(india_data)} records for India")
                
                # Create clean filename for output
                base_name = filename.split('.')[0]
                output_filename = f"india_{base_name}.csv"
                output_path = os.path.join(self.output_dir, output_filename)
                
                # Save the filtered data
                india_data.to_csv(output_path, index=False)
                print(f"   💾 Saved to: {output_path}")
                
                # Create summary
                self.create_summary(india_data, base_name)
                
            except Exception as e:
                print(f"   ❌ Error processing {file_path}: {str(e)}")
                import traceback
                traceback.print_exc()
    
    def create_summary(self, india_data, file_name):
        """Create statistical summary of India data"""
        summary_file = os.path.join(self.output_dir, f"summary_{file_name}.txt")
        
        try:
            with open(summary_file, 'w') as f:
                f.write(f"INDIA DATA SUMMARY: {file_name}\n")
                f.write("=" * 60 + "\n\n")
                
                f.write(f"Total Records: {len(india_data)}\n")
                
                if 'Year' in india_data.columns:
                    f.write(f"Year Range: {india_data['Year'].min()} - {india_data['Year'].max()}\n")
                
                if 'Item' in india_data.columns:
                    f.write(f"Unique Items: {len(india_data['Item'].unique())}\n")
                    try:
                        top_items = india_data['Item'].value_counts().head(5)
                        f.write(f"Top 5 Items:\n")
                        for item, count in top_items.items():
                            f.write(f"  - {item}: {count}\n")
                    except:
                        pass
                
                if 'Element' in india_data.columns:
                    f.write(f"Unique Elements: {len(india_data['Element'].unique())}\n")
                
                if 'Unit' in india_data.columns:
                    f.write(f"Units: {', '.join(india_data['Unit'].unique().tolist())}\n")
                
                # Add statistical summary for numeric values
                if 'Value' in india_data.columns:
                    try:
                        values = pd.to_numeric(india_data['Value'], errors='coerce')
                        if len(values.dropna()) > 0:
                            f.write(f"\nValue Statistics:\n")
                            f.write(f"  Mean: {values.mean():.2f}\n")
                            f.write(f"  Median: {values.median():.2f}\n")
                            f.write(f"  Min: {values.min():.2f}\n")
                            f.write(f"  Max: {values.max():.2f}\n")
                            f.write(f"  Std Dev: {values.std():.2f}\n")
                    except:
                        pass
                
                # Add flag distribution if available
                if 'Flag' in india_data.columns:
                    f.write(f"\nFlag Distribution:\n")
                    for flag, count in india_data['Flag'].value_counts().items():
                        f.write(f"  {flag}: {count}\n")
                    
            print(f"   📝 Summary saved to: {summary_file}")
        except Exception as e:
            print(f"   ⚠️ Could not create summary: {str(e)}")
    
    def run(self):
        """Execute the extraction process"""
        print("🚀 Starting India Data Extraction")
        print("=" * 60)
        print(f"📁 Input directory: {self.base_dir}")
        print(f"📁 Output directory: {self.output_dir}")
        print("=" * 60)
        
        # First, let's check what files are available
        print("\n🔍 Scanning for available files...")
        all_csv_files = glob.glob(os.path.join(self.base_dir, "**/*.csv"), recursive=True)
        all_files = glob.glob(os.path.join(self.base_dir, "**/*"), recursive=True)
        
        print(f"   Found {len(all_csv_files)} CSV files total")
        if len(all_csv_files) > 0:
            print("\n   Available CSV files:")
            for f in all_csv_files[:10]:  # Show first 10
                print(f"      - {os.path.basename(f)}")
            if len(all_csv_files) > 10:
                print(f"      ... and {len(all_csv_files) - 10} more")
        
        # Process each file pattern
        processed_count = 0
        for pattern in self.file_patterns:
            self.process_file(pattern)
            processed_count += 1
        
        # Check if any India data was saved
        saved_files = os.listdir(self.output_dir)
        if saved_files:
            print(f"\n📊 India Data Files Created:")
            for file in sorted(saved_files):
                if file.startswith('india_'):
                    file_path = os.path.join(self.output_dir, file)
                    df = pd.read_csv(file_path)
                    print(f"   ✅ {file}: {len(df)} records")
        else:
            print("\n⚠️ No India data was extracted. Let's check what data is available...")
            self.debug_data_structure()
        
        print("\n✅ Extraction complete!")
        print(f"📂 All output saved in: {self.output_dir}")
        print(f"📄 Total files created: {len(saved_files)}")
    
    def debug_data_structure(self):
        """Debug function to check data structure of available files"""
        print("\n🔍 Debugging - Checking data structure...")
        
        all_csv_files = glob.glob(os.path.join(self.base_dir, "**/*.csv"), recursive=True)
        
        for csv_file in all_csv_files[:3]:  # Check first 3 files
            try:
                df = pd.read_csv(csv_file, nrows=5)
                print(f"\nFile: {os.path.basename(csv_file)}")
                print(f"Columns: {df.columns.tolist()}")
                print(f"First rows:")
                print(df.head())
                
                # Check for India-related data
                if 'Area' in df.columns:
                    print(f"Area values: {df['Area'].unique()[:5]}")
            except Exception as e:
                print(f"Error reading {csv_file}: {str(e)}")

if __name__ == "__main__":
    # Initialize with your paths
    extractor = IndiaDataExtractor(
        base_dir="harvest_iq/apps/agents/agents/yield_pred/data",
        output_dir="harvest_iq/apps/agents/agents/yield_pred/data/india_specific_data"
    )
    extractor.run()