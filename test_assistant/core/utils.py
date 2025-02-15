import google.generativeai as genai
from django.conf import settings
from .models import Exam, Question
import json

# Configure the API key
genai.configure(api_key=settings.GENAI_API_KEY)  # Use your actual API key from Django settings

# Create a model object
model = genai.GenerativeModel("gemini-1.5-flash")

def generate_questions(prompt, number_of_questions=5):
    try:
        # Generate questions with the model
        response = model.generate_content(prompt)
        generated_text = response.text
        
        print("\n-------------------------------------------------------------\n")
        print("Model Response:\n", generated_text)

        # Process the response and extract structured questions
        questions = process_generated_text(generated_text, number_of_questions)
        return questions
    except Exception as e:
        print(f"An error occurred while generating questions: {e}")
        return []

def process_generated_text(text, number_of_questions):
    """
    Extracts and processes the JSON response from the AI model.
    Ensures that extra text (like ```json) is removed before parsing.
    """
    try:
        # Find the first occurrence of '{' to remove unwanted text like ```json
        json_start = text.find("{")
        if json_start == -1:
            raise ValueError("No JSON object found in the model response.")

        # Find the last '}' to remove any unwanted suffix (e.g., trailing ```)
        json_end = text.rfind("}")
        if json_end == -1:
            raise ValueError("Invalid JSON format: Missing closing '}'.")

        # Extract only the valid JSON part
        json_text = text[json_start:json_end + 1]  # Include the closing '}'

        # Parse JSON safely
        response_data = json.loads(json_text)

        

        # Validate if 'questions' key exists in response
        if 'questions' not in response_data:
            raise ValueError("'questions' key not found in the response.")

        # Get the requested number of questions
        questions = response_data['questions'][:number_of_questions]

        # Log a warning if fewer questions are generated
        if len(questions) < number_of_questions:
            print(f"⚠ Warning: Only {len(questions)} questions were generated, but {number_of_questions} were requested.")

        return questions
    except json.JSONDecodeError as e:
        print(f"JSON decoding error: {e}")
        return []
    except ValueError as e:
        print(f"Error processing JSON response: {e}")
        return []

def store_generated_questions(exam, questions):
    """
    Stores generated questions and answers in the database.
    Each question is linked to the Exam model.
    """
    for question_data in questions:
        try:
            Question.objects.create(
                exam=exam,
                text=question_data.get('question', 'Unknown Question'),
                question_type=question_data.get('type', 'Short Answer'),  # Default type; can be extended
                correct_answer=question_data.get('correct_answer', 'N/A'),
                marks=question_data.get('marks', 1),  # Default to 1 mark
                options=json.dumps(question_data.get('options', []))  # Store options as JSON
            )
        except Exception as e:
            print(f"Error saving question to DB: {e}")
