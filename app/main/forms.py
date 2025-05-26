from django import forms
from django.contrib.auth.models import User
import re


class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль")

    class Meta:
        model = User
        fields = ['username', 'password']

    def clean_password(self):
        password = self.cleaned_data.get('password')

        # Перевірка довжини
        if len(password) < 8:
            raise forms.ValidationError("Пароль має бути довжиною мінімум 8 символів.")

        # Перевірка категорій
        has_letters = bool(re.search(r'[a-zA-Z]', password))  # Латинські літери
        has_digits = bool(re.search(r'\d', password))  # Цифри
        special_chars = re.findall(r'[^a-zA-Z0-9]', password)  # Спеціальні символи
        has_special = len(special_chars) > 0
        special_count = len(special_chars)

        # Перевірка кількості спеціальних символів
        if special_count > 1:
            raise forms.ValidationError("Пароль може містити не більше одного спеціального символу.")

        # Перевірка на наявність принаймні 2 з 3 категорій
        categories_present = sum([has_letters, has_digits, has_special])
        if categories_present < 2:
            raise forms.ValidationError(
                "Пароль має містити принаймні 2 з 3 категорій: латинські літери, цифри, спеціальний символ.")

        return password

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Користувач з таким ім'ям уже існує.")
        return username