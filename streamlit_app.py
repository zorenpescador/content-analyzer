import streamlit as st
import re
from typing import Dict, Any, Tuple

# --- Configuration and Weights (Based on Google Ranking Systems Explained) ---

MAX_SCORE = 100
WEIGHTS = {
    # I. Editorial & Authority (Max 35 pts)
    "EEAT_EXPERIENCE": 10,
    "EEAT_TRUST_EXPERT": 15,
    "UTILITY_DEPTH": 10,
    # II. Topical Relevance (Max 20 pts)
    "KEYWORD_RELEVANCE": 20,
    # III. Integrity (SpamBrain, AI) (Max 20 pts)
    "INTEGRITY_COMPLIANCE": 20, 
    # IV. Technical, Freshness & Link Strategy (Max 25 pts)
    "TECHNICAL_FRESHNESS": 25,
}

# Key phrases derived from the "Google Ranking Systems Explained" document
EEAT_EXPERIENCE_KEYWORDS = [
    r"i tested", r"in my experience", r"my results", r"proprietary data", 
    r"i found that", r"after using", r"i discovered", r"original analysis"
]
EEAT_TRUST_KEYWORDS = [
    r"author:", r"byline", r"credentials", r"references", r"cited", 
    r"disclaimer", r"verified by", r"published in"
]
SPAM_MANIPULATION_KEYWORDS = [
    r"buy now", r"best price", r"click here", r"unbeatable", 
    r"limited time offer", r"money back guarantee", r"must have"
]
AI_DISCLOSURE_KEYWORDS = [
    r"ai-generated", r"automated content", r"large language model", 
    r"edited by ai"
]
REPETITIVE_PATTERNS = [
    r"it is a great", r"this is the best", r"very great", r"fantastic opportunity"
]
# New keywords for Freshness and Linking strategy
FRESHNESS_LINKING_KEYWORDS = {
    "internal_link": r"\[internal link\]",
    "external_link": r"\[external link\]",
    "updated_date": r"updated:\s*\d{4}|\bas of\s*\d{4}" # e.g., "Updated: 2024" or "as of 2025"
}


def segment_content(content: str) -> Dict[str, Any]:
    """Splits content into sections and extracts structural data."""
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    if not paragraphs:
        return {"intro": "", "body": "", "conclusion": "", "paragraphs": [], "headings": []}

    intro = paragraphs[0]
    conclusion = paragraphs[-1] if len(paragraphs) > 1 else ""
    body = "\n\n".join(paragraphs[1:-1]) if len(paragraphs) > 2 else ""
    
    headings = re.findall(r'(##|###|####)\s*(.*)', content)
    
    return {"intro": intro, "body": body, "conclusion": conclusion, "paragraphs": paragraphs, "headings": headings}


def calculate_flesch_reading_ease(content: str) -> float:
    """Calculates a simplified Flesch Reading Ease score (proxy)."""
    sentences = re.split(r'[.!?]+', content)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    words = re.findall(r'\b\w+\b', content)
    word_count = len(words)
    sentence_count = len(sentences)

    if word_count == 0 or sentence_count == 0:
        return 0.0

    # Proxy for Syllables per Word (ASW) - generally averages 1.5 in English
    ASL = word_count / sentence_count
    ASW = 1.5 # Fixed proxy for simplicity
    
    flesch_score = 206.835 - (1.015 * ASL) - (84.6 * ASW)
    return max(0, flesch_score)


