import streamlit as st
import re
import math

# --- Configuration and Styling ---

st.set_page_config(layout="wide", page_title="Advanced Content Quality Analyzer")

# Custom CSS for better styling and readability
st.markdown("""
<style>
    /* Main Streamlit container width */
    .reportview-container .main {
        padding-top: 2rem;
    }
    /* Header styling */
    h1 {
        font-size: 2.5rem;
        color: #1A73E8; /* Google Blue */
        border-bottom: 2px solid #D9D9D9;
        padding-bottom: 5px;
        margin-bottom: 10px;
    }
    /* Section headers */
    h3 {
        color: #3C4043;
        font-weight: 600;
        margin-top: 1.5rem;
    }
    /* Score card styling */
    .score-card {
        border: 1px solid #E8EAED;
        padding: 10px;
        border-radius: 8px;
        background-color: #F8F9FA;
        margin-bottom: 10px;
        text-align: center;
    }
    .score-value {
        font-size: 2.5rem;
        font-weight: 700;
    }
    .score-label {
        font-size: 0.9rem;
        color: #5F6368;
    }
    /* Priority list styling */
    .priority-item {
        background-color: #FCE8E6; /* Light red for urgency */
        border-left: 5px solid #EA4335;
        padding: 8px;
        margin-bottom: 5px;
        border-radius: 4px;
        font-weight: 500;
    }
    /* Finding boxes */
    .positive-cue {
        color: #0D723C;
        font-weight: 500;
    }
    .missing-signal {
        color: #A60000;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)


# --- Analysis Constants (Derived from Google Ranking Systems Research) ---

# Section 1: E-E-A-T (Experience, Expertise, Authority, Trust) & Utility (Max 40 Pts)
EEAT_MAX_SCORE = 40
EEAT_TRUST_KEYWORDS = [
    r"author:", r"cited", r"sources", r"data suggests", r"peer-reviewed", r"methodology", r"disclosure"
]
EEAT_EXPERIENCE_KEYWORDS = [
    r"i found that", r"after using", r"i discovered", r"original analysis", r"hands-on", r"i tested", r"first-hand"
]
UTILITY_KEYWORDS = [
    r"step-by-step", r"how to", r"tutorial", r"actionable", r"comprehensive", r"guide", r"in-depth"
]
# Weighting: 20 pts for EEAT cues, 20 pts for Utility/Depth/Intent

# Section 2: Keyword Relevance & Placement (Max 20 Pts)
KEYWORD_MAX_SCORE = 20
KEYWORD_DENSITY_TARGET = (0.5, 2.5) # Target percentage range
KEYWORD_PLACEMENT_LENGTH = 150 # Check for keyword presence in the first 150 characters

# Section 3: Integrity & Compliance (SpamBrain / Helpful Content) (Max 20 Pts)
INTEGRITY_MAX_SCORE = 20
SPAMMY_KEYWORDS = [
    r"buy now", r"click here", r"unbeatable deal", r"limited time offer", r"guaranteed", r"cash back", r"instant access"
]
REPETITIVE_PHRASES = [
    r"very good article", r"is a great product", r"fantastic opportunity", r"the best thing" # Generic, formulaic phrases
]
AI_DISCLOSURE_KEYWORDS = [
    r"ai-generated", r"ai writer", r"automated content", r"llm", r"model-assisted"
]
MIN_WORD_COUNT = 300 # Heuristic for thin content penalty

# Section 4: Technical, Freshness & Link Strategy (Page Experience / Site Quality) (Max 20 Pts)
TECH_MAX_SCORE = 20
FRESHNESS_KEYWORDS = [r"updated:", r"current as of", r"latest research", r"recent changes"]
LINK_PLACEHOLDERS = [r"\[internal link", r"\[external link"]
# Usability Check: Short paragraphs (3-7 sentences recommended for mobile UX)

# --- Core Analysis Functions ---

def calculate_reading_ease(text):
    """Calculates a simplified Flesch Kincaid Reading Ease score (0-100)."""
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    words = re.findall(r'\b\w+\b', text)
    syllables = sum(len(re.findall(r'[aeiouy]+', word.lower())) for word in words)

    if not words or not sentences:
        return 100, "N/A"

    ASL = len(words) / len(sentences) # Average Sentence Length
    ASW = syllables / len(words) # Average Syllables per Word

    # Flesch Reading Ease Formula (Simplified)
    score = 206.835 - 1.015 * ASL - 84.6 * ASW

    grade = "Complex (Post-Graduate)"
    if score >= 60:
        grade = "Fairly Easy (8th-9th Grade)"
    if score >= 70:
        grade = "Easy (6th-7th Grade)"
    if score >= 80:
        grade = "Very Easy (5th Grade)"

    return max(0, min(100, score)), grade

def analyze_content(content, target_keyword):
    """Performs the full analysis based on the ranking system mandates."""
    findings = {
        'priority_actions': [],
        'eeat': {'score': 0, 'cues': [], 'missing': [], 'max': EEAT_MAX_SCORE},
        'keyword': {'score': 0, 'cues': [], 'missing': [], 'max': KEYWORD_MAX_SCORE},
        'integrity': {'score': 0, 'cues': [], 'missing': [], 'max': INTEGRITY_MAX_SCORE},
        'technical': {'score': 0, 'cues': [], 'missing': [], 'max': TECH_MAX_SCORE},
    }
    total_score = 0
    clean_content = content.lower()
    word_count = len(re.findall(r'\b\w+\b', clean_content))

    # --- Content Segmentation ---
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    intro_content = paragraphs[0].lower() if paragraphs else ""
    conclusion_content = paragraphs[-1].lower() if len(paragraphs) > 1 else ""

    # --- Helper: Add Missing Signal ---
    def add_missing(section_key, signal, priority=False):
        findings[section_key]['missing'].append(signal)
        if priority:
            findings['priority_actions'].append(signal)

    # --- 1. E-E-A-T & Utility Analysis (Max 40 Pts) ---
    score_eeat = 0

    # A. Experience & Trust (Weighted 25 pts)
    eeat_cues = 0
    for keyword in EEAT_EXPERIENCE_KEYWORDS:
        if re.search(keyword, clean_content):
            findings['eeat']['cues'].append(f"Found Experience cue: '{keyword.strip('r\\').replace('r\\', '')}'")
            eeat_cues += 1
    for keyword in EEAT_TRUST_KEYWORDS:
        if re.search(keyword, clean_content):
            findings['eeat']['cues'].append(f"Found Trust cue: '{keyword.strip('r\\').replace('r\\', '')}'")
            eeat_cues += 1

    if eeat_cues > 0:
        score_eeat += min(25, eeat_cues * 5)
    else:
        add_missing('eeat', "No clear **first-hand experience** or **trust signals** (e.g., 'I tested,' 'cited sources').", True)

    # B. Utility & Intent Fulfillment (Weighted 15 pts)
    utility_cues = 0
    for keyword in UTILITY_KEYWORDS:
        if re.search(keyword, clean_content):
            findings['eeat']['cues'].append(f"Found Utility cue: '{keyword.strip('r\\').replace('r\\', '')}'")
            utility_cues += 1

    # Check for Explicit Question-Answer Structure (Signals High Intent Fulfillment)
    if re.search(r'\?\s*\w{2,}:', content): # Simple check for a question followed by a clear break/answer
        findings['eeat']['cues'].append("Found explicit **Question-Answer structure** (signals intent fulfillment).")
        score_eeat += 5
    else:
        add_missing('eeat', "Missing explicit **Question-Answer** sections for direct intent fulfillment.", False)

    # Check for Author/Persona
    if re.search(r'author:', clean_content) and re.search(r'(dr\.|ph\.d\.)', clean_content):
         findings['eeat']['cues'].append("Found explicit **Author/Expert Persona** (Dr., Ph.D. etc.).")
         score_eeat += 5
    elif re.search(r'author:', clean_content):
         findings['eeat']['cues'].append("Found clear **Author declaration**.")
         score_eeat += 2
    else:
        add_missing('eeat', "No visible **Author/Expert** declaration.", True)


    if utility_cues > 0:
        score_eeat += min(5, utility_cues * 2)

    if score_eeat == 0:
        add_missing('eeat', "Content appears low-effort or AI-generated without editorial oversight.", True)

    findings['eeat']['score'] = min(EEAT_MAX_SCORE, score_eeat)


    # --- 2. Keyword Relevance & Placement Analysis (Max 20 Pts) ---
    score_keyword = 0
    keyword_words = target_keyword.lower().split()
    keyword_mentions = len(re.findall(re.escape(target_keyword.lower()), clean_content))

    # A. Density (Weighted 10 pts)
    if word_count > 0:
        density = (keyword_mentions / word_count) * 100
        findings['keyword']['cues'].append(f"Keyword Density: {density:.2f}% ({keyword_mentions} mentions). Target is {KEYWORD_DENSITY_TARGET[0]:.2f}% - {KEYWORD_DENSITY_TARGET[1]:.2f}%.")
        if KEYWORD_DENSITY_TARGET[0] <= density <= KEYWORD_DENSITY_TARGET[1]:
            score_keyword += 10
        elif density < KEYWORD_DENSITY_TARGET[0]:
            add_missing('keyword', f"Keyword density is too low ({density:.2f}%). Need more mentions.", True)
            score_keyword += 5
        else:
            add_missing('keyword', f"Keyword density is too high ({density:.2f}%). Potential for keyword stuffing.", True)
            score_keyword += 2 # Heavy penalty for stuffing
    else:
        add_missing('keyword', "Content is empty or too short for density analysis.", True)

    # B. Placement (Weighted 10 pts)
    # Check Title (assumed to be H1/first line in markdown)
    title_match = re.search(r'^#\s*(.*)', content, re.MULTILINE | re.IGNORECASE)
    if title_match and target_keyword.lower() in title_match.group(1).lower():
        findings['keyword']['cues'].append("Keyword found in the **Title**.")
        score_keyword += 4
    else:
        add_missing('keyword', "Keyword missing from the **Title**.", True)

    # Check Introduction
    if target_keyword.lower() in intro_content[:KEYWORD_PLACEMENT_LENGTH]:
        findings['keyword']['cues'].append(f"Keyword found in the **Introduction** (first {KEYWORD_PLACEMENT_LENGTH} chars).")
        score_keyword += 4
    else:
        add_missing('keyword', "Keyword missing from the **first 150 characters** of the introduction.", True)

    # Check Conclusion
    if target_keyword.lower() in conclusion_content:
        findings['keyword']['cues'].append("Keyword found in the **Conclusion**.")
        score_keyword += 2
    else:
        add_missing('keyword', "Keyword missing from the **Conclusion**.", False)

    findings['keyword']['score'] = min(KEYWORD_MAX_SCORE, score_keyword)


    # --- 3. Integrity & Compliance (SpamBrain / Helpful Content) (Max 20 Pts) ---
    score_integrity = 20
    penalty_count = 0

    # A. Spammy Language Penalty
    spam_cues = 0
    for keyword in SPAMMY_KEYWORDS:
        if re.search(keyword, clean_content):
            findings['integrity']['cues'].append(f"Found Spam signal: '{keyword.strip('r\\')}'")
            spam_cues += 1
    if spam_cues > 0:
        score_integrity -= 5
        penalty_count += 1
        add_missing('integrity', f"Excessive commercial/spammy language detected ({spam_cues} cues).", True)
    else:
        findings['integrity']['cues'].append("Clean language: No excessive commercial/spammy cues found.")

    # B. Repetitive/Formulaic Penalty (Suggests low editorial effort/mass-produced)
    repetitive_cues = 0
    for phrase in REPETITIVE_PHRASES:
        if len(re.findall(phrase, clean_content)) > 1:
            findings['integrity']['cues'].append(f"Found Repetitive/Formulaic cue: '{phrase.strip('r\\')}' used multiple times.")
            repetitive_cues += 1
    if repetitive_cues > 0:
        score_integrity -= 5
        penalty_count += 1
        add_missing('integrity', f"Formulaic/Repetitive phrases detected ({repetitive_cues} cues).", True)
    else:
        findings['integrity']['cues'].append("Low repetition: Content appears editorially distinct and not formulaic.")

    # C. AI Transparency Penalty (Applies if penalties already incurred)
    ai_disclosed = any(re.search(k, clean_content) for k in AI_DISCLOSURE_KEYWORDS)

    if not ai_disclosed and score_integrity < 20: # Penalize undisclosed AI use ONLY if other spam/low-quality signals exist
        score_integrity -= 5
        penalty_count += 1
        add_missing('integrity', "**AI Transparency Missing:** No AI disclosure found, penalizing for lack of transparency combined with quality issues.", True)
    elif ai_disclosed:
        findings['integrity']['cues'].append("AI Use is **Disclosed** (Good transparency signal).")
    else:
        findings['integrity']['cues'].append("AI Use is either not present or is undisclosed but currently non-penalizing.")

    # D. Thin Content Penalty
    if word_count < MIN_WORD_COUNT:
        score_integrity -= 5
        penalty_count += 1
        add_missing('integrity', f"Content is too thin (Word Count: {word_count}). Target minimum is {MIN_WORD_COUNT} words.", True)

    # E. Zero Score Rule (Mandatory Compliance Failure)
    if penalty_count >= 2:
        findings['integrity']['cues'].append("TOTAL FAILURE: Multiple severe compliance issues detected. Score is reset to **0/20** per strict compliance policy.")
        score_integrity = 0
    elif score_integrity < 0:
        score_integrity = 0

    findings['integrity']['score'] = min(INTEGRITY_MAX_SCORE, score_integrity)

    # --- 4. Technical, Freshness & Link Strategy (Max 20 Pts) ---
    score_tech = 0

    # A. Freshness Signals (Weighted 5 pts)
    freshness_cues = sum(1 for keyword in FRESHNESS_KEYWORDS if re.search(keyword, clean_content))
    if freshness_cues > 0:
        findings['technical']['cues'].append(f"Found Freshness Cues ({freshness_cues}).")
        score_tech += min(5, freshness_cues * 3)
    else:
        add_missing('technical', "No clear **'Updated:'** date or **Freshness** signals.", True)

    # B. Internal & External Link Strategy (Weighted 5 pts)
    internal_links = len(re.findall(r'\[internal link', clean_content))
    external_links = len(re.findall(r'\[external link', clean_content))

    if internal_links >= 2:
        findings['technical']['cues'].append(f"Found {internal_links} **Internal Link** placeholders (Signals good site structure).")
        score_tech += 3
    else:
        add_missing('technical', "Need more **[Internal Link]** placeholders (Target >= 2).", False)

    if external_links >= 1:
        findings['technical']['cues'].append(f"Found {external_links} **External Link** placeholders (Signals good sourcing/Trust).")
        score_tech += 2
    else:
        add_missing('technical', "Missing **[External Link]** placeholders (Target >= 1).", True)

    # C. Usability & Structure (Weighted 10 pts)
    # Check for Headings (assuming use of ## and ###)
    h2_count = len(re.findall(r'^##\s', content, re.MULTILINE))
    h3_count = len(re.findall(r'^###\s', content, re.MULTILINE))

    if h2_count >= 3:
        findings['technical']['cues'].append(f"Found {h2_count} primary section headings (**##**).")
        score_tech += 5
    else:
        add_missing('technical', "Need more primary section headings (**##**); content lacks clear hierarchy.", True)

    # Paragraph Length Check (Heuristic for mobile usability/readability)
    long_paragraphs = sum(1 for p in paragraphs if len(re.findall(r'[.!?]+', p)) > 7)
    if long_paragraphs == 0 and len(paragraphs) > 5:
        findings['technical']['cues'].append("Paragraphs are short and digestible (good mobile UX).")
        score_tech += 5
    elif long_paragraphs > 0:
        add_missing('technical', f"Found {long_paragraphs} long paragraphs (potential mobile/readability issue).", True)
        score_tech += 2

    findings['technical']['score'] = min(TECH_MAX_SCORE, score_tech)

    # --- Final Score Aggregation ---
    total_score = findings['eeat']['score'] + findings['keyword']['score'] + \
                  findings['integrity']['score'] + findings['technical']['score']

    return findings, total_score, word_count, paragraphs


# --- Streamlit UI Layout ---

def main_app():
    """Main function to run the Streamlit application."""
    st.title("Google Ranking Systems Content Analyzer")
    st.markdown("---")

    # Define the template/placeholder content
    placeholder_content = """
# The Essential Guide to Ranking Systems (Updated: 2024)
Author: Dr. Jenna Smith, Ph.D. in Computer Science

### Understanding the Core Systems
I found that after rigorous testing on over 100 pages, the single most critical factor is the application of the Experience (E) component of E-E-A-T. In my experience, content must demonstrate original insights.

Why is this level of detail important? The reason is that Google’s Helpful Content System penalizes content that lacks original value. [Internal Link]

### Building Trust and Authority
The Trustworthiness (T) mandate requires clear sourcing. We have cited 12 different external sources to back up our claims. This provides strong confidence to the reader and signals high Expertise (E) to the system.

[External Link]

This article is current as of 2024. [Internal Link]
"""

    # --- Input Section ---
    col_input, col_preview = st.columns([1, 1])

    with col_input:
        st.subheader("1. Paste Your Content Draft (Markdown)")
        target_keyword = st.text_input("Target Keyword/Phrase (Required)", "Google Ranking Systems")
        
        # Text area with explicit instructions for markdown structure
        content = st.text_area(
            "Content Draft",
            placeholder_content,
            height=400,
            help="Paste your full content draft. For the best analysis, include Markdown cues like **## Headings**, **[Link Text]** placeholders, and the **'Updated:'** tag for Freshness checks.",
        )
        analyze_button = st.button("Run Comprehensive Analysis")

    with col_preview:
        st.subheader("2. Real-Time Markdown Preview")
        st.markdown(content, unsafe_allow_html=True)


    st.markdown("---")

    # --- Analysis Output Section ---
    if analyze_button and content and target_keyword:
        findings, total_score, word_count, paragraphs = analyze_content(content, target_keyword)
        score_percent = (total_score / 100) * 100
        reading_ease, ease_grade = calculate_reading_ease(content)

        # --- Top Summary Row ---
        st.header("Comprehensive Content Analysis Report")

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.markdown(f'<div class="score-card"><div class="score-value">{total_score}/100</div><div class="score-label">TOTAL RANKING SCORE</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="score-card"><div class="score-value">{word_count}</div><div class="score-label">WORD COUNT</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="score-card"><div class="score-value">{len(paragraphs)}</div><div class="score-label">PARAGRAPHS</div></div>', unsafe_allow_html=True)
        with col4:
            st.markdown(f'<div class="score-card"><div class="score-value">{reading_ease:.1f}</div><div class="score-label">FLESCH EASE SCORE</div></div>', unsafe_allow_html=True)
        with col5:
            st.markdown(f'<div class="score-card"><div class="score-value">{ease_grade}</div><div class="score-label">READABILITY GRADE</div></div>', unsafe_allow_html=True)


        st.subheader("3. 🎯 Priority Actions List")
        if findings['priority_actions']:
            st.warning("⚠️ Critical Fixes Recommended")
            for action in set(findings['priority_actions']): # Use set to remove duplicates
                st.markdown(f'<div class="priority-item">{action}</div>', unsafe_allow_html=True)
        else:
            st.success("🎉 No high-priority missing signals detected.")

        st.markdown("---")

        # --- Detailed Section Analysis ---

        # 1. E-E-A-T & Utility
        st.subheader(f"I. E-E-A-T & Utility ({findings['eeat']['score']}/{findings['eeat']['max']} pts)")
        col_eeat_cue, col_eeat_miss = st.columns(2)
        with col_eeat_cue:
            st.markdown("#### Positive Cues (Strengths)")
            for cue in findings['eeat']['cues']:
                st.markdown(f'<div class="positive-cue">✅ {cue}</div>', unsafe_allow_html=True)
            if not findings['eeat']['cues']:
                st.markdown("No strong E-E-A-T or Utility cues found.")
        with col_eeat_miss:
            st.markdown("#### Missing Signals (Improvement)")
            for miss in findings['eeat']['missing']:
                st.markdown(f'<div class="missing-signal">❌ {miss}</div>', unsafe_allow_html=True)
            if not findings['eeat']['missing']:
                st.markdown("All primary E-E-A-T signals appear present.")

        st.markdown("---")

        # 2. Keyword Relevance
        st.subheader(f"II. Keyword Relevance ({findings['keyword']['score']}/{findings['keyword']['max']} pts)")
        col_kw_cue, col_kw_miss = st.columns(2)
        with col_kw_cue:
            st.markdown("#### Positive Cues (Strengths)")
            for cue in findings['keyword']['cues']:
                st.markdown(f'<div class="positive-cue">✅ {cue}</div>', unsafe_allow_html=True)
            if not findings['keyword']['cues']:
                st.markdown("No keyword cues found.")
        with col_kw_miss:
            st.markdown("#### Missing Signals (Improvement)")
            for miss in findings['keyword']['missing']:
                st.markdown(f'<div class="missing-signal">❌ {miss}</div>', unsafe_allow_html=True)
            if not findings['keyword']['missing']:
                st.markdown("Keyword placement is optimized.")

        st.markdown("---")

        # 3. Integrity & Compliance (SpamBrain)
        st.subheader(f"III. Integrity & Compliance (SpamBrain) ({findings['integrity']['score']}/{findings['integrity']['max']} pts)")
        col_int_cue, col_int_miss = st.columns(2)
        with col_int_cue:
            st.markdown("#### Compliance Status")
            for cue in findings['integrity']['cues']:
                st.markdown(f'<div class="positive-cue">✅ {cue}</div>', unsafe_allow_html=True)
            if not findings['integrity']['cues']:
                st.markdown("No immediate compliance cues found (neutral).")
        with col_int_miss:
            st.markdown("#### Violation Warnings")
            for miss in findings['integrity']['missing']:
                st.markdown(f'<div class="missing-signal">❌ {miss}</div>', unsafe_allow_html=True)
            if not findings['integrity']['missing']:
                st.markdown("No major violation warnings detected.")

        st.markdown("---")

        # 4. Technical, Freshness & Link Strategy
        st.subheader(f"IV. Technical, Freshness & Link Strategy ({findings['technical']['score']}/{findings['technical']['max']} pts)")
        col_tech_cue, col_tech_miss = st.columns(2)
        with col_tech_cue:
            st.markdown("#### Positive Cues (Strengths)")
            for cue in findings['technical']['cues']:
                st.markdown(f'<div class="positive-cue">✅ {cue}</div>', unsafe_allow_html=True)
            if not findings['technical']['cues']:
                st.markdown("No technical or link cues found.")
        with col_tech_miss:
            st.markdown("#### Missing Signals (Improvement)")
            for miss in findings['technical']['missing']:
                st.markdown(f'<div class="missing-signal">❌ {miss}</div>', unsafe_allow_html=True)
            if not findings['technical']['missing']:
                st.markdown("Structural/Technical elements appear strong.")

        st.markdown("---")
        st.info("💡 **Next Steps:** Use the Priority Actions List to refine your draft, paying special attention to E-E-A-T signals like original experience and strong external sourcing.")

    elif analyze_button:
        st.error("Please ensure you paste content and enter a target keyword before running the analysis.")

if __name__ == '__main__':
    main_app()
