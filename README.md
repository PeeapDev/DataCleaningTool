# Education Data Cleaning Tool

A native-first application for cleaning education datasets by identifying and removing duplicate student records, with full offline functionality.

## Features

- Import and export data in both CSV and Excel formats (.xlsx, .xls)
- Detect duplicate student records based on name, date of birth, and academic year
- Support for exact and fuzzy name matching
- Memory-efficient processing for large datasets (300,000+ records)
- Export clean data and duplicates to separate files
- Generate detailed summary reports of cleaning actions
- Complete offline functionality with native performance
- User satisfaction tracking to continuously improve the application

## Installation

### For End Users (Recommended)

#### macOS Installation
1. Download the `.dmg` file from the releases page
2. Open the `.dmg` file
3. Drag the Education Data Cleaner icon to your Applications folder
4. Launch from Applications

#### Windows Installation
1. Download the `.exe` installer from the releases page
2. Run the installer and follow the prompts
3. Launch from the Start Menu or desktop shortcut

### For Developers

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   python run.py
   ```

## Building Native Applications

### For macOS:
```bash
pyinstaller --name "EducationDataCleaner" \
            --windowed \
            --icon=resources/icons/app_icon.icns \
            --add-data "resources:resources" \
            app/main.py
```

### For Windows:
```bash
pyinstaller --name "EducationDataCleaner" ^
            --windowed ^
            --icon=resources\icons\app_icon.ico ^
            --add-data "resources;resources" ^
            app\main.py
```

## Development

This project uses:
- PyQt6 for the user interface
- Pandas for data processing and data analysis
- fuzzywuzzy for fuzzy string matching
- openpyxl and xlrd for Excel file support

## Future Enhancements

- API integration for centralized data management
- Advanced cloud-based reporting capabilities
- Continuous improvements based on user satisfaction feedback
- Enhanced data cleaning algorithms

## Building from Source

We've included a build script that handles packaging for both macOS and Windows:

```bash
python build_app.py
```

This will automatically create the appropriate package for your current platform (.dmg for macOS, .exe for Windows).

## License

MIT