def analyze_content(content: str, target_keyword: str) -> Dict[str, Any]:
    """Analyzes content against all core ranking system mandates."""
    content_lower = content.lower()
    sections = segment_content(content)
    word_count = len(re.findall(r'\b\w+\b', content))
    
    results = {
        "word_count": word_count,
        "flesch_ease": calculate_flesch_reading_ease(content),
        "total_score": 0,
        "sections": {}
    }

    # --- Core Analysis Functions ---

    def check_eeat_utility(content_lower: str, word_count: int, sections: Dict[str, Any]) -> Tuple[float, list]:
        """I. Editorial & Authority: E-E-A-T, Utility, and Intent (Max 35 pts)"""
        score = 0
        findings = []
        
        # 1. Experience & Originality (Max 10 pts)
        experience_matches = sum(len(re.findall(k, content_lower)) for k in EEAT_EXPERIENCE_KEYWORDS)
        
        if experience_matches >= 4:
            score += WEIGHTS['EEAT_EXPERIENCE']
            findings.append({"type": "Good", "text": f"Strong experiential language detected ({experience_matches} cues). (Mandate: **Experience**)"})
        else:
            score += WEIGHTS['EEAT_EXPERIENCE'] * 0.3
            findings.append({"type": "Missing", "text": "Lack of verifiable first-hand Experience (E). Add 'I tested' or 'my data' cues."})

        # 2. Trustworthiness & Expertise (Max 15 pts)
        trust_matches = sum(len(re.findall(k, content_lower)) for k in EEAT_TRUST_KEYWORDS)
        if trust_matches >= 3 or 'author:' in content_lower:
            score += WEIGHTS['EEAT_TRUST_EXPERT']
            findings.append({"type": "Good", "text": f"Cues for authorship, sourcing, or credentials found ({trust_matches} cues). (Mandate: **Trustworthiness**)"})
        else:
            score += WEIGHTS['EEAT_TRUST_EXPERT'] * 0.2
            findings.append({"type": "Missing", "text": "Clear authorship (WHO) or external sourcing/vetting signals are weak or missing. (Mandate: Trustworthiness)"})

        # 3. Utility, Depth, & Intent Fulfillment (Max 10 pts)
        # Depth Check (5 pts)
        if word_count >= 1000:
            score += 5
            findings.append({"type": "Good", "text": f"Substantial content depth ({word_count} words). Supports deep user intent satisfaction."})
        elif word_count < 300:
            findings.append({"type": "Missing", "text": f"Content is too short ({word_count} words), risking categorization as low-utility. (Mandate: Utility)"})
        else:
            score += 3
            findings.append({"type": "Warn", "text": f"Mid-range length ({word_count} words). Ensure quality outweighs the quantity."})

        # Intent Fulfillment (Question-Answer Structure) (5 pts)
        question_matches = len(re.findall(r'\?[\s\n][A-Z]', content)) # Question followed by capitalized letter (start of answer)
        if question_matches >= 3:
            score += 5
            findings.append({"type": "Good", "text": f"Strong **Intent Fulfillment** structure ({question_matches} Q/A cues). Excellent 'People-First' signal."})
        elif question_matches >= 1:
            score += 2
            findings.append({"type": "Warn", "text": "Some Q/A structure found. Explicitly ask and answer user questions within the body."})

        return round(score, 2), findings

    def check_keyword_relevance(content: str, target_keyword: str, word_count: int, sections: Dict[str, Any]) -> Tuple[float, list]:
        """II. Topical Relevance (Max 20 pts)"""
        score = 0
        findings = []
        if not target_keyword:
            return 0, [{"type": "Warn", "text": "Target Keyword is missing. Relevance analysis skipped."}]
            
        keyword_lower = target_keyword.lower()
        
        # 1. Density Check (Max 10 pts)
        keyword_matches = len(re.findall(r'\b' + re.escape(keyword_lower) + r'\b', content.lower()))
        density = (keyword_matches / word_count) * 100 if word_count > 0 else 0
        
        if 1.0 <= density <= 3.0:
            score += 10
            findings.append({"type": "Good", "text": f"Optimal Keyword Density ({density:.2f}%) achieved. (Target: 1%-3%)."})
        elif density > 4.0:
            findings.append({"type": "Missing", "text": f"High Density ({density:.2f}%) suggests keyword stuffing/over-optimization risk."})
        else:
            score += 5
            findings.append({"type": "Warn", "text": f"Sub-optimal Density ({density:.2f}%). Review for under or slight over-optimization."})


        # 2. Contextual Placement (Max 10 pts)
        if keyword_lower in sections['intro'].lower():
            score += 10
            findings.append({"type": "Good", "text": "Keyword found in the critical **Introduction** section (Strong Contextual Relevance)."})
        else:
            findings.append({"type": "Missing", "text": "Keyword not found in the introductory context (Usability/Context)."})

        return round(score, 2), findings

    def check_integrity_compliance(content_lower: str) -> Tuple[float, list]:
        """III. Integrity & Compliance (SpamBrain) (Max 20 pts)"""
        score = WEIGHTS['INTEGRITY_COMPLIANCE'] 
        total_penalty = 0
        findings = []

        # Penalty 1: Spam/Commercial Language (Max -5 pts)
        spam_matches = sum(len(re.findall(k, content_lower)) for k in SPAM_MANIPULATION_KEYWORDS)
        if spam_matches > 0:
            penalty = min(spam_matches * 5, 10)
            score -= penalty
            total_penalty += penalty
            findings.append({"type": "Missing", "text": f"**Commercial/Spammy language** detected ({spam_matches} instances). (Mandate: SpamBrain)"})

        # Penalty 2: Repetitive/Formulaic Patterns (Max -5 pts)
        repetitive_matches = sum(len(re.findall(k, content_lower)) for k in REPETITIVE_PATTERNS)
        if repetitive_matches >= 3:
            score -= 5
            total_penalty += 5
            findings.append({"type": "Missing", "text": f"High frequency of **repetitive, formulaic phrasing** ({repetitive_matches} matches). (Mandate: Search Engine-First Warning)"})
        
        # Transparency Check & Penalty 3 (Max -10 pts)
        is_ai_disclosed = any(k in content_lower for k in AI_DISCLOSURE_KEYWORDS)

        if is_ai_disclosed:
            findings.append({"type": "Good", "text": 'Explicit **AI use disclosure** detected. (Mandate: The HOW of Transparency)'})
        else:
            findings.append({"type": "Missing", "text": 'AI use is **not disclosed**. Clarify the role of automation if LLMs were used. (Mandate: Transparency)'})
            
            if total_penalty > 0:
                score -= 10
                total_penalty += 10
                findings.append({"type": "Missing", "text": '***CRITICAL:*** Lack of AI disclosure combined with other manipulative signals increases the risk of a SpamBrain violation.'})

        # FINAL ZERO-OUT RULE: If the total penalty is too high (>= 20), set score to 0
        if total_penalty >= 20: 
            score = 0
            findings.append({"type": "Missing", "text": '**TOTAL FAILURE:** Multiple severe compliance issues detected. Score reset to 0/20 per strict compliance policy.'})

        return max(0, score), findings
    
    def check_technical_freshness_linking(content_lower: str, sections: Dict[str, Any], flesch_ease: float) -> Tuple[float, list]:
        """IV. Technical, Freshness & Link Strategy (Max 25 pts)"""
        score = 0
        findings = []
        
        # 1. Usability & Readability (Page Experience Proxy) (Max 10 pts)
        # Flesch Readability Check (5 pts)
        if flesch_ease > 60:
            score += 5
            findings.append({"type": "Good", "text": f"High Readability (Flesch Ease: {flesch_ease:.1f}). Supports mobile/Page Experience."})
        else:
            findings.append({"type": "Missing", "text": f"Low Readability (Flesch Ease: {flesch_ease:.1f}). Text is complex; hurts user experience."})

        # Paragraph Length Check (5 pts)
        paragraphs = sections['paragraphs']
        if paragraphs:
            para_word_counts = [len(re.findall(r'\b\w+\b', p)) for p in paragraphs]
            avg_para_length = sum(para_word_counts) / len(paragraphs)
            
            if avg_para_length < 80:
                score += 5
                findings.append({"type": "Good", "text": f"Excellent paragraph segmentation (Avg. {avg_para_length:.1f} words)."})
            else:
                findings.append({"type": "Missing", "text": f"Poor paragraph segmentation (Avg. {avg_para_length:.1f} words). Break up large blocks."})
        
        # 2. Freshness Signal (Max 5 pts)
        freshness_match = len(re.findall(FRESHNESS_LINKING_KEYWORDS["updated_date"], content_lower))
        if freshness_match >= 1:
            score += 5
            findings.append({"type": "Good", "text": "Explicit **Freshness Signal** detected (e.g., 'Updated: 2024'). Signals active maintenance."})
        else:
            findings.append({"type": "Warn", "text": "Missing clear date/freshness cues (e.g., 'Updated: [Year]'). Add a recent update timestamp."})

        # 3. Linking Strategy (Internal/External) (Max 10 pts)
        internal_links = len(re.findall(FRESHNESS_LINKING_KEYWORDS["internal_link"], content_lower))
        external_links = len(re.findall(FRESHNESS_LINKING_KEYWORDS["external_link"], content_lower))
        
        if internal_links >= 3 and external_links >= 1:
            score += 10
            findings.append({"type": "Good", "text": f"Strong Linking Strategy found ({internal_links} Internal, {external_links} External). Excellent for authority and site quality."})
        elif internal_links >= 1 or external_links >= 1:
            score += 5
            findings.append({"type": "Warn", "text": f"Weak Linking Strategy detected. Ensure at least 3 [Internal Link] and 1 [External Link] for authority building."})
        else:
            findings.append({"type": "Missing", "text": "No Link Placeholders found. Add **[Internal Link]** and **[External Link]** cues where appropriate."})
            
        return max(0, score), findings


    # --- Execute Checks ---
    
    score_eeat, findings_eeat = check_eeat_utility(content_lower, word_count, sections)
    score_keyword, findings_keyword = check_keyword_relevance(content, target_keyword, word_count, sections)
    score_integrity, findings_integrity = check_integrity_compliance(content_lower)
    score_tech_exp, findings_tech_exp = check_technical_freshness_linking(content_lower, sections, results['flesch_ease'])

    results["sections"]["I. Editorial & Authority (E-E-A-T, Intent)"] = {"score": score_eeat, "max": 35, "findings": findings_eeat}
    results["sections"]["II. Topical Relevance (Keyword Alignment)"] = {"score": score_keyword, "max": 20, "findings": findings_keyword}
    results["sections"]["III. Integrity & Compliance (SpamBrain)"] = {"score": score_integrity, "max": 20, "findings": findings_integrity}
    results["sections"]["IV. Technical, Freshness & Link Strategy"] = {"score": score_tech_exp, "max": 25, "findings": findings_tech_exp}
    results["sections_data"] = sections

    results["total_score"] = score_eeat + score_keyword + score_integrity + score_tech_exp
    return results

