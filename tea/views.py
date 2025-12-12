from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import BooleanField, Count, Exists, OuterRef, Value
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from model.models import FavoriteTea, Tea, TeaReview
from tea.forms import ReviewForm


@require_GET
def published_tea_list(request):
    now = timezone.now()
    teas = (
        Tea.objects.filter(
            published_at__isnull=False,
            published_at__lt=now,
            products__is_available=True,
        )
        .distinct()
        .prefetch_related("products")
        .annotate(favorites_count=Count("favorited_by", distinct=True))
    )

    if request.user.is_authenticated:
        user_favorite = FavoriteTea.objects.filter(
            user=request.user, tea=OuterRef("pk")
        )
        teas = teas.annotate(is_favorited=Exists(user_favorite))
    else:
        teas = teas.annotate(is_favorited=Value(False, output_field=BooleanField()))

    return render(request, "tea/published_tea_list.html", {"teas": teas})


@require_GET
def published_tea_detail(request, tea_id: int):
    """お茶詳細ページ"""
    now = timezone.now()

    # 1つのお茶だけにアノテーションを適用
    queryset = Tea.objects.filter(
        pk=tea_id, published_at__isnull=False, published_at__lt=now
    ).annotate(favorites_count=Count("favorited_by"))

    if request.user.is_authenticated:
        user_favorite = FavoriteTea.objects.filter(
            user=request.user, tea=OuterRef("pk")
        )
        queryset = queryset.annotate(is_favorited=Exists(user_favorite))
    else:
        queryset = queryset.annotate(
            is_favorited=Value(False, output_field=BooleanField())
        )

    tea = get_object_or_404(queryset)

    products = tea.products.filter(is_available=True)
    reviews = tea.reviews.select_related("user").all()

    # ユーザーが既にレビュー済みかチェック
    user_has_reviewed = False
    if request.user.is_authenticated:
        user_has_reviewed = TeaReview.objects.filter(
            tea=tea, user=request.user
        ).exists()

    # レビューフォーム
    review_form = None
    if request.user.is_authenticated and not user_has_reviewed:
        review_form = ReviewForm()

    return render(
        request,
        "tea/published_tea_detail.html",
        {
            "tea": tea,
            "reviews": reviews,
            "user_has_reviewed": user_has_reviewed,
            "review_form": review_form,
            "products": products,
        },
    )


@login_required
@require_POST
def add_favorite_tea(request, tea_id):
    """お気に入りに追加"""
    if request.method == "POST":
        tea = get_object_or_404(Tea, pk=tea_id)

        # お気に入りを追加（既に存在する場合は何もしない）
        FavoriteTea.objects.get_or_create(user=request.user, tea=tea)

        # 更新後のいいね数を取得
        favorites_count = tea.favorited_by.count()

        return JsonResponse(
            {
                "success": True,
                "is_favorited": True,
                "favorites_count": favorites_count,
                "add_url": reverse("add_favorite_tea", args=[tea_id]),
                "cancel_url": reverse("cancel_favorite_tea", args=[tea_id]),
            }
        )

    return JsonResponse({"success": False}, status=400)


@login_required
@require_POST
def cancel_favorite_tea(request, tea_id):
    """お気に入りを解除"""
    if request.method == "POST":
        tea = get_object_or_404(Tea, pk=tea_id)

        # お気に入りを削除
        FavoriteTea.objects.filter(user=request.user, tea=tea).delete()

        # 更新後のいいね数を取得
        favorites_count = tea.favorited_by.count()

        return JsonResponse(
            {
                "success": True,
                "is_favorited": False,
                "favorites_count": favorites_count,
                "add_url": reverse("add_favorite_tea", args=[tea_id]),
                "cancel_url": reverse("cancel_favorite_tea", args=[tea_id]),
            }
        )

    return JsonResponse({"success": False}, status=400)


@login_required
@require_POST
def add_review(request, tea_id):
    """お茶のレビューをする"""
    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.user = request.user
        review.tea_id = tea_id
        review.save()
        messages.success(request, "レビューが送信されました。")
        return redirect("published_tea_detail", tea_id=tea_id)


