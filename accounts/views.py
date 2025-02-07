# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages

from .forms import ProfileUpdateForm

from .models import UserProfile  # If you have a UserProfile model for additional fields

@login_required
def account_settings_view(request):
    if request.method == 'POST':
        profile = request.user.profile  # If the signal worked, this should exist
        # Handle profile update
        if 'username' in request.POST and 'email' in request.POST:
            # Save new profile data (username, email, profile picture)
            user = request.user
            user.username = request.POST['username']
            user.email = request.POST['email']
            if 'profile_picture' in request.FILES:
                user.profile.profile_picture = request.FILES['profile_picture']  # Assuming a user profile model exists
            user.save()
            messages.success(request, 'Profile updated successfully!')

        # Handle password change
        elif 'current_password' in request.POST:
            form = PasswordChangeForm(user=request.user, data=request.POST)
            if form.is_valid():
                form.save()
                update_session_auth_hash(request, form.user)  # To prevent logout after password change
                messages.success(request, 'Password changed successfully!')
            else:
                messages.error(request, 'Error changing password. Please try again.')

        # Handle email notification preferences
        elif 'email_notifications' in request.POST:
            user_profile = request.user.profile
            user_profile.email_notifications = request.POST['email_notifications']
            user_profile.save()
            messages.success(request, 'Email notifications preference saved!')

        # Handle account deactivation
        elif 'deactivate' in request.POST:
            user = request.user
            user.is_active = False
            user.save()
            messages.success(request, 'Your account has been deactivated.')
            return redirect('home')  # Redirect to the home page after deactivation

    return render(request, 'pos/account_settings.html')




def profile_update_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user.profile)
    return render(request, 'pos/account_settings.html', {'form': form})


@login_required
def profile_view(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    # 'created' is a boolean indicating whether a new profile was created.
    return render(request, 'pos/profile.html', {'profile': profile})
