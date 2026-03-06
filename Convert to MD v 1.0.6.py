# Select distinct
#     TEST_DESCRIPTION,
#     t.TEST_NAME,
#     test_script,
#     t.WORKSPACE_NAME, --- Delete this, just use for validating query.
#     t.space_name, --- Delete this, just use for validating query.
#     TEST_SCRIPT_TEST_ID, --- Delete this, just use for validating query.
#     t.Test_id --- Delete this, just use for validating query.

# From (
#     Select s.WORKSPACE_NAME,
#         s.space_name,
#         s.TEST_SCRIPT_TEST_ID,
#         s.Test_script
#     FROM BAQARM_Reporting.oct.IE_TEST_SCRIPT as S
#     inner join (
#         Select Max(test_Script_ID) as 'test_Script_ID',
#             WORKSPACE_NAME,
#             space_name,
#             TEST_SCRIPT_TEST_ID
#         From BAQARM_Reporting.oct.IE_TEST_SCRIPT
#         where workspace_name = 'AM&R' ----Update this for the correct space add additional criteria here based on Test leads.
#         group by WORKSPACE_NAME,
#             space_name,
#             TEST_SCRIPT_TEST_ID ) as MS 
#     on ms.workspace_name = S.WORKSPACE_name and MS.space_name = S.space_name and MS.test_script_ID = S.Test_script_ID) as TS 
# left join BAQARM_Reporting.oct.IE_Test as t on test_ID = TEST_SCRIPT_TEST_ID and T.workspace_name = TS.WORKSPACE_NAME and T.space_name = TS.SPACE_NAME
# and (TEST_REPORTING_TEAM = 'IE-BSS') -- Update this to help narrow down test teams.

import csv
import re
import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
import os
from spellchecker import SpellChecker
from collections import Counter, defaultdict
import time
from openpyxl import Workbook, load_workbook
import contractions
# from pycontractions import Contractions
# import gensim.downloader as api
import pandas as pd
import pandas as pd
from bs4 import BeautifulSoup
import requests
from requests.auth import HTTPBasicAuth
from atlassian import Confluence
import sys
import importlib.util, os
import matplotlib.pyplot as plt
cred_path = os.path.join(os.path.dirname(__file__), 'PythonCred', 'cred.py')
spec = importlib.util.spec_from_file_location('cred', cred_path)
cred = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cred)
from io import StringIO

uid=cred.uid 
pw = cred.pw
path = cred.path
kw = cred.pth2

# Load a pre-trained word2vec model for pycontractions
# w2v = api.load("glove-wiki-gigaword-100")
# cont = Contractions(w2v)

# Create a pop-up window for user input
def get_user_input():
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    while True:
        user_input = simpledialog.askstring("Input", "Enter the MD file name (alphanumeric characters only):")
        if user_input and re.match("^[a-zA-Z0-9]+$", user_input):
            return user_input
        else:
            messagebox.showerror("Invalid input", "Please enter a name with alphanumeric characters only.")

# Function to remove HTML tags
def remove_html_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, ' ', text)

# Function to replace underscores with spaces
def replace_underscores(text):
    return text.replace('_', ' ')

# Create a pop-up window for file selection
def get_file_path():
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    file_path = filedialog.askopenfilename(
        title="Select CSV or Excel File",
        filetypes=(("CSV files", "*.csv"), ("Excel files", "*.xlsx"), ("All files", "*.*"))
    )
    return file_path

# Create a pop-up window for inputing an html link
def get_html_file_path_Chalk():
# pop-up window for text entry of url
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    url = simpledialog.askstring("Input", "Please enter the URL of the Acyronyms:")
    confluence = Confluence(url=url, username=uid, password=pw)
    r = requests.get(url, auth=HTTPBasicAuth(confluence.username, confluence.password))
    html = r.content
    # Parse HTML 
    soup = BeautifulSoup(html, 'html.parser')
    tables = soup.find_all('table')  # Find all tables in the HTML
    
    # Extract the first table (you can modify this to extract other tables if needed)
    table = tables[0]
    
    # Convert HTML table to DataFrame
    df = pd.read_html(StringIO(str(table)))[0]
    return df

