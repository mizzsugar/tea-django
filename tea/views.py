from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.db.models import Count, Exists, OuterRef
from tea.models import Tea, FavoriteTea
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from django.contrib import messages
from django.db.models import Count, Exists, OuterRef, Value, BooleanField
from tea.forms import SignUpForm, SignInForm


def signup_view(request):
    """会員登録ビュー - 完全フラット"""
    # フォームを作成（POSTデータがあれば使用）
    form = SignUpForm(request.POST or None)
    
    # バリデーション成功時のみ保存処理
    if form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, '会員登録が完了しました。')
        return redirect('home')
    
    # GET時やバリデーション失敗時はフォームを表示
    return render(request, 'accounts/signup.html', {'form': form})


def signin_view(request):
    """サインインビュー - 完全フラット"""
    form = SignInForm(request.POST or None)
    
    # バリデーション成功時のみ認証処理
    if form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password']
        )
        
        if user:
            login(request, user)
            messages.success(request, 'ログインしました。')
            return redirect(request.GET.get('next', 'home'))
        
        messages.error(request, 'ユーザー名またはパスワードが正しくありません。')
    
    return render(request, 'accounts/signin.html', {'form': form})


@login_required
def home_view(request):
    """ホーム画面（ログイン必須）"""
    return render(request, 'accounts/home.html')


def signout_view(request):
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

    return render(request, 'tea/published_tea_detail.html', {'tea': tea})



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
