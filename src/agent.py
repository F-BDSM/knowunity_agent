# Core Python imports
import json
from typing import Dict, List, Tuple, Optional, Any
import os
import time
from dotenv import load_dotenv

# External dependencies
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️ OpenAI not installed. Will use Gemini if available.")

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ Google Generative AI not installed.")

import requests

# Local API module imports
from src.api import (
    get_students,
    get_students_topics,
    start_conversation,
    interact,
    submit_mse_predictions,
    evaluate_tutoring,
    BASE_URL,
    API_KEY,
    SET_TYPE
)

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configuration - Choose which AI to use
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()  # "openai" or "gemini"
MODEL_NAME = os.getenv("AI_MODEL", "gemini-1.5-flash")  # Default to free Gemini model

# Initialize AI clients
openai_client = None
gemini_model = None

if AI_PROVIDER == "openai" and OPENAI_AVAILABLE and OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    print(f"✓ Using OpenAI with model: {MODEL_NAME if MODEL_NAME != 'gemini-1.5-flash' else 'gpt-3.5-turbo'}")
elif AI_PROVIDER == "gemini" and GEMINI_AVAILABLE and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel(MODEL_NAME)
    print(f"✓ Using Gemini with model: {MODEL_NAME}")
else:
    print("❌ ERROR: No AI provider configured!")
    print("Please set in .env file:")
    print("AI_PROVIDER=openai or gemini")
    print("OPENAI_API_KEY=your_key OR GEMINI_API_KEY=your_key")
    exit(1)

