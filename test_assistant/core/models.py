from django.db import models
from django.contrib.auth.models import AbstractUser

# Custom User Model (Handles both teachers & students)
from django.contrib.auth.models import AbstractUser, Group, Permission

class User(AbstractUser):
    ROLE_CHOICES = (
        ('Teacher', 'Teacher'),
        ('Student', 'Student'),
    )
    name = models.CharField(max_length=255)
    # email = models.EmailField(unique=False)
    # password = models.CharField(max_length=255)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='Student')
    created_at = models.DateTimeField(auto_now_add=True)

    # Prevent conflicts with Django's built-in auth system
    groups = models.ManyToManyField(Group, related_name="custom_user_groups", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="custom_user_permissions", blank=True)

    def __str__(self):
        return f"{self.name} ({self.role})"

# Exam Model (Created by Teachers)
class Exam(models.Model):
    QUESTION_TYPE_CHOICES = (
        ('MCQ', 'MCQ'),
        ('Short Answer', 'Short Answer'),
        ('Long Answer', 'Long Answer'),
    )

    title = models.CharField(max_length=255)
    subject = models.CharField(max_length=100)
    topic = models.CharField(max_length=100)
    type = models.CharField(max_length=15, choices=QUESTION_TYPE_CHOICES)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'Teacher'})
    created_at = models.DateTimeField(auto_now_add=True)

    # Reverse relation to StudentExamAttempt
    def attempts(self):
        return self.studentexamattempt_set.all()
    def __str__(self):
        return self.title

# Question Model (Linked to Exam)
class Question(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    question_type = models.CharField(max_length=20, choices=Exam.QUESTION_TYPE_CHOICES)
    options = models.JSONField(blank=True, null=True)  # Only for MCQ
    correct_answer = models.TextField()
    marks = models.FloatField(default=1.0)

    def __str__(self):
        return self.text[:50]

# Student Exam Attempt Model (Stores exam attempts)
class StudentExamAttempt(models.Model):
    student = models.ForeignKey(User,on_delete=models.CASCADE, limit_choices_to={'role': 'Student'})
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    score = models.FloatField(default=0.0)
    attempt_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.name} - {self.exam.title} - {self.score}"

# Answer Model (Stores individual student answers)
class Answer(models.Model):
    attempt = models.ForeignKey(StudentExamAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    student_response = models.TextField()
    is_correct = models.BooleanField(default=False)
    obtained_marks = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.attempt.student.name} - {self.question.text[:30]}"

# AI Feedback Model
class Feedback(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'Student'})
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    improvement_suggestions = models.TextField()
    recommended_links = models.JSONField(blank=True, null=True)  # Stores video links, articles, etc.
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for {self.student.name} on {self.exam.title}"

# Group Model (For study groups)
class Group(models.Model):
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'Teacher'})
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# Group Members Model (Mapping students to groups)
class GroupMember(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'Student'})

    def __str__(self):
        return f"{self.student.name} in {self.group.name}"