# Function to read acronyms from the Excel file
def read_acronyms(df):
    acronyms = dict(zip(df.iloc[:, 0].astype(str), df.iloc[:, 1].astype(str)))
    return acronyms

# Function to replace acronyms in the text
def replace_acronyms(text, acronyms):
    if acronyms is None:
        return text
    for acronym, full_form in acronyms.items():
        text = re.sub(r'[\s\W]+' + re.escape(acronym) + r'[\s\W]+', ' '+ full_form +' ', text, flags=re.IGNORECASE)
    return text

# Function to check for misspelled words, ignoring numbers, URLs, and SQL statements
def get_misspelled_words(text):
    spell = SpellChecker()
    # Remove URLs from the text
    text_without_urls = re.sub(r'https?://\S+|www\.\S+', '', text)
    # Remove SQL statements (basic pattern matching for common SQL keywords)
    sql_keywords = r'\b(SELECT|FROM|WHERE|JOIN|ON|GROUP BY|ORDER BY|INSERT INTO|UPDATE|DELETE|CREATE|DROP|ALTER|TABLE|DISTINCT|AND|OR|NOT|IN|LIKE|IS NULL|IS NOT NULL|UNION|ALL|HAVING|LIMIT|OFFSET)\b'
    text_without_sql = re.sub(sql_keywords, '', text_without_urls, flags=re.IGNORECASE)
    # Extract words (ignoring numbers)
    words = re.findall(r'\b[a-zA-Z]+\b', text_without_sql)
    misspelled = spell.unknown(words)
    return misspelled

# Function to create an Excel file for reviewing misspelled words
def create_review_excel(misspelled_dict, file_path):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Misspelled Words"
    sheet.append(['Misspelled Word', 'Suggested Word 1', 'Suggested Word 2', 'Suggested Word 3', 'Count'])
    spell = SpellChecker()
    for word, details in misspelled_dict.items():
        suggestions = spell.candidates(word)
        if suggestions is None:
            suggestions = []
        suggestions = list(suggestions)[:3]  # Get up to 3 suggestions
        # Pad the suggestions list with None to ensure it has exactly 3 elements
        while len(suggestions) < 3:
            suggestions.append(None)
        sheet.append([word] + suggestions + [details['count']])
    workbook.save(file_path)

# Function to read corrections from the Excel file
def read_corrections_from_excel(file_path):
    df = pd.read_excel(file_path)
    corrections = dict(zip(df.iloc[:, 0].astype(str), df.iloc[:, 1].astype(str)))
    return corrections

# Get the file path from the use
file_path = get_file_path()

# Print the header and first five rows of the input file
if file_path.endswith('.csv'):
    with open(file_path, mode='r', encoding='utf-8-sig') as csv_file:
        csv_reader = csv.reader(csv_file)
        header = next(csv_reader)
        print("Header:", header)
        for i, row in enumerate(csv_reader):
            if i < 5:
                print(f"Row {i + 1}:", row)
            else:
                break
else:
    df = pd.read_excel(file_path)
    print("Header:", df.columns.tolist())
    for i, row in df.iterrows():
        if i < 5:
            print(f"Row {i + 1}:", row.tolist())
        else:
            break

# Get user input for the MD file name
user_input = get_user_input()

# Ask the user if they want to replace words with acronyms
root = tk.Tk()
root.withdraw()  # Hide the root window

# Ask the user if they want to replace words with acronyms
fix_acronyms = messagebox.askyesno("Replace Acronyms", "Do you want to replace words with acronyms?")

# Ask the user if they want to fix misspellings
fix_misspellings = messagebox.askyesno("Fix Misspellings", "Do you want to fix misspellings?")

