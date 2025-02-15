# core/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import QuestionGenerationForm
from .utils import generate_questions, store_generated_questions
from django.contrib.auth.decorators import login_required
import json
from .models import Exam, Question, StudentExamAttempt, Answer, Feedback
import google.generativeai as genai
from django.conf import settings

from .forms import UserRegistrationForm, QuestionForm 
from django.contrib.auth import login
from django.contrib.auth import get_user_model
User = get_user_model()  # Get the custom User model



# Configure AI Model
genai.configure(api_key=settings.GENAI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

def index(request):
    return render(request, 'core/index.html')

# @login_required
def generate_exam_questions(request):
    if request.method == 'POST':
        form = QuestionGenerationForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            topic = form.cleaned_data['topic']
            question_type = form.cleaned_data['question_type']
            number_of_questions = form.cleaned_data['num_questions']
            
            print("\n-------------------------------------------------------------\n")
            print("")
            print(request.user)
            
            print("Generating questions for: ",subject, topic, question_type, number_of_questions)

            # Create a new exam entry
            exam = Exam.objects.create(
                title=f"{subject} - {topic}",
                subject=subject,
                topic=topic,
                type=question_type,
                created_by=request.user
            )
            
            
            # Create a prompt for AI based on user input
            prompt = (f"Generate {number_of_questions} {question_type} questions on the topic of {topic} in the subject {subject}. "
            "For each question, include the following details: "
            "1. The question text. "
            "2. The correct answer. "
            "3. For MCQs, provide a list of options (at least 4 options). "
            "Output the results in the following JSON format:\n"
            "{\n"
            "  \"questions\": [\n"
            "    {\n"
            "      \"question\": \"[Question Text]\",\n"
            "      \"correct_answer\": \"[Correct Answer]\",\n"
            "      \"options\": [\"[Option 1]\", \"[Option 2]\", \"[Option 3]\", \"[Option 4]\"]\n"
            "      \"type\": \"[MCQ or Short Answer or Long Answer]\",\n"
            "    },\n"
            "    ...\n"
            "  ]\n"
            "}\n"
            "Make sure to format the answer as JSON with no extra text, and ensure the questions are varied in difficulty."
            )

# Generate the questions based on the updated prompt
            questions = generate_questions(prompt, number_of_questions)


            print("\n-------------------------------------------------------------\n")
            print("Generated questions: ",questions)
            
            # Store the questions in the database
            store_generated_questions(exam, questions)
            
            messages.success(request, f"Exam questions for {subject} - {topic} have been generated successfully!")
            return redirect('exam_detail', exam_id=exam.id)
    else:
        form = QuestionGenerationForm()
    
    return render(request, 'core/generate_exam_questions.html', {'form': form})



# @login_required

def exam_detail(request, exam_id):
    # Retrieve the exam object
    exam = get_object_or_404(Exam, id=exam_id)

    # Retrieve all questions for the exam
    questions = exam.questions.all()

    # Decode the options from JSON string to Python list
    for question in questions:
        if isinstance(question.options, str):
            try:
                # Convert the JSON string into a Python list
                question.options = json.loads(question.options)
            except json.JSONDecodeError:
                # Handle error if decoding fails (optional)
                question.options = []

    
    return render(request, 'core/exam_detail.html', {'exam': exam, 'questions': questions})


@login_required
def take_exam(request, exam_id):
    """
    View for students to take an exam
    """
    exam = get_object_or_404(Exam, id=exam_id)
    questions = exam.questions.all()
    
    # Convert JSON field to list before passing to the template
    for question in questions:
        if question.options:  
            question.options = json.loads(question.options)  # Convert JSON to list

    # Ensure only students can attempt
    if request.user.role != "Student":
        return redirect('index')

    if request.method == "POST":
        # Create an exam attempt
        attempt = StudentExamAttempt.objects.create(student=request.user, exam=exam)

        # Collect student responses
        student_answers = []
        for question in questions:
            student_response = request.POST.get(f'question_{question.id}', '').strip()
            student_answers.append((question, student_response))

        # AI-based evaluation for non-MCQ answers (batch processing)
        if question.question_type == "MCQ":
            marks_and_correctness = [(q.marks if s.lower() == q.correct_answer.strip().lower() else 0, s.lower() == q.correct_answer.strip().lower()) for q, s in student_answers]
        else:
            marks_and_correctness = evaluate_with_ai(student_answers)

        # Save student answers
        for i, (question, student_response) in enumerate(student_answers):
            obtained_marks, is_correct = marks_and_correctness[i]

            Answer.objects.create(
                attempt=attempt,
                question=question,
                student_response=student_response,
                is_correct=is_correct,
                obtained_marks=obtained_marks
            )

        # Redirect to result page
        return redirect('exam_result', attempt_id=attempt.id)

    return render(request, "core/take_exam.html", {"exam": exam, "questions": questions})

def evaluate_with_ai(student_answers):
    """
    Uses AI to evaluate all answers at once by comparing them with the correct answers.
    Returns: List of (marks_obtained, is_correct) tuples.
    """
    prompt = """
    Evaluate the following student answers.Assign marks **out of the maximum marks** specified for each question.

    Return output in a single JSON array like this:
    [
        {"score": <marks_obtained>, "is_correct": <true/false>},
        {"score": <marks_obtained>, "is_correct": <true/false>},
        ...
    ]

    Do NOT add any extra text or explanations, only return the JSON array.

    Now evaluate the following answers:
    """

    # Build structured input for AI
    for question, student_response in student_answers:
        prompt += f"""
        {{
            "question": "{question.text}",
            "ideal_answer": "{question.correct_answer}",
            "student_answer": "{student_response}",
            "max_marks": {question.marks}
        }},
        """

    print(f"\n[AI EVALUATION] Sending prompt to AI:\n{prompt}\n")  # Debugging print

    try:
        response_text = model.generate_content(prompt).text
        print(f"\n[AI RESPONSE] Received:\n{response_text}\n")  # Debugging print

        if not response_text:
            raise ValueError("No response received from AI")

        # Extract only the valid JSON part
        json_start = response_text.find("[")
        json_end = response_text.rfind("]")
        if json_start == -1 or json_end == -1:
            raise ValueError("Invalid JSON format received from AI.")

        json_text = response_text[json_start:json_end + 1]  # Extract only JSON array

        print(f"[AI DEBUG] Extracted JSON Array:\n{json_text}\n")  # Debugging print

        response_data = json.loads(json_text)  # Convert AI output to Python list

        # Ensure AI returned the correct number of results
        if len(response_data) != len(student_answers):
            raise ValueError(f"AI returned {len(response_data)} results, expected {len(student_answers)}")

        return [(item.get("score", 0), item.get("is_correct", False)) for item in response_data]

    except json.JSONDecodeError as e:
        print(f"\n[AI ERROR] JSON Decoding Error: {e}")
    except ValueError as e:
        print(f"\n[AI ERROR] {e}")
    except Exception as e:
        print(f"\n[AI ERROR] Unexpected error: {e}")

    return [(0, False)] * len(student_answers)  # Default to 0 marks if AI fails


@login_required
def exam_result(request, attempt_id):
    """
    View to show exam results and provide AI-generated feedback
    """
    attempt = get_object_or_404(StudentExamAttempt, id=attempt_id, student=request.user)
    answers = attempt.answers.all()

    total_score = sum(answer.obtained_marks for answer in answers)
    attempt.score = total_score
    attempt.save(update_fields=['score'])  # Update only the score field

    # AI feedback text generation
    try:
        feedback_object = Feedback.objects.get(student=request.user, exam=attempt.exam)
    except Feedback.DoesNotExist:
        feedback_text = generate_feedback(answers)
        Feedback.objects.create(
            student=request.user,
            exam=attempt.exam,
            improvement_suggestions=feedback_text,
            recommended_links=["https://www.khanacademy.org/", "https://www.youtube.com/educational_videos"]
        )
    else:
        feedback_text = feedback_object.improvement_suggestions

    return render(request, "core/exam_result.html", {"attempt": attempt, "answers": answers, "feedback": feedback_text})


def generate_feedback(answers):
    """
    AI-generated personalized feedback based on student answers
    """
    prompt = "Generate concise feedback (4-10 lines) for a student based on their performance:\n\n"
    
    for ans in answers:
        prompt += f"Question: {ans.question.text}\nStudent Answer: {ans.student_response}\nCorrect Answer: {ans.question.correct_answer}\n\n"

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"AI Feedback Error: {e}")
        return "Improve by revising the key concepts from your textbook or online resources."

