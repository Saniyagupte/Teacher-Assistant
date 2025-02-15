# core/urls.py
from django.urls import path
from . import views
from django.contrib import admin

urlpatterns = [
    path('generate_exam_questions/', views.generate_exam_questions, name='generate_exam_questions'),
    path('exam/<int:exam_id>/', views.exam_detail, name='exam_detail'),
    path('take_exam/<int:exam_id>/', views.take_exam, name='take_exam'),
    path('exam_result/<int:attempt_id>/', views.exam_result, name='exam_result'),

    path('', views.index, name='index'),
    path('admin/', admin.site.urls),

    path('my_exams/', views.my_exams, name='my_exams'),
    path('edit_question/<int:question_id>/', views.edit_question, name='edit_question'),
]