class InteractiveTutor:
    """Truly interactive tutor with memory and adaptive teaching."""
    
    def __init__(self, ai_provider: str = AI_PROVIDER):
        self.conversation_memory = {}
        self.student_preferences = {}
        self.teaching_history = {}
        self.ai_errors = []
        self.ai_provider = ai_provider
    
    def _call_ai(self, prompt: str, system_prompt: str = None, 
                temperature: float = 0.7, max_tokens: int = 300) -> str:
        """
        Unified AI calling function that works with both OpenAI and Gemini.
        Returns the AI response as text.
        """
        
        try:
            if self.ai_provider == "openai" and openai_client:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                response = openai_client.chat.completions.create(
                    model=MODEL_NAME if MODEL_NAME != "gemini-1.5-flash" else "gpt-3.5-turbo",
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content.strip()
                
            elif self.ai_provider == "gemini" and gemini_model:
                full_prompt = ""
                if system_prompt:
                    full_prompt = f"{system_prompt}\n\n{prompt}"
                else:
                    full_prompt = prompt
                
                response = gemini_model.generate_content(
                    full_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                    )
                )
                return response.text.strip()
                
            else:
                raise Exception(f"AI provider '{self.ai_provider}' not properly configured")
                
        except Exception as e:
            self.ai_errors.append({
                "provider": self.ai_provider,
                "error": str(e)
            })
            raise Exception(f"{self.ai_provider.upper()} API Failed: {str(e)}")
    
    def get_tutor_response(self, conversation_id: str, student_response: str, 
                          turn: int, topic_name: str, grade_level: int = 8) -> str:
        """
        Get an interactive tutor response that builds on the conversation.
        """
        
        # Initialize memory if needed
        if conversation_id not in self.conversation_memory:
            self._initialize_memory(conversation_id, topic_name, grade_level)
        
        memory = self.conversation_memory[conversation_id]
        prefs = self.student_preferences[conversation_id]
        
        # Update conversation history
        memory["history"].append({
            "turn": turn,
            "student": student_response,
            "timestamp": time.time()
        })
        
        # Analyze student response
        analysis = self._analyze_response(student_response, memory, prefs, turn)
        
        # Update memory with new insights
        self._update_memory(conversation_id, student_response, analysis)
        
        # Decide teaching action
        action = self._decide_teaching_action(memory, analysis, turn)
        
        # Generate response based on action
        response = self._generate_interactive_response(
            conversation_id, student_response, analysis, action, memory, prefs, turn
        )
        
        # Record teaching action
        memory["last_action"] = action
        memory["last_topic_covered"] = analysis.get("main_topic", "")
        
        return response
    
    def _initialize_memory(self, conversation_id: str, topic_name: str, grade_level: int):
        """Initialize memory for a new conversation."""
        
        self.conversation_memory[conversation_id] = {
            "topic": topic_name,
            "grade_level": grade_level,
            "history": [],
            "student_profile": {
                "confidence": 3,
                "engagement": 5,
                "preferred_style": "unknown",
                "learning_pace": "medium",
                "difficulties": [],
                "strengths": [],
                "misconceptions": [],
                "questions_asked": []
            },
            "teaching_progress": {
                "concepts_covered": [],
                "examples_given": [],
                "practice_problems": [],
                "corrections_made": []
            },
            "last_action": None,
            "last_topic_covered": None
        }
        
        self.student_preferences[conversation_id] = {
            "likes_examples": False,
            "likes_visuals": False,
            "prefers_short": False,
            "needs_repetition": False,
            "enjoys_challenges": False
        }
        
        self.teaching_history[conversation_id] = []
    
    def _analyze_response(self, response: str, memory: Dict, prefs: Dict, turn: int) -> Dict:
        """Analyze student response for understanding and needs."""
        
        history_text = ""
        for entry in memory["history"][-3:]:
            history_text += f"Turn {entry['turn']}: {entry['student']}\n"
        
        prompt = f"""
        Analyze this student response in a tutoring session.
        
        TOPIC: {memory['topic']}
        CURRENT TURN: {turn + 1}/10
        
        RECENT HISTORY:
        {history_text}
        
        CURRENT RESPONSE: "{response}"
        
        STUDENT PROFILE:
        - Confidence: {memory['student_profile']['confidence']}/5
        - Preferred style: {memory['student_profile']['preferred_style']}
        - Known difficulties: {memory['student_profile']['difficulties'][-3:] if memory['student_profile']['difficulties'] else 'none'}
        - Known strengths: {memory['student_profile']['strengths'][-3:] if memory['student_profile']['strengths'] else 'none'}
        
        Analyze and return JSON with:
        1. main_topic: What specific concept are they talking about?
        2. understanding_level: 1-5 (1=confused, 5=mastered)
        3. emotional_state: "confused", "frustrated", "curious", "confident", "bored", "engaged"
        4. needs_help_with: [specific things they need help with]
        5. has_misconception: true/false
        6. misconception_details: if true, what is it?
        7. is_asking_question: true/false
        8. question_type: if asking, what type? "clarification", "example", "practice", "explanation"
        9. preferred_learning_style_hint: Any hint about how they learn best?
        
        Respond with valid JSON only.
        """
        
        try:
            ai_response = self._call_ai(
                prompt=prompt,
                system_prompt="You are analyzing a student's response to understand their learning needs. Always respond with valid JSON.",
                temperature=0.3,
                max_tokens=400
            )
            
            # Try to parse JSON, handle potential issues
            try:
                return json.loads(ai_response)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    # Fallback to default analysis
                    return {
                        "main_topic": memory["topic"],
                        "understanding_level": 3,
                        "emotional_state": "neutral",
                        "needs_help_with": [],
                        "has_misconception": False,
                        "misconception_details": "",
                        "is_asking_question": False,
                        "question_type": "none",
                        "preferred_learning_style_hint": ""
                    }
            
        except Exception as e:
            self.ai_errors.append({
                "turn": turn,
                "operation": "analysis",
                "error": str(e)
            })
            raise Exception(f"AI Analysis Failed on turn {turn + 1}: {str(e)}")
    
    def _update_memory(self, conversation_id: str, response: str, analysis: Dict):
        """Update memory based on analysis."""
        
        memory = self.conversation_memory[conversation_id]
        prefs = self.student_preferences[conversation_id]
        profile = memory["student_profile"]
        
        # Update understanding level
        profile["confidence"] = analysis.get("understanding_level", profile["confidence"])
        
        # Track difficulties
        if analysis.get("needs_help_with"):
            for need in analysis["needs_help_with"]:
                if need not in profile["difficulties"]:
                    profile["difficulties"].append(need)
        
        # Track misconceptions
        if analysis.get("has_misconception") and analysis.get("misconception_details"):
            if analysis["misconception_details"] not in profile["misconceptions"]:
                profile["misconceptions"].append(analysis["misconception_details"])
        
        # Track questions asked
        if analysis.get("is_asking_question"):
            profile["questions_asked"].append(analysis.get("question_type", "general"))
        
        # Update preferences based on hints
        hint = analysis.get("preferred_learning_style_hint", "").lower()
        response_lower = response.lower()
        
        # Check for example preferences
        example_phrases = ["for example", "like when", "give me an example", "can you show me", "show me how", "for instance"]
        if "example" in hint or any(phrase in response_lower for phrase in example_phrases):
            prefs["likes_examples"] = True
            profile["preferred_style"] = "example-based"
            # Record example topic
            if analysis.get("main_topic"):
                memory["teaching_progress"]["examples_given"].append(analysis["main_topic"])
        
        # Check for concise preference
        short_phrases = ["briefly", "in short", "quick summary", "make it short", "keep it simple", "be concise"]
        if "short" in hint or any(phrase in response_lower for phrase in short_phrases):
            prefs["prefers_short"] = True
            profile["preferred_style"] = "concise"
        
        # Check for step-by-step preference
        step_phrases = ["step by step", "one at a time", "slowly", "break it down", "step through", "explain slowly"]
        if "step" in hint or any(phrase in response_lower for phrase in step_phrases):
            prefs["needs_repetition"] = True
            profile["preferred_style"] = "step-by-step"
    
    def _decide_teaching_action(self, memory: Dict, analysis: Dict, turn: int) -> str:
        """Decide what teaching action to take next."""
        
        profile = memory["student_profile"]
        
        # First two turns: diagnostic
        if turn < 2:
            return "diagnostic"
        
        # If student is confused, clarify
        if analysis["emotional_state"] in ["confused", "frustrated"]:
            return "clarify_confusion"
        
        # If student has misconception, correct it
        if analysis["has_misconception"]:
            return "correct_misconception"
        
        # If student is asking for something specific
        if analysis["is_asking_question"]:
            if analysis["question_type"] == "example":
                return "provide_example"
            elif analysis["question_type"] == "clarification":
                return "clarify_concept"
            elif analysis["question_type"] == "practice":
                return "give_practice"
            elif analysis["question_type"] == "explanation":
                return "explain_deeper"
        
        # If student needs help with something specific
        if analysis["needs_help_with"]:
            need = analysis["needs_help_with"][0]
            # Check if we've addressed this need before
            if need in profile["difficulties"][-3:]:  # Recently mentioned
                return "review_and_practice"
            else:
                return "address_specific_need"
        
        # Based on turn number
        if turn < 5:
            if profile["confidence"] < 3:
                return "teach_fundamentals"
            else:
                return "build_on_basics"
        elif turn < 8:
            return "apply_concepts"
        else:
            return "review_assess"
    
    def _generate_interactive_response(self, conversation_id: str, student_response: str,
                                     analysis: Dict, action: str, memory: Dict, 
                                     prefs: Dict, turn: int) -> str:
        """Generate an interactive response based on the teaching action."""
        
        topic = memory["topic"]
        
        # Build context string
        context = self._build_context_string(memory, prefs, analysis, turn)
        
        # Build instructions
        instructions = self._build_instructions(action, prefs, analysis, turn)
        
        prompt = f"""
        You are an interactive, engaging tutor having a 1-on-1 conversation.
        
        TOPIC: {topic}
        CURRENT TURN: {turn + 1}/10
        TEACHING ACTION: {action}
        
        STUDENT'S LAST RESPONSE: "{student_response}"
        
        {context}
        
        {instructions}
        
        YOUR RESPONSE (2-4 sentences, conversational, direct):
        """
        
        try:
            ai_response = self._call_ai(
                prompt=prompt,
                system_prompt="You are a patient, engaging tutor who listens carefully and responds specifically to each student's needs.",
                temperature=0.8,
                max_tokens=300
            )
            
            # Record teaching action
            self.teaching_history[conversation_id].append({
                "turn": turn,
                "action": action,
                "topic": analysis.get("main_topic", "general"),
                "response_preview": ai_response[:50] + "..."
            })
            
            # Record concept covered
            if analysis.get("main_topic"):
                memory["teaching_progress"]["concepts_covered"].append(analysis["main_topic"])
            
            return ai_response
            
        except Exception as e:
            self.ai_errors.append({
                "turn": turn,
                "operation": "response_generation",
                "action": action,
                "error": str(e)
            })
            raise Exception(f"AI Response Generation Failed on turn {turn + 1}: {str(e)}")
    
    def _build_context_string(self, memory: Dict, prefs: Dict, analysis: Dict, turn: int) -> str:
        """Build context string for the prompt."""
        
        profile = memory["student_profile"]
        teaching = memory["teaching_progress"]
        
        context_parts = []
        
        # Student profile
        context_parts.append(f"STUDENT PROFILE:")
        context_parts.append(f"- Confidence: {profile['confidence']}/5")
        context_parts.append(f"- Preferred learning style: {profile['preferred_style']}")
        
        if profile['difficulties']:
            context_parts.append(f"- Recent difficulties: {', '.join(profile['difficulties'][-2:])}")
        
        if profile['strengths']:
            context_parts.append(f"- Recent strengths: {', '.join(profile['strengths'][-2:])}")
        
        # Student preferences
        pref_list = []
        if prefs.get("likes_examples"):
            pref_list.append("LIKES EXAMPLES - always include concrete examples")
        if prefs.get("prefers_short"):
            pref_list.append("PREFERS SHORT explanations - be concise")
        if prefs.get("needs_repetition"):
            pref_list.append("NEEDS STEP-BY-STEP - break things down")
        
        if pref_list:
            context_parts.append(f"- KNOWN PREFERENCES: {', '.join(pref_list)}")
        
        # Current analysis
        context_parts.append(f"\nCURRENT ANALYSIS:")
        context_parts.append(f"- Emotional state: {analysis['emotional_state']}")
        context_parts.append(f"- Understanding level: {analysis['understanding_level']}/5")
        
        if analysis.get('needs_help_with'):
            context_parts.append(f"- Needs help with: {', '.join(analysis['needs_help_with'][:2])}")
        
        if analysis.get('has_misconception'):
            context_parts.append(f"- Has misconception: {analysis['misconception_details'][:50]}...")
        
        # What we've covered recently
        if teaching.get('concepts_covered'):
            context_parts.append(f"\nRECENTLY COVERED:")
            context_parts.append(f"- Concepts: {', '.join(teaching['concepts_covered'][-2:])}")
        
        if teaching.get('examples_given') and prefs.get('likes_examples'):
            context_parts.append(f"- Recent example topics: {', '.join(teaching['examples_given'][-2:])}")
        
        return "\n".join(context_parts)
    
    def _build_instructions(self, action: str, prefs: Dict, analysis: Dict, turn: int) -> str:
        """Build specific instructions based on action and preferences."""
        
        instructions = []
        
        # Action-specific instructions
        action_instructions = {
            "diagnostic": "Get to know the student's current understanding and interests.",
            "clarify_confusion": "Ask which specific part confuses them. Be specific in your question.",
            "correct_misconception": "Correct the misconception clearly but gently. Explain why it's incorrect.",
            "provide_example": "Provide a concrete, relevant example. Make it relatable.",
            "address_specific_need": "Address their specific need directly. Break it down.",
            "teach_step_by_step": "Break it down into clear, numbered steps.",
            "review_and_practice": "Review the concept and provide a practice problem.",
            "teach_fundamentals": "Explain the basic concept clearly and simply.",
            "apply_concepts": "Show how to apply the concept to a real problem.",
            "review_assess": "Review what was learned and assess understanding."
        }
        
        if action in action_instructions:
            instructions.append(action_instructions[action])
        
        # Preference-based instructions
        if prefs.get("likes_examples"):
            instructions.append("INCLUDE AT LEAST ONE CONCRETE EXAMPLE.")
        if prefs.get("prefers_short"):
            instructions.append("BE CONCISE - get straight to the point.")
        if prefs.get("needs_repetition"):
            instructions.append("BREAK IT DOWN STEP-BY-STEP.")
        
        # Emotion-based instructions
        if analysis.get("emotional_state") in ["confused", "frustrated"]:
            instructions.append("BE EXTRA PATIENT AND SUPPORTIVE. Validate their feelings.")
        elif analysis.get("emotional_state") == "confident":
            instructions.append("CHALLENGE THEM with a slightly harder question.")
        elif analysis.get("emotional_state") == "bored":
            instructions.append("MAKE IT INTERESTING - use a surprising fact.")
        
        # Turn-based instructions
        if turn == 9:  # Last turn
            instructions.append("PROVIDE FINAL ASSESSMENT and encouragement.")
        
        # Always include
        instructions.append("END WITH A QUESTION to continue the conversation.")
        instructions.append("REFERENCE SOMETHING SPECIFIC from their last response.")
        
        return "IMPORTANT INSTRUCTIONS:\n" + "\n".join([f"- {i}" for i in instructions])
    
    def calculate_understanding_level(self, conversation_id: str) -> int:
        """Calculate final understanding level based on conversation."""
        
        if conversation_id not in self.conversation_memory:
            return 3
        
        memory = self.conversation_memory[conversation_id]
        profile = memory["student_profile"]
        
        # Start with baseline
        score = profile["confidence"]
        
        # Adjust based on progress
        teaching = memory["teaching_progress"]
        if teaching.get("concepts_covered"):
            score += 0.5
        
        if profile.get("strengths"):
            score += 0.3
        
        if profile.get("difficulties"):
            score -= 0.2
        
        # Consider engagement
        history = memory.get("history", [])
        if len(history) > 5:
            # Check if student is asking good questions
            questions = profile.get("questions_asked", [])
            if len(questions) > 2:
                score += 0.4
            
            # Check if misconceptions were corrected
            if profile.get("misconceptions"):
                score += 0.3
        
        # Round and clamp to 1-5
        final_score = round(score)
        final_score = max(1, min(5, final_score))
        
        return final_score

