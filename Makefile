# Define variables
PYTHON=python
SCRIPT_SCRAPE_PROGRAMMES=scrapers/scrape_programmes_uqam.py
SCRIPT_SCRAPE_COURS=scrapers/scrape_cours_uqam.py
SCRIPT_CSV_TO_SQL=scripts/convert_csv_to_sql.py
SCRIPT_SIGLES_TO_JSON=scripts/sigles_to_json.py
RAW_COURS=static/data/raw_liste_cours.txt
CLEAN_COURS=static/data/liste_cours.txt
RAW_DATA=static/data/raw_data_uqam.csv
CLEAN_DATA=static/data/data_uqam.csv
DB_FILE=static/data/database.db
APP=app.py

# Define rules
.PHONY: all scrape_programmes scrape_cours scrape_all run clean

all: scrape_all run

# Rule to scrape program data
scrape_programmes:
	@echo "Scraping program data..."
	$(PYTHON) $(SCRIPT_SCRAPE_PROGRAMMES)
	@echo "Removing old cleaned course list..."
	rm -f $(CLEAN_COURS)
	@echo "Generating unique course list..."
	grep -oE '[A-Z]{3}[0-9]{4}' $(RAW_COURS) | sort | uniq > $(CLEAN_COURS)
	@echo "Program data scraping completed."

# Rule to scrape class details
scrape_cours:
	@echo "Scraping course details..."
	$(PYTHON) $(SCRIPT_SCRAPE_COURS)
	@echo "Removing old cleaned data file..."
	rm -f $(CLEAN_DATA)
	@echo "Generating unique course data..."
	cat $(RAW_DATA) | sort | uniq > $(CLEAN_DATA)
	@echo "Removing old database file..."
	rm -f $(DB_FILE)
	@echo "Converting CSV to SQL..."
	$(PYTHON) $(SCRIPT_CSV_TO_SQL)
	@echo "Generating JSON from course sigles..."
	$(PYTHON) $(SCRIPT_SIGLES_TO_JSON)
	@echo "Course details scraping completed."

# Rule to scrape and update both programs and class details
scrape_all: scrape_programmes scrape_cours
	@echo "Scraping programs and courses completed."

# Rule to run the program
run:
	@echo "Starting the application..."
	$(PYTHON) $(APP)
	@echo "Application exited."

# Rule to clean up generated files
clean:
	@echo "Cleaning up raw data files..."
	rm -f $(RAW_COURS) $(RAW_DATA) 
	@echo "Cleanup completed."
