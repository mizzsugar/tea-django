from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from authentication.forms import EmailAuthenticationForm, GeneralUserRegistrationForm
from authentication.services.registration_service import (
    RegistrationResultType,
    RegistrationService,
    ResendResultType,
    VerificationResultType,
)


def _get_base_url(request) -> str:
    """リクエストからベースURLを取得"""
    return request.build_absolute_uri("/")


def signup(request):
    """一般ユーザー登録"""
    if request.method == "POST":
        form = GeneralUserRegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get("email")
            password = form.cleaned_data.get("password1")
            nickname = form.cleaned_data.get("nickname", "")
            base_url = _get_base_url(request)

            result = RegistrationService.register_user(
                email, password, nickname, base_url
            )

            if result.result_type == RegistrationResultType.EMAIL_SEND_FAILED:
                messages.error(request, result.message)
                return render(request, "authentication/signup.html", {"form": form})

            messages.success(request, result.message)
            return redirect("signup_complete")
    else:
        form = GeneralUserRegistrationForm()

    return render(request, "authentication/signup.html", {"form": form})


def verify_email(request, token):
    """メールアドレス確認"""
    result = RegistrationService.verify_email(token)

    if result.result_type == VerificationResultType.SUCCESS:
        messages.success(request, result.message)
        return redirect("signin")

    if result.result_type == VerificationResultType.ALREADY_VERIFIED:
        messages.info(request, result.message)
        return redirect("signin")

    if result.result_type == VerificationResultType.TOKEN_EXPIRED:
        messages.error(request, result.message)
        return redirect("signup")

    # INVALID_TOKEN
    messages.error(request, result.message)
    return redirect("signup")


def resend_verification_email(request):
    """確認メール再送信"""
    if request.method == "POST":
        email = request.POST.get("email")
        base_url = _get_base_url(request)
        result = RegistrationService.resend_verification_email(email, base_url)

        if result.result_type == ResendResultType.SUCCESS:
            messages.success(request, result.message)
        else:
            messages.error(request, result.message)

        return redirect("resend_verification")

    return render(request, "authentication/resend_verification.html")


def signup_complete(request):
    """登録完了ページ"""
    return render(request, "authentication/signup_complete.html")


def signin(request):
    """メールアドレスでログイン"""
    if request.method == "POST":
        form = EmailAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(request, username=email, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, f"ようこそ、{user.get_display_name()}さん!")
                next_url = request.GET.get("next") or request.POST.get("next")
                if next_url:
                    return redirect(next_url)
                return redirect("/")
            else:
                messages.error(
                    request, "メールアドレスまたはパスワードが正しくありません。"
                )
        else:
            # メール未確認エラーの場合は特別なメッセージ
            if "email_not_verified" in str(form.errors):
                # メール再送信リンクを表示
                messages.error(
                    request,
                    "メールアドレスの確認が完了していません。"
                    '<a href="/authentication/resend-verification/">確認メールを再送信</a>',
                    extra_tags="safe",
                )
    else:
        form = EmailAuthenticationForm()

    return render(request, "authentication/signin.html", {"form": form})


@login_required
def home(request):
    """ホーム画面（ログイン必須）"""
    return render(request, "authentication/home.html")


def signout(request):
    """サインアウトビュー"""
    logout(request)
    messages.success(request, "ログアウトしました。")
    return redirect("signin")
