# # core/forms.py
# from django import forms

# class QuestionGenerationForm(forms.Form):
#     subject = forms.CharField(max_length=100)
#     topic = forms.CharField(max_length=100)
#     question_type = forms.ChoiceField(choices=[('MCQ', 'MCQ'), ('Short Answer', 'Short Answer'), ('Long Answer', 'Long Answer')])
#     number_of_questions = forms.IntegerField(min_value=1, max_value=10)  # Limit to 10 for example

from django import forms

from django.contrib.auth.forms import UserCreationForm
from  .models import User , Question

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class QuestionGenerationForm(forms.Form):
    subject = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    topic = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    question_type = forms.ChoiceField(
        choices=[('MCQ', 'MCQ'), ('Short Answer', 'Short Answer'), ('Long Answer', 'Long Answer')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    num_questions = forms.IntegerField(
        min_value=1, max_value=10,  # Ensure it’s between 1 and 10
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )



class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'correct_answer', 'question_type', 'options']