# --- Streamlit UI and Report Generation (Same as previous version for stability) ---

def generate_streamlit_report(results: Dict[str, Any]):
    """Generates the Streamlit display for the analysis report."""
    
    max_total_score = sum(WEIGHTS.values())
    percentage = (results['total_score'] / max_total_score) * 100
    
    st.markdown("---")
    
    # -------------------------------------------------------------------
    # Actionable Summary & Core Metrics
    # -------------------------------------------------------------------
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(label="Overall Quality Score", 
                  value=f"{results['total_score']:.2f} / {max_total_score}",
                  delta=f"{percentage:.1f}%")

    with col2:
        st.metric(label="Word Count", value=results['word_count'])

    with col3:
        # Display Flesch Ease with descriptive feedback
        flesch_ease = results['flesch_ease']
        if flesch_ease >= 60:
            ease_feedback = "Easy to Read"
        elif flesch_ease >= 30:
            ease_feedback = "Moderately Difficult"
        else:
            ease_feedback = "Very Difficult"
        st.metric(label="Flesch Reading Ease", value=f"{flesch_ease:.1f}", delta=ease_feedback)

    with col4:
        if percentage >= 85:
            st.success("Status: EXCELLENT (High alignment with all core systems.)")
        elif percentage >= 60:
            st.warning("Status: GOOD (Foundation is strong; risks need mitigation.)")
        else:
            st.error("Status: ACTION REQUIRED (Missing key quality signals.)")
            
    st.markdown("---")
    
    # Actionable Priority List
    priority_findings = []
    for section_title, section in results['sections'].items():
        if section_title != "sections_data":
            priority_findings.extend([
                f"**{section_title.split('(')[0].strip()}** | {f['text'].replace('***CRITICAL:***', '')}" 
                for f in section['findings'] if f['type'] in ('Missing', 'Warn')
            ])

    if priority_findings:
        st.header("🎯 Priority Action List")
        st.caption("Focus on these issues first to minimize risk and maximize compliance.")
        for i, finding in enumerate(priority_findings[:5]): # Show top 5 priorities
            st.markdown(f"**{i+1}.** {finding}")
        st.markdown("---")
    
    # -------------------------------------------------------------------
    # Detailed Section Breakdown
    # -------------------------------------------------------------------
    
    st.header("Comprehensive Breakdown by Ranking Mandate")
    
    for title, section in results['sections'].items():
        if title == "sections_data": continue
        
        section_percent = (section['score'] / section['max']) * 100
        
        # Determine the icon based on the section score
        if section_percent >= 85:
            icon = "✅"
            expander = st.expander(f"**{icon} {title}** (Score: {section['score']:.2f} / {section['max']} pts)", expanded=False)
        elif section_percent >= 50:
            icon = "🟡"
            expander = st.expander(f"**{icon} {title}** (Score: {section['score']:.2f} / {section['max']} pts)", expanded=True)
        else:
            icon = "❌"
            expander = st.expander(f"**{icon} {title}** (Score: {section['score']:.2f} / {section['max']} pts)", expanded=True)

        with expander:
            st.caption(f"Section Alignment: {section_percent:.1f}%")
            for finding in section['findings']:
                if finding['type'] == 'Good':
                    st.success(f"**Positive Cue:** {finding['text']}", icon="👍")
                elif finding['type'] == 'Warn':
                    st.warning(f"**Improvement Needed:** {finding['text']}", icon="⚠️")
                else:
                    st.error(f"**Missing Signal:** {finding['text']}", icon="🛑")


