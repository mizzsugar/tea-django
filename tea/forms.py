from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import TeaReview


# カスタムUserモデルを取得
User = get_user_model()


class GeneralUserRegistrationForm(UserCreationForm):
    """一般ユーザー登録フォーム（usernameなし）"""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'メールアドレス'
        })
    )
    
    nickname = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ニックネーム'
        })
    )
    
    password1 = forms.CharField(
        label="パスワード",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'パスワード'
        })
    )
    
    password2 = forms.CharField(
        label="パスワード（確認）",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'パスワード（確認）'
        })
    )
    
    class Meta:
        model = User
        fields = ['email', 'nickname', 'password1', 'password2']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.nickname = self.cleaned_data['nickname']
        # 一般ユーザーなのでusernameは自動生成される
        user.is_staff = False
        user.is_superuser = False
        
        if commit:
            user.save()
        return user


class EmailAuthenticationForm(AuthenticationForm):
    """メールアドレスでログインするフォーム"""
    
    username = forms.EmailField(
        label="メールアドレス",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'メールアドレス',
            'autofocus': True
        })
    )
    
    password = forms.CharField(
        label="パスワード",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'パスワード'
        })
    )


class ReviewForm(forms.ModelForm):
    """レビューフォーム"""

    rating = forms.ChoiceField(
        choices=TeaReview.RATING_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='評価',
        initial=3,
    )
    
    class Meta:
        model = TeaReview
        fields = ['rating', 'content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'レビューを入力してください'
            }),
        }
        labels = {
            'content': 'レビュー内容',
        }
