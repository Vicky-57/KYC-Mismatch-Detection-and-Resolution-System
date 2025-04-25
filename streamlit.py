import streamlit as st
import pandas as pd
import numpy as np
import re
import datetime
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import json
import dateutil.parser
import string

class KYCMatcher:
    def __init__(self):
        # Common abbreviations for addresses
        self.address_abbreviations = {
            'st': 'street',
            'rd': 'road',
            'blvd': 'boulevard',
            'ave': 'avenue',
            'apt': 'apartment',
            'blk': 'block',
            'ngr': 'nagar',
            'sec': 'sector',
            'fl': 'floor',
            'apts': 'apartments',
            # India-specific state abbreviations
            'ka': 'karnataka',
            'mh': 'maharashtra',
            'up': 'uttar pradesh',
            'ap': 'andhra pradesh',
            'tn': 'tamil nadu',
            'dl': 'delhi',
            'wb': 'west bengal',
            'gj': 'gujarat',
            'rj': 'rajasthan',
            'mp': 'madhya pradesh',
            # City abbreviations
            'blr': 'bangalore',
            'bang': 'bangalore',
            'hyd': 'hyderabad',
            'mum': 'mumbai',
            'del': 'delhi',
            'kol': 'kolkata',
            'chn': 'chennai',
        }
        
        # Common company name transformations
        self.company_aliases = {
            'facebook': ['meta', 'facebook inc', 'meta platforms', 'meta platforms inc'],
            'google': ['alphabet', 'alphabet inc', 'google inc', 'google llc'],
            'infosys': ['infosys limited', 'infosys ltd', 'infosys technologies'],
            'tata': ['tcs', 'tata consultancy services', 'tata sons', 'tata group'],
            'microsoft': ['ms', 'microsoft corporation', 'msft'],
        }
        
        # Common salutations to remove
        self.salutations = ['mr', 'mrs', 'ms', 'miss', 'dr', 'prof', 'shri', 'smt']
        
        # Suffixes for companies
        self.company_suffixes = ['ltd', 'limited', 'inc', 'incorporated', 'llc', 'corp', 
                                'corporation', 'pvt', 'private', 'gmbh', 'co']

    def normalize_name(self, name):
        """Normalize the name by removing salutations, extra spaces, and standardizing case"""
        if not name:
            return ""
            
        # Convert to lowercase
        normalized = name.lower().strip()
        
        # Remove punctuation except periods in initials
        normalized = re.sub(r'[^\w\s.]', ' ', normalized)
        
        # Remove salutations
        words = normalized.split()
        if words and words[0].replace('.', '') in self.salutations:
            words = words[1:]
        normalized = ' '.join(words)
        
        # Clean up extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized

    def expand_initials(self, name):
        """Create potential variations where initials are expanded"""
        # This is a simplified version - a real implementation would use a name database
        return name

    def normalize_address(self, address):
        """Normalize the address by expanding abbreviations and standardizing format"""
        if not address:
            return ""
            
        # Convert to lowercase
        normalized = address.lower().strip()
        
        # Remove punctuation
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        
        # Expand abbreviations
        words = normalized.split()
        for i, word in enumerate(words):
            if word in self.address_abbreviations:
                words[i] = self.address_abbreviations[word]
        normalized = ' '.join(words)
        
        # Clean up extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized

    def normalize_company_name(self, name):
        """Normalize company names by removing legal suffixes and standardizing format"""
        if not name:
            return ""
            
        normalized = name.lower().strip()
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        
        # Remove common company suffixes
        words = normalized.split()
        filtered_words = [word for word in words if word not in self.company_suffixes]
        normalized = ' '.join(filtered_words)
        
        # Check for known company aliases
        for main_name, aliases in self.company_aliases.items():
            if normalized in aliases or normalized == main_name:
                return main_name
        
        return normalized.strip()

    def normalize_date(self, date_str):
        """Try to parse and normalize date in YYYY-MM-DD format"""
        if not date_str:
            return None
            
        try:
            # Try parsing the date
            parsed_date = dateutil.parser.parse(date_str)
            return parsed_date.strftime('%Y-%m-%d')
        except:
            # Return None if we can't parse it
            return None

    def get_name_similarity(self, name1, name2):
        """Calculate name similarity score with various metrics"""
        if not name1 or not name2:
            return 0
            
        # Normalize both names
        norm1 = self.normalize_name(name1)
        norm2 = self.normalize_name(name2)
        
        # Direct comparison
        if norm1 == norm2:
            return 100
        
        # Split names into parts
        name1_parts = norm1.split()
        name2_parts = norm2.split()
        
        # Handle swapped names (e.g., "Kumar Rajeev" vs "Rajeev Kumar")
        if set(name1_parts) == set(name2_parts):
            return 95
        
        # Check for missing middle name more accurately
        if len(name1_parts) > len(name2_parts) or len(name2_parts) > len(name1_parts):
            # Check if last names match
            if name1_parts[-1] == name2_parts[-1]:
                # Check if first names match
                if name1_parts[0] == name2_parts[0]:
                    # It's likely a middle name difference
                    return 80
                
        # Check if one name is contained within the other
        if norm1 in norm2 or norm2 in norm1:
            return 85
        
        # Initial vs full name (e.g., "S. Ramesh" vs "Subramaniam Ramesh")
        # Extract last names
        name1_last = name1_parts[-1] if name1_parts else ""
        name2_last = name2_parts[-1] if name2_parts else ""
        
        # If last names match and one name has initials
        if name1_last == name2_last and ('.' in norm1 or '.' in norm2):
            # Check if initials match first letters
            has_matching_initials = True
            if '.' in norm1:
                initials = [p.strip('.') for p in norm1.split() if '.' in p]
                other_name_parts = [p[0].lower() for p in norm2.split() if p != name2_last]
                if not all(i in other_name_parts for i in initials):
                    has_matching_initials = False
            elif '.' in norm2:
                initials = [p.strip('.') for p in norm2.split() if '.' in p]
                other_name_parts = [p[0].lower() for p in norm1.split() if p != name1_last]
                if not all(i in other_name_parts for i in initials):
                    has_matching_initials = False
                    
            if has_matching_initials:
                return 80
        
        # Use fuzzy matching as a fallback
        token_sort_ratio = fuzz.token_sort_ratio(norm1, norm2)
        token_set_ratio = fuzz.token_set_ratio(norm1, norm2)
        
        return max(token_sort_ratio, token_set_ratio)

    def get_address_similarity(self, addr1, addr2):
        """Calculate address similarity with component-wise comparison"""
        if not addr1 or not addr2:
            return 0
            
        # Normalize both addresses
        norm1 = self.normalize_address(addr1)
        norm2 = self.normalize_address(addr2)
        
        # Direct comparison
        if norm1 == norm2:
            return 100
        
        # Count the number of abbreviations
        abbrev_count = 0
        for word in self.address_abbreviations:
            if word in addr1.lower() or word in addr2.lower():
                abbrev_count += 1
        
        # Extract potential postal codes
        postal_code1 = re.search(r'\b\d{5,6}\b', addr1)
        postal_code2 = re.search(r'\b\d{5,6}\b', addr2)
        
        postal_match = 0
        if postal_code1 and postal_code2:
            pc1 = postal_code1.group()
            pc2 = postal_code2.group()
            if pc1 == pc2:
                postal_match = 25
            elif abs(int(pc1) - int(pc2)) <= 5:  # Nearby postal codes
                postal_match = 15
        
        # Use fuzzy matching for the whole address
        token_sort_ratio = fuzz.token_sort_ratio(norm1, norm2)
        token_set_ratio = fuzz.token_set_ratio(norm1, norm2)
        
        base_score = max(token_sort_ratio, token_set_ratio)
        
        # Slightly reduce score based on abbreviation usage
        if abbrev_count > 0:
            base_score = max(base_score - (abbrev_count * 2), 0)
        
        # Boost score if postal codes match
        final_score = min(100, base_score + postal_match)
        
        return final_score

    def compare_dates(self, date1, date2):
        """Compare two dates and return similarity score"""
        norm_date1 = self.normalize_date(date1)
        norm_date2 = self.normalize_date(date2)
        
        if not norm_date1 or not norm_date2:
            return 0
            
        if norm_date1 == norm_date2:
            return 100
            
        # Check for potential date format swaps (MM/DD vs DD/MM)
        try:
            d1 = datetime.datetime.strptime(norm_date1, '%Y-%m-%d')
            d2 = datetime.datetime.strptime(norm_date2, '%Y-%m-%d')
            
            # Check if month and day might be swapped
            swapped_date2 = f"{d2.year}-{d2.day:02d}-{d2.month:02d}"
            if norm_date1 == swapped_date2:
                return 50  # Potential format confusion
                
            # Check for year difference only
            if d1.month == d2.month and d1.day == d2.day:
                return 50
                
            # Check for close dates (within 5 days)
            delta = abs((d1 - d2).days)
            if delta <= 5:
                return 80
                
        except:
            pass
            
        return 0

    def compare_documents(self, doc_a, doc_b):
        """Compare two documents and return a detailed comparison with confidence scores"""
        results = {}
        explanations = []
        caution_notes = []
        
        # Name comparison
        name_similarity = self.get_name_similarity(doc_a.get('Name', ''), doc_b.get('Name', ''))
        results['name_similarity'] = name_similarity
        
        if name_similarity >= 95:
            explanations.append(f"Names match with high confidence ({name_similarity}%)")
        elif name_similarity >= 80:
            explanations.append(f"Names are likely to match ({name_similarity}%)")
            
            # Check for missing middle name more explicitly
            name1_parts = self.normalize_name(doc_a.get('Name', '')).split()
            name2_parts = self.normalize_name(doc_b.get('Name', '')).split()
            
            if abs(len(name1_parts) - len(name2_parts)) > 0:
                caution_notes.append("Middle name discrepancy detected")
                
        elif name_similarity >= 60:
            explanations.append(f"Names have some similarity ({name_similarity}%)")
        else:
            explanations.append(f"Names differ significantly ({name_similarity}%)")
        
        # Address comparison
        address_similarity = self.get_address_similarity(doc_a.get('Address', ''), doc_b.get('Address', ''))
        results['address_similarity'] = address_similarity
        
        if address_similarity >= 95:
            explanations.append(f"Addresses match with high confidence ({address_similarity}%)")
        elif address_similarity >= 80:
            explanations.append(f"Addresses are likely to match ({address_similarity}%)")
        elif address_similarity >= 60:
            explanations.append(f"Addresses have some similarity ({address_similarity}%)")
        else:
            explanations.append(f"Addresses differ significantly ({address_similarity}%)")
        
        # DOB comparison
        dob_similarity = self.compare_dates(doc_a.get('DOB', ''), doc_b.get('DOB', ''))
        results['dob_similarity'] = dob_similarity
        
        if dob_similarity == 100:
            explanations.append("DOB matches exactly")
        elif dob_similarity == 50:
            explanations.append("Possible DOB format confusion (MM/DD vs DD/MM)")
            caution_notes.append("DOB ambiguity: possible MM/DD vs DD/MM format confusion")
        elif dob_similarity > 0:
            explanations.append(f"DOB has some similarity ({dob_similarity}%)")
        else:
            explanations.append("DOB does not match")
        
        # Gender comparison
        gender_match = 100 if doc_a.get('Gender', '').lower() == doc_b.get('Gender', '').lower() else 0
        results['gender_match'] = gender_match
        
        if gender_match == 100:
            explanations.append("Gender matches")
        else:
            explanations.append("Gender does not match")
        
        # Calculate overall confidence score with weighted factors
        # Names and addresses are most important, followed by DOB and gender
        overall_confidence = (
            name_similarity * 0.4 +
            address_similarity * 0.3 +
            dob_similarity * 0.2 +
            gender_match * 0.1
        )
        
        # Adjust confidence based on critical mismatches
        if name_similarity < 50 or address_similarity < 40:
            overall_confidence *= 0.7  # Major penalty for significant mismatches
        
        if gender_match == 0 and doc_a.get('Gender') and doc_b.get('Gender'):
            overall_confidence *= 0.8  # Penalty for gender mismatch
            
        # Apply stronger penalty for DOB issues as this is critical for identification
        if dob_similarity == 50:  # This is the MM/DD vs DD/MM case
            overall_confidence *= 0.7  # Stronger penalty for date format ambiguity
            
        if dob_similarity == 0 and doc_a.get('DOB') and doc_b.get('DOB'):
            overall_confidence *= 0.7  # Stronger penalty for complete DOB mismatch
        
        # Special handling for Case 12 type scenarios (missing middle name + DOB format issue)
        if caution_notes and dob_similarity == 50:
            overall_confidence = min(overall_confidence, 70)  # Cap at medium confidence
                
        # Determine match category
        match_category = "No match"
        if overall_confidence >= 90:
            match_category = "High confidence match"
        elif overall_confidence >= 70:
            match_category = "Medium-to-high confidence match"
        elif overall_confidence >= 50:
            if caution_notes:
                match_category = "Medium confidence match with caution"
            else:
                match_category = "Medium confidence match"
        elif overall_confidence >= 30:
            match_category = "Low-to-medium confidence match"
        
        # Add caution notes to explanations if present
        if caution_notes:
            explanations.append("CAUTION: " + "; ".join(caution_notes))
        
        return {
            'detailed_scores': results,
            'overall_confidence': round(overall_confidence, 2),
            'match_category': match_category,
            'explanations': explanations
        }