def register(request):
    if (request.method=='POST'):
        form = UserRegistrationForm(request.POST)
        if form.is_valid() :
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password1'])
            user.save()
            login(request, user)
            return redirect('index')
        
    else:
        form = UserRegistrationForm()

    return render(request, 'registration/register.html', {'form': form})

@login_required
def my_exams(request):
    exams = Exam.objects.filter(created_by=request.user)

    # Check if the logged-in user has attempted each exam
    for exam in exams:
        attempt = StudentExamAttempt.objects.filter(student=request.user, exam=exam).first()
        exam.is_taken = bool(attempt)  # Add a flag to indicate whether the student has taken the exam
    
    return render(request, 'core/my_exams.html', {'exams': exams})

from .models import Question
from .forms import QuestionForm  # Assuming you have a form for editing questions

@login_required
def edit_question(request, question_id):
    question = get_object_or_404(Question, id=question_id)

    # Only allow teachers to edit questions
    # if not request.user.is_teacher:
    #     return redirect('exam_detail', question.exam.id)

    if request.method == "POST":
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():

            form.save()
            return redirect('exam_detail', question.exam.id)
    else:
        form = QuestionForm(instance=question)

    return render(request, 'core/edit_question.html', {'form': form, 'question': question})


### app.py logic -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------