# Ask the user if they have already reviewed misspellings and have a file similar to the misspelling output file
root = tk.Tk()
root.withdraw()  # Hide the root window
reviewed_misspellings = messagebox.askyesno(
    "Misspelling Review",
    "Have you already reviewed misspellings and do you have a file similar to the misspelling output file you want to add in?"
)

# Define reviewed_words based on user input
if reviewed_misspellings:
    # Prompt user to select the reviewed Excel file
    reviewed_file_path = filedialog.askopenfilename(
        title="Select Reviewed Misspelled Words Excel File",
        filetypes=(("Excel files", "*.xlsx"), ("All files", "*.*"))
    )
    if reviewed_file_path:
        reviewed_df = pd.read_excel(reviewed_file_path)
        reviewed_words = set(str(word).lower() for word in reviewed_df.iloc[:, 0].tolist())
    else:
        reviewed_words = set()
else:
    reviewed_words = set()

# If replacing acronyms, get the Excel file path with acronyms from the user
if fix_acronyms:
    excel_file_path = get_html_file_path_Chalk()
    acronyms = read_acronyms(excel_file_path)
else:
    acronyms = None

# Construct the MD file path in the same directory as the input file
file_directory = os.path.dirname(file_path)
md_file_path = os.path.join(file_directory, f'{user_input}.md')

# Construct the misspelled words Excel file path
file_name = os.path.splitext(os.path.basename(file_path))[0]
misspelled_excel_file_path = os.path.join(file_directory, f'{file_name}_misspelled_words.xlsx')

# Print the original file size
file_size = os.path.getsize(file_path)
print(f"Original file size: {file_size} bytes")

# Start the timer
start_time = time.time()

# Get the column name from the user
column_name = simpledialog.askstring("Input", "Enter the column name to calculate average character length:")

# Read the input file and convert it to a list of dictionaries
word_count = 0
misspelled_counter = Counter()
misspelled_dict = defaultdict(lambda: {'corrected': '', 'count': 0, 'originals': []})
total_characters = 0
num_rows = 0
max_length = 0
min_length = float('inf')
total_length = []

if file_path.endswith('.csv'):
    with open(file_path, mode='r', encoding='utf-8-sig') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        data = []
        for row in csv_reader:
            cleaned_row = {key: remove_html_tags(str(value)) for key, value in row.items()}
            cleaned_row = {key: contractions.fix(value) for key, value in cleaned_row.items()}
           # cleaned_row = {key: replace_underscores(value) for key, value in cleaned_row.items()}
            if fix_acronyms:
                cleaned_row = {key: replace_acronyms(value, acronyms) for key, value in cleaned_row.items()}
            data.append(cleaned_row)
            for key, cell in cleaned_row.items():
                if cell.startswith('{"value":"- '):
                    cell = cell.replace('{"value":"- ', '')
                if cell.endswith('}'):
                    cell = cell[:-1]
                cleaned_row[key] = cell
                if fix_misspellings:
                    misspelled_words = get_misspelled_words(cell)
                    for word in misspelled_words:
                        if word.lower() in reviewed_words:
                            continue
                        corrected_word = word  # Placeholder for actual correction logic
                        misspelled_counter.update([word])
                        misspelled_dict[word]['corrected'] = corrected_word
                        misspelled_dict[word]['count'] += 1
                        misspelled_dict[word]['originals'].append(word)
            # Calculate total characters, number of rows, max and min length for the specified column
            if column_name in row:
                length = len(str(row[column_name]))  # Convert to string before calculating length
                total_length.append(length)
                total_characters += length
                num_rows += 1
                if length > max_length:
                    max_length = length
                if length < min_length:
                    min_length = length
