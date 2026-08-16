from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

from .models import User


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'field-input', 'placeholder': 'you@example.com', 'autofocus': True})
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'field-input', 'placeholder': 'Your name'})
    )
    company_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'field-input', 'placeholder': 'Studio / company (optional)'}),
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'company_name', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'field-input', 'placeholder': 'Create a password'})
        self.fields['password2'].widget.attrs.update({'class': 'field-input', 'placeholder': 'Confirm password'})

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email


class SignInForm(AuthenticationForm):
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'class': 'field-input', 'placeholder': 'you@example.com', 'autofocus': True}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'field-input', 'placeholder': 'Password'})
    )
