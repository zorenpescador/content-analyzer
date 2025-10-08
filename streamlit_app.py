import streamlit as st
import re
from typing import Dict, Any, Tuple

# --- Configuration and Weights (Based on content_guidelines.md) ---

MAX_SCORE = 100
WEIGHTS = {
    "EEAT_EXPERIENCE": 20,
    "EEAT_TRUST_EXPERT": 15,
    "UTILITY_DEPTH": 15,
    "KEYWORD_RELEVANCE": 25,
    "INTEGRITY_COMPLIANCE": 25,
}

# Key phrases derived from content_guidelines.md
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
# Proxy for formulaic/repetitive patterns (low editorial effort)
REPETITIVE_PATTERNS = [
    r"it is a great", r"this is the best", r"very great", r"fantastic opportunity"
]


def analyze_content(content: str, target_keyword: str) -> Dict[str, Any]:
    """
    Analyzes content against E-E-A-T, Integrity, Utility, and Keyword Relevance.
    """
    content_lower = content.lower()
    word_count = len(re.findall(r'\b\w+\b', content))
    
    # Initialize results structure
    results = {
        "word_count": word_count,
        "total_score": 0,
        "sections": {}
    }

    # --- Analysis Functions ---

    def check_eeat(content_lower: str, word_count: int) -> Tuple[float, list]:
        """I. The Editorial Mandate: E-E-A-T and Utility"""
        score = 0
        findings = []
        
        # 1. Experience & Originality (Max 20 pts)
        experience_matches = sum(len(re.findall(k, content_lower)) for k in EEAT_EXPERIENCE_KEYWORDS)
        
        if experience_matches >= 5:
            score += WEIGHTS['EEAT_EXPERIENCE']
            findings.append({"type": "Good", "text": f"Strong experiential language detected ({experience_matches} cues). (Guideline: E-E-A-T Experience)"})
        elif experience_matches >= 1:
            score += WEIGHTS['EEAT_EXPERIENCE'] * 0.5
            findings.append({"type": "Warn", "text": f"Some experiential cues detected ({experience_matches}). Increase first-hand knowledge details. (Guideline: E-E-A-T Experience)"})
        else:
            findings.append({"type": "Missing", "text": "Significant lack of verifiable first-hand Experience (E). (Guideline: E-E-A-T Experience)"})

        # 2. Trustworthiness & Expertise (Max 15 pts)
        trust_matches = sum(len(re.findall(k, content_lower)) for k in EEAT_TRUST_KEYWORDS)
        
        if trust_matches >= 3 or 'author:' in content_lower:
            score += WEIGHTS['EEAT_TRUST_EXPERT']
            findings.append({"type": "Good", "text": f"Cues for authorship, sourcing, or credentials found ({trust_matches} cues). (Guideline: Trustworthiness & Expertise)"})
        else:
            score += WEIGHTS['EEAT_TRUST_EXPERT'] * 0.2
            findings.append({"type": "Missing", "text": "Clear authorship or external sourcing/vetting signals are weak or missing. (Guideline: Trustworthiness & Expertise)"})

        # 3. Utility & Depth (Max 15 pts)
        if word_count >= 800:
            score += WEIGHTS['UTILITY_DEPTH']
            findings.append({"type": "Good", "text": f"Substantial content depth ({word_count} words), supports satisfying user intent. (Guideline: Utility)"})
        elif word_count < 300:
            score += WEIGHTS['UTILITY_DEPTH'] * 0.1
            findings.append({"type": "Missing", "text": f"Content is too short ({word_count} words), risking categorization as low-utility. (Guideline: Utility)"})
        else:
            score += WEIGHTS['UTILITY_DEPTH'] * 0.7
            findings.append({"type": "Warn", "text": f"Mid-range length ({word_count} words). Ensure quality and comprehensiveness outweigh the quantity. (Guideline: Utility)"})

        return round(score, 2), findings

    def check_keyword_relevance(content: str, target_keyword: str, word_count: int) -> Tuple[float, list]:
        """II. Keyword Relevance and Context"""
        score = 0
        findings = []
        keyword_lower = target_keyword.lower()

        # 1. Density Check (Max 15 pts)
        keyword_matches = len(re.findall(r'\b' + re.escape(keyword_lower) + r'\b', content.lower()))
        density = (keyword_matches / word_count) * 100 if word_count > 0 else 0
        
        # Optimal density is 1% to 3%
        if 1.0 <= density <= 3.0:
            score += 15
            findings.append({"type": "Good", "text": f"Optimal Keyword Density ({density:.2f}%) achieved. (Target: 1%-3%)"})
        elif 0.5 < density < 1.0 or 3.0 < density <= 4.0:
            score += 10
            findings.append({"type": "Warn", "text": f"Sub-optimal Density ({density:.2f}%). Review for under or slight over-optimization."})
        elif density > 4.0:
            findings.append({"type": "Missing", "text": f"High Density ({density:.2f}%) suggests keyword stuffing/over-optimization risk."})
        else:
            findings.append({"type": "Missing", "text": f"Very low Density ({density:.2f}%) indicates the content lacks focus on the target topic."})


        # 2. Contextual Placement (Max 10 pts)
        # Check if keyword is in the first 100 words (proxy for title/h1/intro)
        first_100_words = " ".join(re.findall(r'\b\w+\b', content)[:100]).lower()
        if keyword_lower and keyword_lower in first_100_words:
            score += 10
            findings.append({"type": "Good", "text": "Keyword found in the critical initial 100 words (Contextual Relevance)."})
        elif not keyword_lower:
             findings.append({"type": "Warn", "text": "No target keyword provided for relevance check."})
        else:
            findings.append({"type": "Missing", "text": "Keyword not found in the introductory context (Usability/Context)."})

        return round(score, 2), findings

    def check_integrity_compliance(content_lower: str) -> Tuple[float, list]:
        """III. Integrity and Compliance (SpamBrain)"""
        score = WEIGHTS['INTEGRITY_COMPLIANCE'] # Start at 25 points
        total_penalty = 0
        findings = []

        # Penalty 1: Spam/Commercial Language (Max -10 pts)
        spam_matches = sum(len(re.findall(k, content_lower)) for k in SPAM_MANIPULATION_KEYWORDS)
        if spam_matches > 0:
            penalty = min(spam_matches * 5, 10)
            score -= penalty
            total_penalty += penalty
            findings.append({"type": "Missing", "text": f"**Commercial/Spammy language** detected ({spam_matches} instances). Review affiliate disclosures and overly promotional wording. (Guideline: Avoid Manipulation)"})

        # Penalty 2: Repetitive/Formulaic Patterns (Max -5 pts)
        repetitive_matches = sum(len(re.findall(k, content_lower)) for k in REPETITIVE_PATTERNS)
        if repetitive_matches >= 3:
            score -= 5
            total_penalty += 5
            findings.append({"type": "Missing", "text": f"High frequency of **repetitive, formulaic phrasing** ({repetitive_matches} matches). Signals low editorial effort/mass production. (Guideline: Link Strategy Proxy)"})
        
        # Transparency Check & Penalty 3 (Max -10 pts)
        is_ai_disclosed = any(k in content_lower for k in AI_DISCLOSURE_KEYWORDS)

        if is_ai_disclosed:
            findings.append({"type": "Good", "text": 'Explicit **AI use disclosure** detected. This is essential for transparency. (Guideline: AI/Automation Use)'})
        else:
            findings.append({"type": "Missing", "text": 'AI use is **not disclosed**. If LLMs were used, you must clarify the role of automation. (Guideline: AI/Automation Use)'})
            
            # Penalty for lack of disclosure only if other problems exist (SpamBrain Risk)
            if total_penalty > 0:
                score -= 10
                total_penalty += 10
                findings.append({"type": "Missing", "text": '***CRITICAL:*** Lack of AI disclosure combined with other manipulative signals increases the risk of a SpamBrain penalty.'})

        # FINAL ZERO-OUT RULE: If the total penalty is too high (>= 20), set score to 0
        if total_penalty >= 20: 
            score = 0
            findings.append({"type": "Missing", "text": '**TOTAL FAILURE:** Multiple severe compliance issues detected. Score reset to 0/25 per strict compliance policy.'})


        return max(0, score), findings

    # --- Execute Checks ---
    
    score_eeat, findings_eeat = check_eeat(content_lower, word_count)
    score_keyword, findings_keyword = check_keyword_relevance(content, target_keyword, word_count)
    score_integrity, findings_integrity = check_integrity_compliance(content_lower)

    results["sections"]["E-E-A-T & Utility"] = {"score": score_eeat, "max": WEIGHTS['EEAT_EXPERIENCE'] + WEIGHTS['EEAT_TRUST_EXPERT'] + WEIGHTS['UTILITY_DEPTH'], "findings": findings_eeat}
    results["sections"]["Keyword Relevance"] = {"score": score_keyword, "max": WEIGHTS['KEYWORD_RELEVANCE'], "findings": findings_keyword}
    results["sections"]["Integrity & Compliance"] = {"score": score_integrity, "max": WEIGHTS['INTEGRITY_COMPLIANCE'], "findings": findings_integrity}

    results["total_score"] = score_eeat + score_keyword + score_integrity
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
            st.success("Status: EXCELLENT")
        elif percentage >= 60:
            st.warning("Status: GOOD")
        else:
            st.error("Status: ACTION REQUIRED")
            
    st.markdown("---")
    
    # Detailed Section Breakdown
    st.header("Detailed Compliance Findings")
    
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
    
    st.title("📚 Content Quality Analyzer")
    st.markdown("""
        Analyze content alignment with Google's Core Ranking Systems (**E-E-A-T**, **Utility**, **SpamBrain**, and **Keyword Relevance**).
        \n*Based on the research from Google's Ranking Systems Guide.*
    """)
    st.markdown("---")

    # Input Fields
    col_input_1, col_input_2 = st.columns([3, 1])
    
    with col_input_2:
        target_keyword = st.text_input(
            "Target Keyword/Phrase (Required for Relevance Check)",
            placeholder="e.g., best air fryer 2024"
        )
    
    with col_input_1:
        placeholder_content = """
        Paste your article or draft content here. 
        Aim for a minimum of 300 words for the utility check.
        Ensure you include clear authorship (e.g., 'Author: [Name]') and verifiable experience cues (e.g., 'I tested', 'in my experience') to score highly on E-E-A-T.
        """
        content = st.text_area(
            "Paste Content for Analysis",
            placeholder=placeholder_content,
            height=300
        )
    
    if st.button("Run Comprehensive Analysis", type="primary"):
        if not content:
            st.error("Please paste content into the text area to run the analysis.")
        elif not target_keyword:
            st.warning("Analysis will run, but the Keyword Relevance check will be incomplete without a target keyword.")
            analysis_results = analyze_content(content, target_keyword)
            generate_streamlit_report(analysis_results)
        else:
            with st.spinner('Analyzing content against core ranking guidelines...'):
                analysis_results = analyze_content(content, target_keyword)
                generate_streamlit_report(analysis_results)

if __name__ == "__main__":
    main()