# ------------------- Interactive Session Runner -------------------

def run_interactive_session(student_id: str, topic_id: str, topic_name: str, 
                           grade_level: int = 8, show_details: bool = True) -> Tuple[int, List]:
    """
    Run an interactive 10-turn tutoring session with true conversation flow.
    """
    
    if show_details:
        print(f"\n{'='*80}")
        print(f"INTERACTIVE TUTORING SESSION")
        print(f"Topic: {topic_name} (Grade {grade_level})")
        print(f"AI Provider: {AI_PROVIDER.upper()}")
        print(f"{'='*80}")
    
    # Initialize tutor
    tutor = InteractiveTutor(ai_provider=AI_PROVIDER)
    
    # Start conversation
    try:
        conv_data = start_conversation(student_id, topic_id)
        conversation_id = conv_data["conversation_id"]
        student_response = conv_data.get("student_response", "")
    except Exception as e:
        if show_details:
            print(f"❌ ERROR starting conversation: {e}")
        raise
    
    if show_details:
        print(f"\n[Initial] Student: {student_response}")
    
    conversation_log = []
    
    # Run 10-turn conversation
    for turn in range(10):
        if show_details:
            print(f"\n[Turn {turn + 1}/10]")
            print("-" * 40)
        
        try:
            # Get tutor response
            tutor_response = tutor.get_tutor_response(
                conversation_id, student_response, turn, topic_name, grade_level
            )
            
            if show_details:
                print(f"Tutor: {tutor_response}")
                # Show teaching action
                history = tutor.teaching_history.get(conversation_id, [])
                if history and history[-1]["turn"] == turn:
                    action_display = history[-1]["action"].replace('_', ' ').title()
                    print(f"[Teaching: {action_display}]")
            
            # Get student response (except last turn)
            if turn < 9:
                response_data = interact(conversation_id, tutor_response)
                student_response = response_data.get("student_response", "")
                
                if show_details:
                    print(f"Student: {student_response}")
            
            # Log conversation
            conversation_log.append({
                "turn": turn + 1,
                "tutor": tutor_response,
                "student": student_response if turn < 9 else "N/A"
            })
            
        except Exception as e:
            if show_details:
                print(f"\n❌ ERROR on Turn {turn + 1}: {e}")
                if tutor.ai_errors:
                    print(f"AI Errors: {len(tutor.ai_errors)}")
                    for err in tutor.ai_errors[-2:]:
                        print(f"  {err['provider']}: {err['error'][:80]}")
            raise
    
    # Calculate final understanding
    final_prediction = tutor.calculate_understanding_level(conversation_id)
    
    if show_details:
        print(f"\n{'='*80}")
        print(f"SESSION COMPLETE")
        print(f"{'='*80}")
        
        memory = tutor.conversation_memory.get(conversation_id, {})
        if memory:
            profile = memory["student_profile"]
            print(f"\n📊 Student Profile:")
            print(f"  Confidence: {profile.get('confidence', 3)}/5")
            print(f"  Preferred style: {profile.get('preferred_style', 'unknown')}")
            
            if profile.get('difficulties'):
                print(f"  Key difficulties: {', '.join(profile['difficulties'][:3])}")
            
            if profile.get('strengths'):
                print(f"  Key strengths: {', '.join(profile['strengths'][:3])}")
        
        print(f"\n🎯 Final Prediction: {final_prediction}/5")
        
        # Show AI error summary
        if tutor.ai_errors:
            print(f"\n⚠️ AI Errors: {len(tutor.ai_errors)}")
            for err in tutor.ai_errors:
                print(f"  {err['provider']}: {err['error'][:80]}")
    
    return final_prediction, conversation_log

