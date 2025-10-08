import streamlit as st
import re
from typing import Dict, Any, Tuple

# --- Configuration and Weights (Based on Google Ranking Systems Explained) ---

MAX_SCORE = 100
WEIGHTS = {
    # I. Editorial & Authority (Max 40 pts)
    "EEAT_EXPERIENCE": 15,
    "EEAT_TRUST_EXPERT": 15,
    "UTILITY_DEPTH": 10,
    # II. Topical Relevance (Max 20 pts)
    "KEYWORD_RELEVANCE": 20,
    # III. Integrity (SpamBrain, AI) (Max 20 pts)
    "INTEGRITY_COMPLIANCE": 20, 
    # IV. Technical & Experience (CWV/Usability Proxy) (Max 20 pts)
    "TECHNICAL_EXPERIENCE": 20,
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
EDITORIAL_QUALITY_KEYWORDS = [
    r"updated on", r"correction:", r"fact checked", r"editorial review"
]


def segment_content(content: str) -> Dict[str, str]:
    """Splits content into Introduction, Body, and Conclusion heuristically."""
    # Split content by double newlines (typical paragraph break)
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    
    if not paragraphs:
        return {"intro": "", "body": "", "conclusion": ""}

    intro = paragraphs[0]
    conclusion = paragraphs[-1] if len(paragraphs) > 1 else ""
    body = "\n\n".join(paragraphs[1:-1]) if len(paragraphs) > 2 else ""
    
    return {"intro": intro, "body": body, "conclusion": conclusion, "paragraphs": paragraphs}


def analyze_content(content: str, target_keyword: str) -> Dict[str, Any]:
    """Analyzes content against all core ranking system mandates."""
    content_lower = content.lower()
    sections = segment_content(content)
    word_count = len(re.findall(r'\b\w+\b', content))
    
    results = {
        "word_count": word_count,
        "total_score": 0,
        "sections": {}
    }

    # --- Core Analysis Functions ---

    def check_eeat_utility(content_lower: str, word_count: int, sections: Dict[str, str]) -> Tuple[float, list]:
        """I. Editorial & Authority: E-E-A-T and Utility (Max 40 pts)"""
        score = 0
        findings = []
        
        # 1. Experience & Originality (Max 15 pts)
        experience_matches = sum(len(re.findall(k, content_lower)) for k in EEAT_EXPERIENCE_KEYWORDS)
        
        if experience_matches >= 5:
            score += WEIGHTS['EEAT_EXPERIENCE']
            findings.append({"type": "Good", "text": f"Strong experiential language detected ({experience_matches} cues). (Mandate: **Experience** and **Reviews System** criteria met)"})
        elif experience_matches >= 1:
            score += WEIGHTS['EEAT_EXPERIENCE'] * 0.5
            findings.append({"type": "Warn", "text": f"Some experiential cues detected ({experience_matches}). Increase first-hand knowledge details/proprietary data. (Mandate: Experience)"})
        else:
            findings.append({"type": "Missing", "text": "Significant lack of verifiable first-hand Experience (E). (Mandate: Experience)"})

        # 2. Trustworthiness & Expertise (Max 15 pts)
        trust_matches = sum(len(re.findall(k, content_lower)) for k in EEAT_TRUST_KEYWORDS)
        
        if trust_matches >= 3 or 'author:' in content_lower:
            score += WEIGHTS['EEAT_TRUST_EXPERT']
            findings.append({"type": "Good", "text": f"Cues for authorship, sourcing, or credentials found ({trust_matches} cues). (Mandate: **Trustworthiness** & YMYL Scrutiny)"})
        else:
            score += WEIGHTS['EEAT_TRUST_EXPERT'] * 0.2
            findings.append({"type": "Missing", "text": "Clear authorship (WHO) or external sourcing/vetting signals are weak or missing. (Mandate: Trustworthiness)"})

        # 3. Utility & Depth (Max 10 pts)
        if word_count >= 1000:
            score += WEIGHTS['UTILITY_DEPTH']
            findings.append({"type": "Good", "text": f"Substantial content depth ({word_count} words). Supports deep user intent satisfaction. (Mandate: **Utility**)"})
        elif word_count < 300:
            score += WEIGHTS['UTILITY_DEPTH'] * 0.1
            findings.append({"type": "Missing", "text": f"Content is too short ({word_count} words), risking categorization as low-utility. (Mandate: Utility)"})
        else:
            score += WEIGHTS['UTILITY_DEPTH'] * 0.6
            findings.append({"type": "Warn", "text": f"Mid-range length ({word_count} words). Ensure quality and comprehensiveness outweigh the quantity. (Mandate: Utility)"})

        return round(score, 2), findings

    def check_keyword_relevance(content: str, target_keyword: str, word_count: int, sections: Dict[str, str]) -> Tuple[float, list]:
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


        # 2. Contextual Placement (Max 10 pts) - Importance in Introduction
        # Check if keyword is present in the Introduction section (first paragraph)
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
    
    def check_technical_site_quality(content_lower: str, sections: Dict[str, str]) -> Tuple[float, list]:
        """IV. Technical & Page Experience (Max 20 pts)"""
        score = 0
        findings = []
        
        # 1. Usability & Readability (Page Experience Proxy) (Max 10 pts)
        paragraphs = sections['paragraphs']
        if paragraphs:
            para_word_counts = [len(re.findall(r'\b\w+\b', p)) for p in paragraphs]
            avg_para_length = sum(para_word_counts) / len(paragraphs)
            
            # Target short paragraphs for mobile/usability (e.g., avg < 80 words)
            if avg_para_length < 80:
                score += 10
                findings.append({"type": "Good", "text": f"Excellent readability (Avg. Paragraph length: {avg_para_length:.1f} words). Supports mobile/Page Experience."})
            elif avg_para_length < 120:
                score += 5
                findings.append({"type": "Warn", "text": f"Moderate readability (Avg. Paragraph length: {avg_para_length:.1f} words). Break up longer blocks for better mobile experience."})
            else:
                findings.append({"type": "Missing", "text": f"Poor readability (Avg. Paragraph length: {avg_para_length:.1f} words). Long paragraphs hurt user experience (CWV proxy)."})
        else:
            findings.append({"type": "Warn", "text": "Cannot assess paragraph length due to lack of distinct paragraph breaks."})

        # 2. Editorial Structure & Updates (Site Quality Proxy) (Max 10 pts)
        
        # Check for headings (simple proxy for good structure/scannability)
        heading_matches = len(re.findall(r'(##|###|####)', content_lower))
        if heading_matches >= 3:
            score += 5
            findings.append({"type": "Good", "text": f"Good structural organization detected ({heading_matches}+ headings). Essential for site quality and accessibility."})
        else:
            findings.append({"type": "Warn", "text": "Ensure proper heading structure (H2, H3, etc.) for accessibility and scannability."})
            
        # Check for Editorial Cues
        editorial_matches = sum(len(re.findall(k, content_lower)) for k in EDITORIAL_QUALITY_KEYWORDS)
        if editorial_matches >= 1:
            score += 5
            findings.append({"type": "Good", "text": "Editorial cues (e.g., 'updated', 'correction') found. Signals active site quality maintenance."})
        else:
            findings.append({"type": "Missing", "text": "Lack of clear site quality signals (e.g., recent update timestamps, editorial checks)."})
            
        return max(0, score), findings


    # --- Execute Checks ---
    
    score_eeat, findings_eeat = check_eeat_utility(content_lower, word_count, sections)
    score_keyword, findings_keyword = check_keyword_relevance(content, target_keyword, word_count, sections)
    score_integrity, findings_integrity = check_integrity_compliance(content_lower)
    score_tech_exp, findings_tech_exp = check_technical_site_quality(content_lower, sections)

    results["sections"]["I. Editorial & Authority (E-E-A-T, Utility)"] = {"score": score_eeat, "max": 40, "findings": findings_eeat}
    results["sections"]["II. Topical Relevance (Keyword Alignment)"] = {"score": score_keyword, "max": 20, "findings": findings_keyword}
    results["sections"]["III. Integrity & Compliance (SpamBrain)"] = {"score": score_integrity, "max": 20, "findings": findings_integrity}
    results["sections"]["IV. Technical & Page Experience (CWV Proxy)"] = {"score": score_tech_exp, "max": 20, "findings": findings_tech_exp}

    results["total_score"] = score_eeat + score_keyword + score_integrity + score_tech_exp
    return results

# --- Streamlit UI and Report Generation ---

def generate_streamlit_report(results: Dict[str, Any]):
    """Generates the Streamlit display for the analysis report."""
    
    max_total_score = sum(WEIGHTS.values())
    percentage = (results['total_score'] / max_total_score) * 100
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(label="Overall Quality Score", 
                  value=f"{results['total_score']:.2f} / {max_total_score}",
                  delta=f"{percentage:.1f}%")

    with col2:
        st.metric(label="Word Count", value=results['word_count'])

    with col3:
        if percentage >= 85:
            st.success("Status: EXCELLENT (High alignment with all core systems.)")
        elif percentage >= 60:
            st.warning("Status: GOOD (Solid foundation; address flagged risks.)")
        else:
            st.error("Status: ACTION REQUIRED (Missing key quality signals.)")
            
    st.markdown("---")
    
    # Detailed Section Breakdown
    st.header("Detailed Compliance Findings")
    st.markdown("Findings are categorized based on the four core mandates derived from Google's ranking systems.")
    
    for title, section in results['sections'].items():
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
                # Map finding type to Streamlit style
                if finding['type'] == 'Good':
                    st.success(f"**Positive Cue:** {finding['text']}", icon="👍")
                elif finding['type'] == 'Warn':
                    st.warning(f"**Improvement Needed:** {finding['text']}", icon="⚠️")
                else:
                    st.error(f"**Missing Signal:** {finding['text']}", icon="🛑")


def main():
    st.set_page_config(page_title="Google Ranking Content Analyzer", layout="wide")
    
    st.title("📚 Comprehensive Content Quality Analyzer (V2)")
    st.markdown("""
        Analyzes content against four core mandates: **Editorial/E-E-A-T**, **Relevance**, **Integrity**, and **Page Experience**.
    """)
    st.markdown("---")

    # Input Fields
    col_input_1, col_input_2 = st.columns([3, 1])
    
    with col_input_2:
        target_keyword = st.text_input(
            "Target Keyword/Phrase (Mandatory for Relevance Check)",
            placeholder="e.g., Core Web Vitals best practices"
        )
    
    with col_input_1:
        placeholder_content = """
        Paste your article or draft content here. Use double newlines for paragraph breaks (Enter twice).

        Ensure you include:
        1. Experience cues (e.g., 'I tested', 'my results').
        2. Authorship/Sourcing (e.g., 'Author: [Name]').
        3. Headings (##, ###) for structure.
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
                generate_streamlit_report(analysis_results)

if __name__ == "__main__":
    main()
