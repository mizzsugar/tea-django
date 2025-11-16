from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.db.models import Count, Exists, OuterRef
from tea.models import Tea, FavoriteTea, TeaReview
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from django.contrib import messages
from django.db.models import Count, Exists, OuterRef, Value, BooleanField
from tea.forms import GeneralUserRegistrationForm, EmailAuthenticationForm, ReviewForm


def signup(request):
    """一般ユーザー登録"""
    if request.method == 'POST':
        form = GeneralUserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '登録が完了しました。ログインしてください。')
            return redirect('signin')
    else:
        form = GeneralUserRegistrationForm()
    
    return render(request, 'accounts/signup.html', {'form': form})


def signin(request):
    """メールアドレスでログイン"""
    if request.method == 'POST':
        form = EmailAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')  # usernameフィールドにemailが入る
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'ようこそ、{user.get_display_name()}さん！')
                
                # next パラメータがあればそこにリダイレクト
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('/')  # ホームページなど適切なURLに変更
            else:
                messages.error(request, 'メールアドレスまたはパスワードが正しくありません。')
    else:
        form = EmailAuthenticationForm()
    
    return render(request, 'accounts/signin.html', {'form': form})


@login_required
def home(request):
    """ホーム画面（ログイン必須）"""
    return render(request, 'accounts/home.html')


def signout(request):
    """サインアウトビュー"""
    logout(request)
    messages.success(request, 'ログアウトしました。')
    return redirect('signin')


def published_tea_list(request):
    now = timezone.now()
    teas = Tea.objects.filter(published_at__isnull=False, published_at__lt=now).\
        annotate(favorites_count=Count('favorited_by'))
    
    # ログイン中のユーザーがいいねしているかをアノテーション
    if request.user.is_authenticated:
        user_favorite = FavoriteTea.objects.filter(
            user=request.user,
            tea=OuterRef('pk')
        )
        teas = teas.annotate(is_favorited=Exists(user_favorite))
    else:
        # ログインしていない場合はすべてFalse
        teas = teas.annotate(
            is_favorited=Value(False, output_field=BooleanField())
        )
    
    return render(request, 'tea/published_tea_list.html', {'teas': teas})


def published_tea_detail(request, tea_id: int):
    """お茶詳細ページ"""
    now = timezone.now()

    # 1つのお茶だけにアノテーションを適用
    queryset = Tea.objects.filter(pk=tea_id, published_at__isnull=False, published_at__lt=now).\
        annotate(favorites_count=Count('favorited_by'))
    
    if request.user.is_authenticated:
        user_favorite = FavoriteTea.objects.filter(
            user=request.user,
            tea=OuterRef('pk')
        )
        queryset = queryset.annotate(is_favorited=Exists(user_favorite))
    else:
        queryset = queryset.annotate(
            is_favorited=Value(False, output_field=BooleanField())
        )
    
    tea = get_object_or_404(queryset)

    # レビュー一覧を取得
    reviews = tea.reviews.select_related('user').all()
    
    # ユーザーが既にレビュー済みかチェック
    user_has_reviewed = False
    if request.user.is_authenticated:
        user_has_reviewed = TeaReview.objects.filter(
            tea=tea,
            user=request.user
        ).exists()

    # レビューフォーム
    review_form = None
    if request.user.is_authenticated and not user_has_reviewed:
        review_form = ReviewForm()

    return render(request, 'tea/published_tea_detail.html', {
        'tea': tea,
        'reviews': reviews,
        'user_has_reviewed': user_has_reviewed,
        'review_form': review_form,
    })



@login_required
def add_favorite_tea(request, tea_id):
    """お気に入りに追加"""
    if request.method == 'POST':
        tea = get_object_or_404(Tea, pk=tea_id)
        
        # お気に入りを追加（既に存在する場合は何もしない）
        FavoriteTea.objects.get_or_create(user=request.user, tea=tea)
        
        # 更新後のいいね数を取得
        favorites_count = tea.favorited_by.count()
        
        return JsonResponse({
            'success': True,
            'is_favorited': True,
            'favorites_count': favorites_count,
            'add_url': reverse('add_favorite_tea', args=[tea_id]),
            'cancel_url': reverse('cancel_favorite_tea', args=[tea_id])
        })
    
    return JsonResponse({'success': False}, status=400)


@login_required
def cancel_favorite_tea(request, tea_id):
    """お気に入りを解除"""
    if request.method == 'POST':
        tea = get_object_or_404(Tea, pk=tea_id)
        
        # お気に入りを削除
        FavoriteTea.objects.filter(user=request.user, tea=tea).delete()
        
        # 更新後のいいね数を取得
        favorites_count = tea.favorited_by.count()
        
        return JsonResponse({
            'success': True,
            'is_favorited': False,
            'favorites_count': favorites_count,
            'add_url': reverse('add_favorite_tea', args=[tea_id]),
            'cancel_url': reverse('cancel_favorite_tea', args=[tea_id])
        })
    
    return JsonResponse({'success': False}, status=400)


@login_required
def add_review(request, tea_id):
    """お茶のレビューをする"""
    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.user = request.user
        review.tea_id = tea_id
        review.save()
        messages.success(request, 'レビューが送信されました。')
        return redirect('published_tea_detail', tea_id=tea_id)