# Streamlit app
def main():
    st.set_page_config(page_title="KYC Mismatch Detection System", page_icon="🔍", layout="wide")
    
    st.title("KYC Mismatch Detection and Resolution System")
    st.write("""
    This application detects and resolves mismatches in Know Your Customer (KYC) documents,
    particularly focusing on name and address variations. It provides confidence scores and explanations
    for why documents are considered matching or non-matching.
    """)
    
    matcher = KYCMatcher()
    
    st.header("Document Comparison")
    
    input_method = st.radio("Choose input method:", ["Form Input", "JSON Input", "Sample Cases"])
    
    if input_method == "Form Input":
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Document A")
            name_a = st.text_input("Name (Doc A):", key="name_a")
            address_a = st.text_area("Address (Doc A):", key="address_a")
            dob_a = st.text_input("Date of Birth (Doc A):", key="dob_a", 
                                  help="Format: DD/MM/YYYY or MM/DD/YYYY or YYYY-MM-DD")
            gender_a = st.selectbox("Gender (Doc A):", ["", "Male", "Female", "Other"], key="gender_a")
            
        with col2:
            st.subheader("Document B")
            name_b = st.text_input("Name (Doc B):", key="name_b")
            address_b = st.text_area("Address (Doc B):", key="address_b")
            dob_b = st.text_input("Date of Birth (Doc B):", key="dob_b",
                                 help="Format: DD/MM/YYYY or MM/DD/YYYY or YYYY-MM-DD")
            gender_b = st.selectbox("Gender (Doc B):", ["", "Male", "Female", "Other"], key="gender_b")
        
        doc_a = {
            "Name": name_a,
            "Address": address_a,
            "DOB": dob_a,
            "Gender": gender_a
        }
        
        doc_b = {
            "Name": name_b,
            "Address": address_b,
            "DOB": dob_b,
            "Gender": gender_b
        }
        
    elif input_method == "JSON Input":
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Document A (JSON)")
            json_a = st.text_area("Paste JSON for Document A:", 
                                height=200,
                                key="json_a",
                                help="Format: {\"Name\": \"John Doe\", \"Address\": \"123 Main St\", \"DOB\": \"01/01/1990\", \"Gender\": \"Male\"}")
            
        with col2:
            st.subheader("Document B (JSON)")
            json_b = st.text_area("Paste JSON for Document B:", 
                                height=200,
                                key="json_b",
                                help="Format: {\"Name\": \"J. Doe\", \"Address\": \"123 Main Street\", \"DOB\": \"1990-01-01\", \"Gender\": \"Male\"}")
        
        try:
            doc_a = json.loads(json_a) if json_a.strip() else {}
        except:
            st.error("Invalid JSON format for Document A")
            doc_a = {}
            
        try:
            doc_b = json.loads(json_b) if json_b.strip() else {}
        except:
            st.error("Invalid JSON format for Document B")
            doc_b = {}
            
    else:  # Sample cases
        sample_cases = {
            "Case 1: Middle Name Variation": {
                "doc_a": {"Name": "Anita Sharma", "DOB": "15/08/1985", "Gender": "Female", "Address": ""},
                "doc_b": {"Name": "Anita R. Sharma", "DOB": "15/08/1985", "Gender": "Female", "Address": ""}
            },
            "Case 2: Swapped Name Order": {
                "doc_a": {"Name": "Kumar Rajeev", "DOB": "10/05/1978", "Gender": "Male", "Address": ""},
                "doc_b": {"Name": "Rajeev Kumar", "DOB": "10/05/1978", "Gender": "Male", "Address": ""}
            },
            "Case 3: Address Abbreviation": {
                "doc_a": {"Name": "", "DOB": "", "Gender": "", "Address": "123 MG Road, Bangalore, Karnataka"},
                "doc_b": {"Name": "", "DOB": "", "Gender": "", "Address": "123 Mahatma Gandhi Rd., Blr, KA"}
            },
            "Case 11: Complex Case - Multiple Issues": {
                "doc_a": {
                    "Name": "Dr. A. K. Mehta",
                    "Address": "501 Ashirwad Apartments, Vashi, Navi Mumbai, Maharashtra, 400703",
                    "DOB": "02/03/1970",
                    "Gender": "Male"
                },
                "doc_b": {
                    "Name": "Ashok Kumar Mehta",
                    "Address": "Ashirwad Apts, Sec-17, Vashi, Mumbai, MH, 400703",
                    "DOB": "03-02-1970",
                    "Gender": "Male"
                }
            },
            "Case 12: Cross-Validation with Conflicting Data": {
                "doc_a": {
                    "Name": "Sunil Kumar Sharma",
                    "Address": "Block 3, Shakti Nagar, Delhi, 110007",
                    "DOB": "05/12/1990",
                    "Gender": "Male"
                },
                "doc_b": {
                    "Name": "Sunil Sharma",
                    "Address": "Blk-III, Shakti Ngr, New Delhi, 110007",
                    "DOB": "12/05/1990",
                    "Gender": "Male"
                }
            }
        }
        
        selected_case = st.selectbox("Select a sample case:", list(sample_cases.keys()))
        selected_data = sample_cases[selected_case]
        
        doc_a = selected_data["doc_a"]
        doc_b = selected_data["doc_b"]
        
        # Display the selected case details
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Document A")
            st.json(doc_a)
        with col2:
            st.subheader("Document B")
            st.json(doc_b)
    
    # Process comparison when button is clicked
    if st.button("Compare Documents"):
        if (doc_a.get("Name") or doc_a.get("Address")) and (doc_b.get("Name") or doc_b.get("Address")):
            results = matcher.compare_documents(doc_a, doc_b)
            
            st.header("Comparison Results")
            
            # Overall confidence with visual indicator
            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric("Overall Confidence Score", f"{results['overall_confidence']}%")
            with col2:
                st.write(f"**Match Category:** {results['match_category']}")
            
            # Progress bar for visual representation
            confidence_color = "green" if results['overall_confidence'] >= 70 else "orange" if results['overall_confidence'] >= 50 else "red"
            st.progress(results['overall_confidence']/100)
            
            # Detailed scores in expander
            with st.expander("View Detailed Scores"):
                scores = results['detailed_scores']
                score_df = pd.DataFrame({
                    "Metric": ["Name Similarity", "Address Similarity", "Date of Birth Similarity", "Gender Match"],
                    "Score": [
                        f"{scores.get('name_similarity', 0)}%", 
                        f"{scores.get('address_similarity', 0)}%",
                        f"{scores.get('dob_similarity', 0)}%",
                        f"{scores.get('gender_match', 0)}%"
                    ]
                })
                st.table(score_df)
            
            # Explanations
            st.subheader("Analysis")
            for explanation in results['explanations']:
                st.write(f"• {explanation}")
                
            # Recommendations based on confidence
            # Recommendations based on confidence
            st.subheader("Recommendation")
            if "caution" in results['match_category'].lower():
                st.warning(f"⚠️ {results['match_category']}. Manual review recommended.")
            elif results['overall_confidence'] >= 90:
                st.success("✅ Documents likely belong to the same entity. Automated processing can proceed.")
            elif results['overall_confidence'] >= 70:
                st.info("ℹ️ Documents likely match but with minor discrepancies. Consider secondary verification.")
            elif results['overall_confidence'] >= 50:
                st.warning("⚠️ Some significant differences found. Manual review recommended.")
            else:
                st.error("❌ Documents likely refer to different entities or contain major errors. Manual review required.")
                            
        else:
            st.error("Please enter at least name or address information for both documents.")

if __name__ == "__main__":
    main()