import os
import json
from django.shortcuts import render
from groq import Groq
from dotenv import load_dotenv

# Load API key from .env
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Check if API key is loaded
if not GROQ_API_KEY:
    print("Warning: GROQ_API_KEY not found in .env file. Please add it to your .env file.")

# Initialize Groq client only if API key exists
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

def parse_ai_response(ai_output):
    """Parse AI response and extract JSON, handling various formats."""
    try:
        # Clean the response - remove markdown code blocks if present
        content = ai_output.strip()
        
        # Remove JSON code blocks
        if content.startswith("```json"):
            content = content[7:-3].strip()  # Remove ```json and ```
        elif content.startswith("```"):
            content = content[3:-3].strip()  # Remove ``` and ```
        
        # Parse JSON
        parsed_data = json.loads(content)
        
        # Ensure all expected keys exist with proper defaults
        expected_keys = ["syntax_errors", "logical_errors", "key_improvements", "fixed_code", "explanation"]
        for key in expected_keys:
            if key not in parsed_data:
                parsed_data[key] = [] if "errors" in key or "improvements" in key else ""
        
        return parsed_data
        
    except json.JSONDecodeError as e:
        # Return error structure if JSON parsing fails
        return {
            "error": f"Failed to parse AI response as JSON: {str(e)}",
            "raw": ai_output,
            "syntax_errors": [],
            "logical_errors": [],
            "key_improvements": [],
            "fixed_code": "",
            "explanation": ""
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "raw": ai_output,
            "syntax_errors": [],
            "logical_errors": [],
            "key_improvements": [],
            "fixed_code": "",
            "explanation": ""
        }

def home(request):
    context = {
        "user_code": "",
        "ai_result": None,
        "error": None,
        "debug": None
    }
    
    if request.method == "POST":
        # Get user code from form
        user_code = request.POST.get("code", "").strip()
        context["user_code"] = user_code
        
        # Validate input
        if not user_code:
            context["error"] = "❌ Please enter some code to review."
        elif not GROQ_API_KEY or not client:
            context["error"] = "❌ API key not configured. Please check your .env file."
        else:
            try:
                # Prepare optimized prompt for better JSON response
                prompt = f"""You are an expert code reviewer. Analyze the following code and provide feedback in STRICT JSON format.

IMPORTANT: Return ONLY valid JSON with these exact keys:
- syntax_errors (array of strings)
- logical_errors (array of strings) 
- key_improvements (array of strings)
- fixed_code (string with corrected code)
- explanation (string with detailed explanation)

Code to review:

{user_code}

Return JSON in this exact format (no additional text):
{{
  "syntax_errors": ["error1", "error2", ...],
  "logical_errors": ["error1", "error2", ...],
  "key_improvements": ["improvement1", "improvement2", ...],
  "fixed_code": "corrected code here",
  "explanation": "detailed explanation here"
}}"""


                # Call Groq API
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {
                            "role": "system", 
                            "content": "You are an expert code reviewer specializing in Python, JavaScript, Java, C++, and other programming languages. Always return valid JSON format without any additional text or markdown formatting."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,  # Lower temperature for more consistent JSON
                    max_tokens=2000,
                    top_p=0.9
                )

                # Extract AI response
                ai_output = response.choices[0].message.content
                
                # Parse the response
                ai_result = parse_ai_response(ai_output)
                context["ai_result"] = ai_result
                
                # If there was a parsing error, add to context
                if "error" in ai_result and ai_result["error"]:
                    context["error"] = ai_result["error"]
                    
            except Exception as e:
                # Handle API errors
                import traceback
                context["error"] = f"❌ API Error: {str(e)}"
                context["debug"] = traceback.format_exc()
                
                # Provide a fallback result structure
                context["ai_result"] = {
                    "error": f"API Error: {str(e)}",
                    "raw": "Unable to get AI response.",
                    "syntax_errors": [],
                    "logical_errors": [],
                    "key_improvements": [],
                    "fixed_code": "",
                    "explanation": ""
                }
    
    # GET request or after POST processing → render template
    return render(request, "home.html", context)


# Optional: Add a health check endpoint
def health_check(request):
    """Check if the API is working."""
    if not GROQ_API_KEY:
        return render(request, "error.html", {
            "error": "API Key not configured"
        })
    
    try:
        # Simple test call
        client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "Say 'OK'"}],
            max_tokens=10
        )
        return render(request, "health.html", {"status": "healthy"})
    except Exception as e:
        return render(request, "error.html", {"error": str(e)})