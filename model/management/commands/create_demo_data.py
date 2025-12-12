import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils import timezone
from faker import Faker

from model.models import (
    FavoriteTea,
    Order,
    OrderItem,
    ShippingFee,
    TaxRate,
    Tea,
    TeaProduct,
    TeaReview,
    User,
)


class Command(BaseCommand):
    help = "デモ用のダミーデータを生成"

    def handle(self, *args, **options):
        fake = Faker("ja_JP")

        self.stdout.write("税率と送料の設定...")
        self._create_tax_and_shipping()

        self.stdout.write("ユーザー作成中...")
        users = self._create_users(100, fake)

        self.stdout.write("お茶作成中...")
        teas = self._create_teas(20, fake)

        self.stdout.write("商品作成中...")
        products = self._create_products(teas)

        # お茶を3つのグループに分ける
        # グループ1: お気に入り多い・購入少ない (14種 = 70%)
        # グループ2: お気に入り少ない・購入多い (3種 = 15%)
        # グループ3: バランス型 (3種 = 15%)
        high_fav_low_purchase = teas[:14]
        low_fav_high_purchase = teas[14:17]
        balanced = teas[17:]

        self.stdout.write("お気に入り作成中...")
        self._create_favorites_strategic(
            users, high_fav_low_purchase, low_fav_high_purchase, balanced
        )

        self.stdout.write("レビュー作成中...")
        self._create_reviews(100, users, teas, fake)

        self.stdout.write("注文作成中...")
        self._create_orders_strategic(
            300,
            600,
            users,
            products,
            high_fav_low_purchase,
            low_fav_high_purchase,
            balanced,
            fake,
        )

        self.stdout.write(self.style.SUCCESS("✓ デモデータの作成が完了しました！"))

    def _create_tax_and_shipping(self):
        """税率と送料を設定"""
        if not TaxRate.objects.exists():
            TaxRate.objects.create(
                rate=Decimal("10.00"),
                start_date=timezone.now().date() - timedelta(days=365),
                is_active=True,
            )

        if not ShippingFee.objects.exists():
            ShippingFee.objects.create(
                fee=800,
                free_shipping_threshold=5000,
                start_date=timezone.now().date() - timedelta(days=365),
                is_active=True,
            )

    def _create_users(self, count, fake):
        """ユーザーを作成"""
        users = []
        for i in range(count):
            email = f"user{i + 1}@example.com"
            user = User.objects.create_user(
                email=email,
                password="password123",
                nickname=fake.name(),
                is_email_verified=True,
                is_active=True,
            )
            users.append(user)
        return users

    def _create_teas(self, count, fake):
        """お茶を作成"""
        teas = []
        steam_types = ["light", "middle", "deep"]

        # リアルなお茶の説明文
        descriptions = [
            "爽やかな香りと上品な甘みが特徴の煎茶です。一番茶のみを使用し、丁寧に仕上げました。",
            "深い蒸しで仕上げた、まろやかな味わいの深蒸し茶。渋みが少なく飲みやすいです。",
            "静岡県産の上質な茶葉を使用。すっきりとした後味が楽しめます。",
            "濃厚な旨味とコクが特徴。じっくりと味わいたい方におすすめの一品です。",
            "香り高く、バランスの取れた味わい。毎日のお茶時間にぴったりです。",
            "若葉の爽やかな香りが広がる、春摘みの新茶。季節限定の味わいをお楽しみください。",
            "伝統的な製法で作られた、昔ながらの味わい。懐かしい香りが心を和ませます。",
            "柔らかな甘みと深いコクが調和した、上品な味わいの煎茶です。",
            "すっきりとした飲み口で、食事との相性も抜群。毎日飲んでも飽きない味です。",
            "茶葉本来の旨味を引き出した、こだわりの一品。贅沢なひとときをどうぞ。",
            "渋みと甘みのバランスが絶妙。お茶好きの方に特におすすめです。",
            "芳醇な香りと深い味わいが特徴。ゆっくりとお楽しみください。",
            "爽やかな香りと優しい甘み。朝のお目覚めの一杯にぴったりです。",
            "濃厚な旨味が口いっぱいに広がります。特別な日のおもてなしにも。",
            "軽やかな飲み口で、どなたにも愛される味わい。ご家族みんなで楽しめます。",
            "茶葉の鮮やかな緑色が美しい、見た目にも楽しい煎茶です。",
            "まろやかで優しい味わい。ほっと一息つきたい時におすすめです。",
            "深い蒸しによる濃厚な味わいと、爽やかな後味が魅力です。",
            "上質な茶葉を厳選。贅沢な香りと味わいをお楽しみいただけます。",
            "バランスの良い味わいで、和菓子との相性も抜群です。",
        ]

        tea_names = [
            "特選煎茶「翠香」",
            "深蒸し煎茶「緑風」",
            "玉露「雫」",
            "かぶせ茶「若葉」",
            "上煎茶「山霧」",
            "ほうじ茶「香ばし」",
            "玄米茶「和み」",
            "抹茶「碧雲」",
            "釜炒り茶「清流」",
            "茎茶「白露」",
            "芽茶「初摘み」",
            "粉茶「朝霧」",
            "特上煎茶「極み」",
            "深蒸し茶「深緑」",
            "煎茶「さえみどり」",
            "新茶「初音」",
            "煎茶「やぶきた」",
            "深蒸し「富士の誉」",
            "玉緑茶「玉響」",
            "煎茶「茜富士」",
        ]

        origins = [
            "静岡県掛川市",
            "静岡県川根本町",
            "鹿児島県知覧",
            "京都府宇治市",
            "三重県伊勢市",
            "埼玉県狭山市",
            "静岡県牧之原市",
            "鹿児島県志布志市",
            "福岡県八女市",
            "静岡県島田市",
            "愛知県西尾市",
            "奈良県大和高原",
            "滋賀県土山町",
            "宮崎県都城市",
            "熊本県山都町",
            "佐賀県嬉野市",
            "長崎県東彼杵町",
            "岐阜県揖斐川町",
            "静岡県本山",
            "鹿児島県頴娃町",
        ]

        for i in range(count):
            tea = Tea.objects.create(
                name=tea_names[i],
                steam_type=random.choice(steam_types),
                origin=origins[i],
                description=descriptions[i],
                caffeine_free=random.choice([True, False]) if i % 8 == 0 else False,
                published_at=timezone.now() - timedelta(days=random.randint(1, 365)),
            )
            teas.append(tea)
        return teas

    def _create_products(self, teas):
        """商品を作成（各お茶に100g, 200g, 300gの3種類）"""
        products = []
        weights = [100, 200, 300]
        base_prices = {100: 800, 200: 1500, 300: 2000}

        for tea in teas:
            for weight in weights:
                product = TeaProduct.objects.create(
                    tea=tea,
                    weight=weight,
                    price=base_prices[weight] + random.randint(-200, 500),
                    stock=random.randint(50, 200),
                    is_available=True,
                )
                products.append(product)
        return products

    def _create_favorites_strategic(self, users, high_fav_teas, low_fav_teas, balanced_teas):
        """戦略的にお気に入りを作成"""
        
        created = 0
        
        # 5週間の期間設定（2025年11月12日〜2025年12月16日）
        end_date = timezone.datetime(2025, 12, 16, 23, 59, 59, tzinfo=timezone.get_current_timezone())
        start_date = timezone.datetime(2025, 11, 12, 0, 0, 0, tzinfo=timezone.get_current_timezone())
        
        for user in users:
            favorites = []
            
            # グループ1（お気に入り多い）: 各ユーザーが3-7個選ぶ
            num_high_fav = random.randint(3, 7)
            favorites.extend(random.sample(high_fav_teas, 
                                        min(num_high_fav, len(high_fav_teas))))
            
            # グループ2（お気に入り少ない）: 各ユーザーが0-1個選ぶ
            if random.random() < 0.3:  # 30%の確率で1個
                favorites.extend(random.sample(low_fav_teas, 1))
            
            # グループ3（バランス型）: 各ユーザーが0-2個選ぶ
            num_balanced = random.randint(0, 2)
            if num_balanced > 0:
                favorites.extend(random.sample(balanced_teas, 
                                            min(num_balanced, len(balanced_teas))))
            
            # お気に入り登録（created_atをランダムに分散）
            for tea in favorites:
                fav = FavoriteTea.objects.create(user=user, tea=tea)
                
                # 5週間の間でランダムな日時を生成
                total_seconds = int((end_date - start_date).total_seconds())
                random_seconds = random.randint(0, total_seconds)
                random_datetime = start_date + timedelta(seconds=random_seconds)
                
                # created_atを更新
                FavoriteTea.objects.filter(pk=fav.pk).update(created_at=random_datetime)
                created += 1
        
        self.stdout.write(f'  {created}件のお気に入りを作成（2025/11/12-12/16に分散）')


    def _create_reviews(self, count, users, teas, fake):
        """レビューを作成"""
        # リアルなレビュー文
        review_texts = [
            '香りが良く、とても美味しかったです。リピート確定です！',
            '渋みが少なく飲みやすい。毎日飲んでいます。',
            '上品な味わいで、来客時にも出せる品質です。',
            '深い味わいで満足。価格も手頃で助かります。',
            '爽やかな香りが最高。朝の一杯に最適です。',
            'まろやかで飲みやすく、家族全員が気に入っています。',
            '期待以上の品質でした。また購入したいです。',
            '濃厚な旨味があり、お茶好きにはたまりません。',
            'すっきりした後味で、食事にも合います。',
            '丁寧に作られているのが分かる味。大満足です。',
            '香りが良く、リラックスできます。おすすめです。',
            'コスパ最高！この価格でこの品質は嬉しい。',
            '初めて購入しましたが、とても気に入りました。',
            '友人へのギフトにも使いました。喜ばれました。',
            '毎日飲んでも飽きない美味しさです。',
            '色も綺麗で、見た目も楽しめます。',
            '程よい渋みと甘みのバランスが絶妙です。',
            'お茶本来の味が楽しめて満足しています。',
            '包装も丁寧で、ギフトにぴったりでした。',
            'リピーターです。いつも美味しくいただいています。',
        ]
        
        # 5週間の期間設定
        end_date = timezone.datetime(2025, 12, 16, 23, 59, 59, tzinfo=timezone.get_current_timezone())
        start_date = timezone.datetime(2025, 11, 12, 0, 0, 0, tzinfo=timezone.get_current_timezone())
        
        created = 0
        max_attempts = count * 3
        attempts = 0
        
        while created < count and attempts < max_attempts:
            user = random.choice(users)
            tea = random.choice(teas)
            attempts += 1
            
            if TeaReview.objects.filter(user=user, tea=tea).exists():
                continue
            
            review = TeaReview.objects.create(
                user=user,
                tea=tea,
                rating=random.choices([3, 4, 5], weights=[15, 35, 50])[0],
                content=random.choice(review_texts) if random.random() > 0.2 else ''
            )
            
            # created_atをランダムに分散
            total_seconds = int((end_date - start_date).total_seconds())
            random_seconds = random.randint(0, total_seconds)
            random_datetime = start_date + timedelta(seconds=random_seconds)
            
            TeaReview.objects.filter(pk=review.pk).update(created_at=random_datetime)
            created += 1
        
        self.stdout.write(f'  {created}件のレビューを作成（2025/11/12-12/16に分散）')


    def _create_orders_strategic(self, order_count, total_items, users, products,
                                high_fav_teas, low_fav_teas, balanced_teas, fake):
        """戦略的に注文を作成"""
        # 5週間の期間設定（2025年11月12日〜2025年12月16日）
        end_date = timezone.datetime(2025, 12, 16, 23, 59, 59, tzinfo=timezone.get_current_timezone())
        start_date = timezone.datetime(2025, 11, 12, 0, 0, 0, tzinfo=timezone.get_current_timezone())
        total_seconds = int((end_date - start_date).total_seconds())
        
        # 商品をグループごとに分類
        high_fav_products = [p for p in products if p.tea in high_fav_teas]
        low_fav_products = [p for p in products if p.tea in low_fav_teas]
        balanced_products = [p for p in products if p.tea in balanced_teas]
        
        for i in range(order_count):
            # 5週間の間でランダムな日時を生成
            random_seconds = random.randint(0, total_seconds)
            order_date = start_date + timedelta(seconds=random_seconds)
            
            user = random.choice(users)
            order_number = f'ORD{order_date.strftime("%Y%m%d%H%M%S")}{i:04d}'
            
            order = Order.objects.create(
                user=user,
                order_number=order_number,
                status=random.choice(['paid', 'processing', 'shipped', 'delivered']),
                shipping_name=f'ユーザー{random.randint(1, 100)}',
                shipping_postal_code=f'{random.randint(100, 999)}-{random.randint(1000, 9999)}',
                shipping_address=f'東京都渋谷区{random.randint(1, 100)}番地',
                shipping_phone=f'090-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}',
                subtotal=0,
                tax_amount=0,
                shipping_fee=0,
                total_amount=0,
                tax_rate=Decimal('10.00')
            )
            
            # created_atとupdated_atを設定
            Order.objects.filter(pk=order.pk).update(
                created_at=order_date,
                updated_at=order_date
            )
        
        # 注文明細を戦略的に作成
        orders = list(Order.objects.all())
        items_per_order = total_items // order_count
        
        for order in orders:
            num_items = random.randint(1, min(5, items_per_order))
            selected_products = []
            
            # 商品選択の重み付け
            for _ in range(num_items):
                rand = random.random()
                if rand < 0.20 and high_fav_products:
                    product = random.choice(high_fav_products)
                elif rand < 0.80 and low_fav_products:
                    product = random.choice(low_fav_products)
                else:
                    product = random.choice(balanced_products) if balanced_products else random.choice(products)
                
                if product not in selected_products:
                    selected_products.append(product)
            
            for product in selected_products:
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=random.randint(1, 3),
                    price=product.price
                )
            
            order.calculate_amounts()
            order.save()
        
        self.stdout.write(f'  {order_count}件の注文を作成（2025/11/12-12/16に分散）')