# ------------------- Data Collection Functions -------------------

def get_all_student_topic_pairs(set_type: str = "mini_dev") -> List[Tuple[str, str, str, int]]:
    """Get ALL student-topic pairs with topic names and grade levels."""
    
    print(f"\n🔍 Collecting ALL student-topic pairs for {set_type} set...")
    
    students_data = get_students(set_type)
    
    # Extract students
    if isinstance(students_data, dict):
        if "students" in students_data:
            students = students_data["students"]
        elif "data" in students_data:
            students = students_data["data"]
        else:
            students = list(students_data.values())
    else:
        students = students_data
    
    print(f"  Found {len(students)} students")
    
    all_pairs = []
    
    for i, student in enumerate(students):
        student_id = student.get("id") or student.get("student_id")
        if not student_id:
            continue
        
        try:
            topics_data = get_students_topics(student_id)
            
            if isinstance(topics_data, dict):
                topics = topics_data.get("topics", [])
            else:
                topics = topics_data
            
            print(f"  Student {i+1}: {len(topics)} topics")
            
            for topic in topics:
                topic_id = topic.get("id")
                topic_name = topic.get("name", "Unknown Topic")
                grade_level = topic.get("grade_level", 8)
                
                if topic_id:
                    all_pairs.append((student_id, topic_id, topic_name, grade_level))
                    
        except Exception as e:
            print(f"  Error getting topics for student {student_id[:8]}: {e}")
    
    print(f"\n✅ Total student-topic pairs to process: {len(all_pairs)}")
    return all_pairs