# import re
# import requests
# import language_tool_python
# import spacy

# # Initialize LanguageTool for grammar checking
# tool = language_tool_python.LanguageTool('en-US')

# # Load spaCy model for similarity
# nlp = spacy.load("en_core_web_md")

# def preprocess_answer(text):
#     """
#     Preprocess the answer while keeping original grammar, punctuation, and structure.
#     Only removes extra spaces.
#     """
#     return text.strip()  # Keep everything else intact

# def evaluate_clarity(user_answer, model_answer):
#     """
#     Evaluate clarity by providing feedback based on how well-structured and clear
#     the student's answer is compared to the model answer.
#     """
#     # Calculate the length of both the student and model answers
#     clarity_feedback = ""
#     clarity_score = 3.0  # Default to neutral score

#     if len(user_answer.split()) < len(model_answer.split()):
#         clarity_feedback = "Answer is shorter than expected."
#         clarity_score = 2.5  # Slightly lower score for shorter answers
#     elif len(user_answer.split()) > len(model_answer.split()):
#         clarity_feedback = "Answer is longer than expected. Try to be concise."
#         clarity_score = 3.5  # Slightly higher score for longer answers, if well-structured
#     else:
#         clarity_feedback = "Answer length is appropriate."
#         clarity_score = 4.0  # For appropriate length answers

#     # Assume clarity is around structure and presentation
#     return clarity_score, clarity_feedback

# def evaluate_length(user_answer, model_answer):
#     """
#     Checks if the student's answer length is within a reasonable range compared to the model answer.
#     If the deviation is greater than 10%, apply a penalty.
#     """
#     ideal_length = len(model_answer.split())
#     user_length = len(user_answer.split())
#     length_penalty = 0

#     if abs(ideal_length - user_length) > ideal_length * 0.1:  # If deviation >10%
#         length_penalty = abs(ideal_length - user_length) * 0.2  # Apply penalty

#     return length_penalty, f"Ideal length: {ideal_length} words. Student's answer: {user_length} words."

# def evaluate_accuracy(user_answer, model_answer):
#     """
#     Compares the student's answer with the model answer using semantic similarity (using spaCy).
#     """
#     # Create spaCy Doc objects for both model and user answers
#     model_doc = nlp(model_answer)
#     user_doc = nlp(user_answer)

#     # Compute the cosine similarity between the two answers
#     similarity_score = model_doc.similarity(user_doc)

#     # Assign score and explanation based on the similarity score
#     if similarity_score >= 0.9:
#         accuracy_score = 1.0
#         accuracy_feedback = "The answers are identical in meaning."
#     elif similarity_score >= 0.8:
#         accuracy_score = 0.8
#         accuracy_feedback = "Minor differences, but meaning is preserved."
#     elif similarity_score >= 0.6:
#         accuracy_score = 0.6
#         accuracy_feedback = "Some differences, but still mostly correct."
#     elif similarity_score >= 0.3:
#         accuracy_score = 0.3
#         accuracy_feedback = "Significant deviation in meaning."
#     else:
#         accuracy_score = 0.0
#         accuracy_feedback = "Completely incorrect answer."

#     return accuracy_score, accuracy_feedback

# def grammar_score(user_answer):
#     """
#     Checks grammar mistakes and applies a penalty of -0.2 per mistake.
#     Returns the total penalty and a list of grammar errors as strings.
#     """
#     matches = tool.check(user_answer)
#     penalty = len(matches) * 0.2  # Deduct 0.2 per mistake

#     # Collect grammar errors as strings for serialization
#     error_messages = [match.message for match in matches]
    
#     return penalty, error_messages

# def evaluate_answer(model_answer, user_answer):
#     model_answer = preprocess_answer(model_answer)
#     user_answer = preprocess_answer(user_answer)

#     # Evaluate clarity
#     clarity_score, clarity_feedback = evaluate_clarity(user_answer, model_answer)

#     # Evaluate length
#     length_penalty, length_feedback = evaluate_length(user_answer, model_answer)

#     # Evaluate accuracy
#     accuracy_score, accuracy_feedback = evaluate_accuracy(user_answer, model_answer)

#     # Compute grammar penalty
#     grammar_penalty, grammar_matches = grammar_score(user_answer)

#     # Final score calculation (out of 8)
#     final_score = 8 - grammar_penalty - length_penalty
#     final_score = max(0, round(final_score, 2))  # Ensure score is non-negative

#     # Feedback report
#     feedback = {
#         "clarity_feedback": f"Clarity Score: {clarity_score}/5 | {clarity_feedback}",
#         "length_feedback": length_feedback,
#         "accuracy_feedback": accuracy_feedback,
#         "grammar_feedback": f"Grammar penalty: {grammar_penalty:.2f}. Errors: {len(grammar_matches)}.",
#         "final_score_feedback": f"Final score (out of 8): {final_score:.2f}",
#         "grammar_matches": grammar_matches
#     }

#     return final_score, feedback