def render_structural_map(sections: Dict[str, Any]):
    """Renders the Structural Map in the sidebar."""
    st.sidebar.header("🗺️ Structural Map")
    st.sidebar.caption("Review H2/H3/H4 hierarchy.")
    
    headings = sections['headings']
    if not headings:
        st.sidebar.warning("No headings (##, ###, ####) found in content.")
        return

    map_html = "<ul>"
    for level_str, text in headings:
        level = len(level_str) 
        indent = (level - 2) * 20 
        
        if level == 2:
            symbol = "●"
            style = "font-weight: bold;"
        elif level == 3:
            symbol = "○"
            style = "font-style: italic;"
        else:
            symbol = "—"
            style = ""
            
        map_html += f"<li style='margin-left: {indent}px; {style} list-style: none;'>{symbol} {text}</li>"
        
    map_html += "</ul>"
    st.sidebar.markdown(map_html, unsafe_allow_html=True)


def main():
    st.set_page_config(page_title="Google Ranking Content Analyzer (V5)", layout="wide")
    
    st.title("📚 Comprehensive Content Quality Analyzer (V5)")
    st.markdown("""
        Analyzes content against four core mandates: **E-E-A-T/Intent**, **Relevance**, **Integrity**, and **Freshness/Linking Strategy**.
    """)
    st.markdown("---")

    col_input_1, col_input_2 = st.columns([3, 1])
    
    with col_input_2:
        target_keyword = st.text_input(
            "Target Keyword/Phrase",
            placeholder="e.g., Core Web Vitals best practices"
        )
    
    with col_input_1:
        placeholder_content = """
        Paste your article or draft content here. Use double newlines for paragraph breaks (Enter twice).

        To score well on the new checks, include:
        1. Experience cues (e.g., 'I tested', 'my results').
        2. Q/A structure (e.g., "Why is this important? The reason is...").
        3. Freshness cues (e.g., 'Updated: 2024').
        4. Link Cues (e.g., '[Internal Link]' or '[External Link]').
        """
        content = st.text_area(
            "Paste Content for Analysis",
            placeholder=placeholder_content,
            height=350
        )
    
    if st.button("Run Comprehensive Analysis", type="primary"):
        if not content:
            st.error("Please paste content into the text area to run the analysis.")
        else:
            with st.spinner('Analyzing content against core ranking guidelines...'):
                analysis_results = analyze_content(content, target_keyword)
                
                render_structural_map(analysis_results["sections_data"])
                generate_streamlit_report(analysis_results)

if __name__ == "__main__":
    main()
