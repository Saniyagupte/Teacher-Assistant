import os
import re
import requests
import language_tool_python
import spacy
from flask import Flask, render_template, request, jsonify, session

# Initialize LanguageTool for grammar checking
tool = language_tool_python.LanguageTool('en-US')

# Load spaCy model for similarity
nlp = spacy.load("en_core_web_md")

def preprocess_answer(text):
    """
    Preprocess the answer while keeping original grammar, punctuation, and structure.
    Only removes extra spaces.
    """
    return text.strip()  # Keep everything else intact

def evaluate_clarity(user_answer, model_answer):
    """
    Evaluate clarity by providing feedback based on how well-structured and clear
    the student's answer is compared to the model answer.
    """
    # Calculate the length of both the student and model answers
    clarity_feedback = ""
    clarity_score = 3.0  # Default to neutral score

    if len(user_answer.split()) < len(model_answer.split()):
        clarity_feedback = "Answer is shorter than expected."
        clarity_score = 2.5  # Slightly lower score for shorter answers
    elif len(user_answer.split()) > len(model_answer.split()):
        clarity_feedback = "Answer is longer than expected. Try to be concise."
        clarity_score = 3.5  # Slightly higher score for longer answers, if well-structured
    else:
        clarity_feedback = "Answer length is appropriate."
        clarity_score = 4.0  # For appropriate length answers

    # Assume clarity is around structure and presentation
    return clarity_score, clarity_feedback

def evaluate_length(user_answer, model_answer):
    """
    Checks if the student's answer length is within a reasonable range compared to the model answer.
    If the deviation is greater than 10%, apply a penalty.
    """
    ideal_length = len(model_answer.split())
    user_length = len(user_answer.split())
    length_penalty = 0

    if abs(ideal_length - user_length) > ideal_length * 0.1:  # If deviation >10%
        length_penalty = abs(ideal_length - user_length) * 0.2  # Apply penalty

    return length_penalty, f"Ideal length: {ideal_length} words. Student's answer: {user_length} words."

def evaluate_accuracy(user_answer, model_answer):
    """
    Compares the student's answer with the model answer using semantic similarity (using spaCy).
    """
    # Create spaCy Doc objects for both model and user answers
    model_doc = nlp(model_answer)
    user_doc = nlp(user_answer)

    # Compute the cosine similarity between the two answers
    similarity_score = model_doc.similarity(user_doc)

    # Assign score and explanation based on the similarity score
    if similarity_score >= 0.9:
        accuracy_score = 1.0
        accuracy_feedback = "The answers are identical in meaning."
    elif similarity_score >= 0.8:
        accuracy_score = 0.8
        accuracy_feedback = "Minor differences, but meaning is preserved."
    elif similarity_score >= 0.6:
        accuracy_score = 0.6
        accuracy_feedback = "Some differences, but still mostly correct."
    elif similarity_score >= 0.3:
        accuracy_score = 0.3
        accuracy_feedback = "Significant deviation in meaning."
    else:
        accuracy_score = 0.0
        accuracy_feedback = "Completely incorrect answer."

    return accuracy_score, accuracy_feedback

def grammar_score(user_answer):
    """
    Checks grammar mistakes and applies a penalty of -0.2 per mistake.
    Returns the total penalty and a list of grammar errors as strings.
    """
    matches = tool.check(user_answer)
    penalty = len(matches) * 0.2  # Deduct 0.2 per mistake

    # Collect grammar errors as strings for serialization
    error_messages = [match.message for match in matches]
    
    return penalty, error_messages

def evaluate_answer(model_answer, user_answer):
    model_answer = preprocess_answer(model_answer)
    user_answer = preprocess_answer(user_answer)

    # Evaluate clarity
    clarity_score, clarity_feedback = evaluate_clarity(user_answer, model_answer)

    # Evaluate length
    length_penalty, length_feedback = evaluate_length(user_answer, model_answer)

    # Evaluate accuracy
    accuracy_score, accuracy_feedback = evaluate_accuracy(user_answer, model_answer)

    # Compute grammar penalty
    grammar_penalty, grammar_matches = grammar_score(user_answer)

    # Final score calculation (out of 8)
    final_score = 8 - grammar_penalty - length_penalty
    final_score = max(0, round(final_score, 2))  # Ensure score is non-negative

    # Feedback report
    feedback = {
        "clarity_feedback": f"Clarity Score: {clarity_score}/5 | {clarity_feedback}",
        "length_feedback": length_feedback,
        "accuracy_feedback": accuracy_feedback,
        "grammar_feedback": f"Grammar penalty: {grammar_penalty:.2f}. Errors: {len(grammar_matches)}.",
        "final_score_feedback": f"Final score (out of 8): {final_score:.2f}",
        "grammar_matches": grammar_matches
    }

    return final_score, feedback

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'saniya124'  # Set your secret key for sessions

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit_teacher', methods=['POST'])
def submit_teacher():
    question_1 = request.form['question_1']
    answer_1 = request.form['answer_1']
    question_2 = request.form['question_2']
    answer_2 = request.form['answer_2']

    # Store teacher's answers in session (or database)
    session['teacher_answers'] = {
        'question_1': question_1,
        'answer_1': answer_1,
        'question_2': question_2,
        'answer_2': answer_2
    }

    return jsonify({"status": "success", "message": "Teacher answers saved successfully!"})

@app.route('/submit_student', methods=['POST'])
def submit_student():
    try:
        student_answer_1 = request.form['answer_1']
        student_answer_2 = request.form['answer_2']

        # Retrieve model answers from session (or database)
        model_answers = session.get('teacher_answers')

        if not model_answers:
            return jsonify({"status": "error", "message": "Model answers not provided yet!"})

        model_answer_1 = model_answers.get('answer_1')
        model_answer_2 = model_answers.get('answer_2')

        # Evaluate the answers
        score_1, feedback_1 = evaluate_answer(model_answer_1, student_answer_1)
        score_2, feedback_2 = evaluate_answer(model_answer_2, student_answer_2)

        results = {
            "question_1": {
                "feedback": feedback_1,
                "score": score_1,
            },
            "question_2": {
                "feedback": feedback_2,
                "score": score_2,
            }
        }

        return jsonify({"status": "success", "results": results})

    except Exception as e:
        print(f"Error in /submit_student: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred."})

if __name__ == "__main__":
    app.run(debug=True)
