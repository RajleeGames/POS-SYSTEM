# accounts/forms.py
from django import forms
from .models import UserProfile  # Assuming you are using a UserProfile model

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['profile_picture', 'bio']  # Add any fields you need