# ------------------- Configuration Helper -------------------

def setup_environment():
    """Check and setup environment for AI providers."""
    
    print("\n" + "="*80)
    print("AI TUTORING AGENT - Multi-Provider Support")
    print("="*80)
    
    # Check available providers
    print("\n🔍 Checking AI providers...")
    
    providers_available = []
    
    if OPENAI_AVAILABLE and OPENAI_API_KEY:
        providers_available.append("OpenAI")
        print(f"  ✓ OpenAI: Available (key loaded)")
    
    if GEMINI_AVAILABLE and GEMINI_API_KEY:
        providers_available.append("Gemini")
        print(f"  ✓ Gemini: Available (key loaded)")
    
    if not providers_available:
        print("\n❌ No AI providers configured!")
        print("\nTo use OpenAI:")
        print("  1. Get API key from https://platform.openai.com/api-keys")
        print("  2. Add to .env: OPENAI_API_KEY=your_key")
        print("  3. Install: pip install openai")
        
        print("\nTo use Gemini (FREE tier available):")
        print("  1. Get API key from https://makersuite.google.com/app/apikey")
        print("  2. Add to .env: GEMINI_API_KEY=your_key")
        print("  3. Install: pip install google-generativeai")
        
        print("\nIn .env file, also set:")
        print("  AI_PROVIDER=gemini  # or 'openai'")
        print("  AI_MODEL=gemini-1.5-flash  # free model")
        
        exit(1)
    
    print(f"\n✅ Available providers: {', '.join(providers_available)}")
    print(f"📋 Using: {AI_PROVIDER.upper()} with model: {MODEL_NAME}")
    
    return True