# お茶の好み診断の質問データ
TEA_PREFERENCE_QUESTIONS = [
    {
        "id": 1,
        "question": "朝起きた時、最初に飲みたいのは？",
        "choices": [
            {
                "value": "a",
                "text": "すっきり爽やかな一杯",
                "scores": {"light": 3, "middle": 1, "deep": 0},
            },
            {
                "value": "b",
                "text": "バランスの良い落ち着く一杯",
                "scores": {"light": 1, "middle": 3, "deep": 1},
            },
            {
                "value": "c",
                "text": "濃厚でしっかりした一杯",
                "scores": {"light": 0, "middle": 1, "deep": 3},
            },
        ],
    },
    {
        "id": 2,
        "question": "お茶の香りで好きなのは？",
        "choices": [
            {
                "value": "a",
                "text": "清々しい青葉のような香り",
                "scores": {"light": 3, "middle": 1, "deep": 0},
            },
            {
                "value": "b",
                "text": "ほどよい香ばしさと甘さ",
                "scores": {"light": 1, "middle": 3, "deep": 1},
            },
            {
                "value": "c",
                "text": "深くまろやかな香り",
                "scores": {"light": 0, "middle": 1, "deep": 3},
            },
        ],
    },
    {
        "id": 3,
        "question": "味の濃さの好みは？",
        "choices": [
            {
                "value": "a",
                "text": "薄めでさっぱり",
                "scores": {"light": 3, "middle": 1, "deep": 0},
            },
            {
                "value": "b",
                "text": "標準的な濃さ",
                "scores": {"light": 1, "middle": 3, "deep": 1},
            },
            {
                "value": "c",
                "text": "濃いめでしっかり",
                "scores": {"light": 0, "middle": 1, "deep": 3},
            },
        ],
    },
    {
        "id": 4,
        "question": "お茶を飲む時、どんな気分になりたい？",
        "choices": [
            {
                "value": "a",
                "text": "シャキッと目覚めたい",
                "scores": {"light": 3, "middle": 1, "deep": 0},
            },
            {
                "value": "b",
                "text": "リラックスしたい",
                "scores": {"light": 1, "middle": 3, "deep": 1},
            },
            {
                "value": "c",
                "text": "ほっこり温まりたい",
                "scores": {"light": 0, "middle": 1, "deep": 3},
            },
        ],
    },
    {
        "id": 5,
        "question": "苦味についてどう思う？",
        "choices": [
            {
                "value": "a",
                "text": "控えめがいい",
                "scores": {"light": 3, "middle": 1, "deep": 0},
            },
            {
                "value": "b",
                "text": "適度にあると良い",
                "scores": {"light": 1, "middle": 3, "deep": 1},
            },
            {
                "value": "c",
                "text": "しっかり感じたい",
                "scores": {"light": 0, "middle": 1, "deep": 3},
            },
        ],
    },
    {
        "id": 6,
        "question": "お茶と一緒に食べるなら？",
        "choices": [
            {
                "value": "a",
                "text": "軽めの和菓子（干菓子など）",
                "scores": {"light": 3, "middle": 1, "deep": 0},
            },
            {
                "value": "b",
                "text": "おまんじゅうやどら焼き",
                "scores": {"light": 1, "middle": 3, "deep": 1},
            },
            {
                "value": "c",
                "text": "羊羹や練り切り",
                "scores": {"light": 0, "middle": 1, "deep": 3},
            },
        ],
    },
    {
        "id": 7,
        "question": "お茶を淹れる時の温度は？",
        "choices": [
            {
                "value": "a",
                "text": "少し冷ました70度くらい",
                "scores": {"light": 3, "middle": 1, "deep": 0},
            },
            {
                "value": "b",
                "text": "80度くらい",
                "scores": {"light": 1, "middle": 3, "deep": 1},
            },
            {
                "value": "c",
                "text": "熱めの90度くらい",
                "scores": {"light": 0, "middle": 1, "deep": 3},
            },
        ],
    },
    {
        "id": 8,
        "question": "お茶の色で好きなのは？",
        "choices": [
            {
                "value": "a",
                "text": "黄金色に輝く澄んだ色",
                "scores": {"light": 3, "middle": 1, "deep": 0},
            },
            {
                "value": "b",
                "text": "鮮やかな黄緑色",
                "scores": {"light": 1, "middle": 3, "deep": 1},
            },
            {
                "value": "c",
                "text": "深い緑色",
                "scores": {"light": 0, "middle": 1, "deep": 3},
            },
        ],
    },
]


@login_required
def tea_preference_quiz(request):
    """お茶の好み診断ページ"""
    return render(
        request,
        "tea/preference_quiz.html",
        {"questions": TEA_PREFERENCE_QUESTIONS},
    )


@login_required
@require_POST
def tea_preference_result(request):
    """お茶の好み診断結果を計算して保存"""
    scores = {"light": 0, "middle": 0, "deep": 0}

    for question in TEA_PREFERENCE_QUESTIONS:
        answer = request.POST.get(f"q{question['id']}")
        if answer:
            for choice in question["choices"]:
                if choice["value"] == answer:
                    for tea_type, score in choice["scores"].items():
                        scores[tea_type] += score
                    break

    # 最も高いスコアのタイプを選択
    preference = max(scores, key=scores.get)

    # ユーザーのtea_preferenceを更新
    request.user.tea_preference = preference
    request.user.save(update_fields=["tea_preference"])

    # 診断結果の詳細情報
    preference_details = {
        "light": {
            "name": "浅蒸し",
            "description": "あなたにおすすめは「浅蒸し」のお茶です！清々しい香りとすっきりとした味わいが特徴で、シャキッとしたい朝や、さっぱりしたい時にぴったり。繊細な旨味と爽やかな渋みのバランスが絶妙です。",
            "color": "#90EE90",
        },
        "middle": {
            "name": "中蒸し",
            "description": "あなたにおすすめは「中蒸し」のお茶です！香りと味のバランスが良く、どんなシーンにも合う万能タイプ。ほどよい甘みと旨味で、毎日飲んでも飽きない美味しさです。",
            "color": "#3CB371",
        },
        "deep": {
            "name": "深蒸し",
            "description": "あなたにおすすめは「深蒸し」のお茶です！濃厚な味わいとまろやかなコクが特徴で、リラックスしたい時やしっかりとお茶を楽しみたい時に最適。甘みが強く、渋みが少ないのが魅力です。",
            "color": "#006400",
        },
    }

    return render(
        request,
        "tea/preference_result.html",
        {
            "preference": preference,
            "preference_detail": preference_details[preference],
            "scores": scores,
        },
    )