else:
    df = pd.read_excel(file_path)
    data = df.to_dict(orient='records')
    for row in data:
        cleaned_row = {key: remove_html_tags(str(value)) for key, value in row.items()}
        cleaned_row = {key: contractions.fix(value) for key, value in cleaned_row.items()}
        cleaned_row = {key: replace_underscores(value) for key, value in cleaned_row.items()}
        if replace_acronyms:
            cleaned_row = {key: replace_acronyms(value, acronyms) for key, value in cleaned_row.items()}
        for key, cell in cleaned_row.items():
            if cell.startswith('{"value":"- '):
                cell = cell.replace('{"value":"- ', '')
            if cell.endswith('}'):
                cell = cell[:-1]
            cleaned_row[key] = cell
            if fix_misspellings:
                misspelled_words = get_misspelled_words(cell)
                for word in misspelled_words:
                    if word.lower() in reviewed_words:
                        continue
                    corrected_word = word  # Placeholder for actual correction logic
                    misspelled_counter.update([word])
                    misspelled_dict[word]['corrected'] = corrected_word
                    misspelled_dict[word]['count'] += 1
                    misspelled_dict[word]['originals'].append(word)
        # Calculate total characters, number of rows, max and min length for the specified column
        if column_name in row:
            length = len(str(row[column_name]))  # Convert to string before calculating length
            total_length.append(length) # create a list to store length of each row
            total_characters += length
            num_rows += 1
            if length > max_length:
                max_length = length
            if length < min_length:
                min_length = length

# Calculate and print the average, max, and min character length
if num_rows > 0:
    average_length = total_characters / num_rows
    print(f"Average character length of column '{column_name}': {average_length:.2f}")
    print(f"Maximum character length of column '{column_name}': {max_length}")
    print(f"Minimum character length of column '{column_name}': {min_length}")
# Create a distribution chart for test case character length
    #print(total_length)
    s = pd.Series(total_length)
    mean = s.mean()
    std = s.std()
    plt.figure(figsize=(8,5))
    plt.hist(s,bins=40,density=True,alpha=0.4,edgecolor='none',label='Histogram')
    s.plot(kind='kde',linewidth=2,label='KDE Curve')
    plt.axvline(mean,color='red',linestyle='--',label=f'Mean = {mean:.2f}')
    plt.axvline(mean+std,color='green',linestyle=':',label=f'+1 SD = {mean+std:.2f}')
    plt.axvline(mean-std,color='green',linestyle=':',label=f'-1 SD = {mean-std:.2f}')
    plt.xlim(0,s.max()+100)
    plt.xlabel('Character Count')
    plt.ylabel('Density')
    plt.legend()
    plt.show()
else:
    print(f"Column '{column_name}' not found in the input file.")


# Create an Excel file for reviewing misspelled words if misspelling conversion is not skipped
if fix_misspellings:
    # Remove reviewed words from misspelled_dict
    for word in list(misspelled_dict.keys()):
        if word.lower() in reviewed_words:
            del misspelled_dict[word]
    create_review_excel(misspelled_dict, misspelled_excel_file_path)

    # Inform the user to review the Excel file
    messagebox.showinfo("Review Misspelled Words", f"Please review and correct the misspelled words in the Excel file: {misspelled_excel_file_path}")

    # Wait for the user to review and correct the Excel file
    messagebox.showinfo("Waiting", "Press OK after you have reviewed and corrected the Excel file.")

    # Read corrections from the Excel file
    corrections = read_corrections_from_excel(misspelled_excel_file_path)

    # Update the data with the corrected words
    for row in data:
        for key, value in row.items():
            words = str(value).split()
            corrected_words = [corrections.get(word, word) for word in words]
            row[key] = ' '.join(corrected_words)

# Write the data to a Markdown file
with open(md_file_path, 'w', encoding='utf-8') as md_file:
    for row in data:
        for key, value in row.items():
            md_file.write(f"**{key}**: {value}\n\n")

# Inform the user that the words have been corrected
messagebox.showinfo("Words Corrected", "The misspelled words have been corrected and the Markdown file has been saved.")

# End the timer and print the elapsed time
end_time = time.time()
elapsed_time = end_time - start_time
print(f"Elapsed time: {elapsed_time} seconds")

