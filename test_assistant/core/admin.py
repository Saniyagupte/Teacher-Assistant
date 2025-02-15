from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Exam, Question, StudentExamAttempt, Answer, Feedback, Group, GroupMember

# Customizing the User model in admin panel
# class CustomUserAdmin(UserAdmin):
#     model = User
#     list_display = ('username', 'name', 'email', 'role', 'is_active', 'is_staff')
#     list_filter = ('role', 'is_staff', 'is_superuser')
#     fieldsets = (
#         (None, {'fields': ('username', 'password')}),
#         ('Personal Info', {'fields': ('name', 'email', 'role')}),
#         ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
#         ('Important Dates', {'fields': ('last_login', 'date_joined')}),
#     )
#     search_fields = ('username', 'name', 'email')
#     ordering = ('username',)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    pass

# Registering models
# admin.site.register(User, CustomUserAdmin)
admin.site.register(Exam)
admin.site.register(Question)
admin.site.register(StudentExamAttempt)
admin.site.register(Answer)
admin.site.register(Feedback)
admin.site.register(Group)
admin.site.register(GroupMember)