# ------------------- Main Execution -------------------

def main():
    """
    Run interactive tutoring sessions for ALL student-topic pairs.
    """
    
    # Setup environment
    setup_environment()
    
    SET_TYPE = "mini_dev"
    
    try:
        # Get ALL student-topic pairs
        all_pairs = get_all_student_topic_pairs(SET_TYPE)
        
        if not all_pairs:
            print("❌ No student-topic pairs found!")
            return
        
        print(f"\n🚀 Starting tutoring sessions for {len(all_pairs)} student-topic pairs...")
        print(f"AI Provider: {AI_PROVIDER.upper()}")
        print(f"Model: {MODEL_NAME}")
        print(f"Each session: 10 turns")
        
        predictions_dict = {}
        successful_sessions = 0
        failed_sessions = 0
        start_time = time.time()
        
        # Process each pair
        for i, (student_id, topic_id, topic_name, grade_level) in enumerate(all_pairs):
            print(f"\n{'='*60}")
            print(f"[Session {i+1}/{len(all_pairs)}]")
            print(f"Student: {student_id[:8]}")
            print(f"Topic: {topic_name} (Grade {grade_level})")
            print(f"{'='*60}")
            
            try:
                # Run the session (show details only for first few)
                show_details = i < 2  # Show full conversation for first 2 sessions
                prediction, conversation_log = run_interactive_session(
                    student_id, topic_id, topic_name, grade_level, show_details=show_details
                )
                
                predictions_dict[(student_id, topic_id)] = prediction
                successful_sessions += 1
                
                print(f"✓ Prediction: {prediction}/5")
                
                # Save conversation log for first 3 sessions
                if i < 3:
                    safe_topic_name = topic_name.replace(' ', '_').replace('/', '_')
                    filename = f"conversation_{student_id[:8]}_{safe_topic_name}.json"
                    with open(filename, "w") as f:
                        json.dump({
                            "student_id": student_id,
                            "topic_id": topic_id,
                            "topic_name": topic_name,
                            "grade_level": grade_level,
                            "prediction": prediction,
                            "conversation": conversation_log
                        }, f, indent=2)
                    print(f"📄 Conversation saved to: {filename}")
                
                # Small delay to avoid rate limiting
                time.sleep(0.3)
                
            except Exception as e:
                failed_sessions += 1
                print(f"❌ Session failed: {str(e)[:80]}...")
                # Default prediction on error
                predictions_dict[(student_id, topic_id)] = 3
        
        elapsed_time = time.time() - start_time
        
        print(f"\n{'='*80}")
        print("ALL SESSIONS COMPLETE")
        print(f"{'='*80}")
        print(f"✅ Successful sessions: {successful_sessions}/{len(all_pairs)}")
        print(f"❌ Failed sessions: {failed_sessions}/{len(all_pairs)}")
        print(f"📊 Total predictions: {len(predictions_dict)}")
        print(f"⏱️  Total time: {elapsed_time:.1f} seconds")
        print(f"⏱️  Average per session: {elapsed_time/len(all_pairs):.1f} seconds")
        
        # Submit predictions for MSE evaluation
        print(f"\n{'='*80}")
        print("SUBMITTING PREDICTIONS FOR MSE EVALUATION")
        print(f"{'='*80}")
        
        if predictions_dict:
            print(f"📤 Submitting {len(predictions_dict)} predictions...")
            try:
                mse_result = submit_mse_predictions(predictions_dict, SET_TYPE)
                
                # Safe printing of results
                print(f"📊 MSE Score: {mse_result.get('mse_score', 'N/A')}")
                print(f"📝 Predictions submitted: {mse_result.get('num_predictions', 'N/A')}")
                
                submission_num = mse_result.get('submission_number')
                if submission_num is not None:
                    print(f"🔄 Submission number: {submission_num}")
                else:
                    print(f"🔄 Submission number: N/A")
                    
                remaining = mse_result.get('submissions_remaining')
                if remaining is not None:
                    print(f"📦 Remaining submissions: {remaining}")
                    
            except Exception as e:
                print(f"❌ MSE Submission Error: {e}")
                print("\nDebug info - prediction dict sample:")
                for key, value in list(predictions_dict.items())[:2]:
                    print(f"  Student: {key[0][:8]}, Topic: {key[1][:8]}, Prediction: {value}")
        
        # Evaluate tutoring quality
        print(f"\n{'='*80}")
        print("EVALUATING TUTORING QUALITY")
        print(f"{'='*80}")
        
        try:
            tutoring_result = evaluate_tutoring(SET_TYPE)
            
            # Safe printing of results
            score = tutoring_result.get('score', 'N/A')
            if isinstance(score, (int, float)):
                print(f"⭐ Tutoring Quality Score: {score:.4f}")
            else:
                print(f"⭐ Tutoring Quality Score: {score}")
                
            print(f"💬 Conversations evaluated: {tutoring_result.get('num_conversations', 'N/A')}")
            
            sub_num = tutoring_result.get('submission_number')
            if sub_num is not None:
                print(f"🔄 Submission number: {sub_num}")
            else:
                print(f"🔄 Submission number: N/A")
                
            remaining = tutoring_result.get('submissions_remaining')
            if remaining is not None:
                print(f"📦 Remaining evaluations: {remaining}")
                
        except Exception as e:
            print(f"❌ Tutoring Evaluation Error: {e}")
        
        # Save comprehensive results
        print(f"\n{'='*80}")
        print("SAVING COMPREHENSIVE RESULTS")
        print(f"{'='*80}")
        
        results_summary = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "ai_provider": AI_PROVIDER,
            "model": MODEL_NAME,
            "set_type": SET_TYPE,
            "total_pairs": len(all_pairs),
            "successful_sessions": successful_sessions,
            "failed_sessions": failed_sessions,
            "total_predictions": len(predictions_dict),
            "total_time_seconds": round(elapsed_time, 1),
            "average_time_per_session": round(elapsed_time/len(all_pairs), 1),
            "predictions": {
                f"{student_id}_{topic_id}": level 
                for (student_id, topic_id), level in predictions_dict.items()
            }
        }
        
        # Add evaluation results if available
        if 'mse_result' in locals():
            results_summary["mse_score"] = mse_result.get('mse_score')
            results_summary["mse_submission_number"] = mse_result.get('submission_number')
            results_summary["mse_submissions_remaining"] = mse_result.get('submissions_remaining')
        
        if 'tutoring_result' in locals():
            results_summary["tutoring_score"] = tutoring_result.get('score')
            results_summary["tutoring_submission_number"] = tutoring_result.get('submission_number')
            results_summary["tutoring_submissions_remaining"] = tutoring_result.get('submissions_remaining')
        
        results_filename = f"tutoring_results_{SET_TYPE}_{int(time.time())}.json"
        with open(results_filename, "w") as f:
            json.dump(results_summary, f, indent=2)
        
        print(f"📄 Complete results saved to: {results_filename}")
        
        # Save predictions in correct format for submission
        predictions_formatted = {
            "predictions": [
                {
                    "student_id": student_id,
                    "topic_id": topic_id,
                    "predicted_level": level
                }
                for (student_id, topic_id), level in predictions_dict.items()
            ],
            "set_type": SET_TYPE
        }
        
        predictions_filename = f"predictions_{SET_TYPE}_{int(time.time())}.json"
        with open(predictions_filename, "w") as f:
            json.dump(predictions_formatted, f, indent=2)
        
        print(f"📄 Predictions in submission format: {predictions_filename}")
        
        print(f"\n{'='*80}")
        print("PROCESS COMPLETE! 🎯")
        print(f"{'='*80}")
        
        print(f"\n📈 FINAL SUMMARY:")
        print(f"  Total student-topic pairs processed: {len(all_pairs)}")
        print(f"  Successful 10-turn conversations: {successful_sessions}")
        print(f"  Failed conversations: {failed_sessions}")
        print(f"  Total time: {elapsed_time:.1f} seconds")
        
        if 'mse_score' in results_summary:
            mse_score = results_summary['mse_score']
            print(f"  📊 MSE Score: {mse_score:.4f} {'(lower is better)' if isinstance(mse_score, (int, float)) else ''}")
            
        if 'tutoring_score' in results_summary:
            tutoring_score = results_summary['tutoring_score']
            print(f"  ⭐ Tutoring Quality: {tutoring_score:.4f} {'(higher is better)' if isinstance(tutoring_score, (int, float)) else ''}")
        
        print(f"\n📁 Files created:")
        print(f"  {results_filename} - Complete results")
        print(f"  {predictions_filename} - Predictions for submission")
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
