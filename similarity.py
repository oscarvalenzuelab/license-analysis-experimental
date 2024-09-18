import requests
from difflib import SequenceMatcher
import re
import os
from collections import Counter

# SPDX license list text file URL template
spdx_text_url_template = "https://raw.githubusercontent.com/spdx/license-list-data/master/text/{}.txt"

# Directory to store downloaded licenses locally
license_dir = "licenses_texts"
os.makedirs(license_dir, exist_ok=True)

# Function to fetch or load license text (download if not already stored locally)
def fetch_or_load_license_text(license_id):
    license_file_path = os.path.join(license_dir, f"{license_id}.txt")

    # Check if the license text is already stored locally
    if os.path.exists(license_file_path):
        with open(license_file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()

    # If not stored locally, fetch it from the SPDX GitHub repo
    url = spdx_text_url_template.format(license_id)
    try:
        response = requests.get(url)
        if response.status_code == 200:
            license_text = response.text.strip()

            # Save the downloaded text locally
            with open(license_file_path, 'w', encoding='utf-8') as f:
                f.write(license_text)

            return license_text
        else:
            return ""
    except requests.RequestException as e:
        return ""

# Function to clean and tokenize text (remove punctuation, split words, lowercased)
def clean_and_tokenize(text):
    # Remove punctuation and convert to lower case
    cleaned = re.sub(r'[^\w\s]', '', text.lower())
    return cleaned.split()

# Function to identify common and different words in license group
def identify_similar_and_different_words(licenses, group_licenses):
    group_texts = {}
    word_counts = Counter()

    # Fetch and tokenize the text for each license in the group
    for license_id in group_licenses:
        license_text = fetch_or_load_license_text(license_id)
        if license_text:
            tokenized_text = clean_and_tokenize(license_text)
            group_texts[license_id] = tokenized_text
            word_counts.update(set(tokenized_text))  # Count unique words

    # Identify common and different words
    common_words = [word for word, count in word_counts.items() if count == len(group_licenses)]
    unique_words = {license_id: [] for license_id in group_licenses}

    # Identify unique words for each license
    for license_id, tokenized_text in group_texts.items():
        unique_words[license_id] = [word for word in tokenized_text if word not in common_words]

    return common_words, unique_words

# SPDX license list text file URL template
spdx_url = 'https://raw.githubusercontent.com/spdx/license-list-data/master/json/licenses.json'
response = requests.get(spdx_url)
spdx_data = response.json()

# Function to extract the part of the name before the first hyphen
def extract_prefix(name):
    prefix = name.split('-')[0]  # Take everything before the first hyphen
    return prefix

# Function to clean the group name by removing numbers and making it human-readable
def clean_group_name(prefix):
    cleaned = re.sub(r'[0-9]+', '', prefix).strip('- ')
    return cleaned + "-Like"

# Function to group licenses by the prefix of their SPDX IDs
def group_licenses_by_prefix(licenses):
    groups = {}
    processed = set()  # To track licenses that have already been grouped

    for license_id in licenses.keys():
        if license_id in processed:
            continue

        # Extract the prefix (part of the name before the first hyphen or the whole name if no hyphen)
        prefix = extract_prefix(license_id)
        
        # Initialize the group with the current license
        current_group = [license_id]
        processed.add(license_id)

        # Find all other licenses that share the same prefix
        for other_license_id in licenses.keys():
            if other_license_id == license_id or other_license_id in processed:
                continue

            other_prefix = extract_prefix(other_license_id)

            if prefix == other_prefix:
                current_group.append(other_license_id)
                processed.add(other_license_id)

        # Clean the group name
        clean_name = clean_group_name(prefix)

        # Store the group if it has more than one license
        if len(current_group) > 1:
            groups[clean_name] = current_group

    return groups

# Extract license IDs from the SPDX data
licenses = {license['licenseId']: license['name'] for license in spdx_data['licenses']}

# Group licenses by prefix (before the first hyphen or whole string if no hyphen)
print("Grouping licenses by prefix...")  # Debug message
license_groups = group_licenses_by_prefix(licenses)

# Output the grouped licenses and identify common/different words
print("Grouped licenses and identified differences:")
for group_name, group_licenses in license_groups.items():
    print(f"Group: {group_name}")
    common_words, unique_words = identify_similar_and_different_words(licenses, group_licenses)

    # Print common words for the group
    print(f"  Common words across all licenses: {', '.join(common_words)}")

    # Print unique words for each license
    for license_id in group_licenses:
        print(f"  Unique words for {license_id}: {', '.join(unique_words[license_id])}")
