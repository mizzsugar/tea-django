import random
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from model.models import (
    User, Tea, TeaProduct, TeaReview, Order, OrderItem, 
    TaxRate, ShippingFee, FavoriteTea
)


class Command(BaseCommand):
    help = 'デモ用のダミーデータを生成'

    def handle(self, *args, **options):
        fake = Faker('ja_JP')
        
        self.stdout.write('税率と送料の設定...')
        self._create_tax_and_shipping()
        
        self.stdout.write('ユーザー作成中...')
        users = self._create_users(100, fake)
        
        self.stdout.write('お茶作成中...')
        teas = self._create_teas(20, fake)
        
        self.stdout.write('商品作成中...')
        products = self._create_products(teas)
        
        self.stdout.write('お気に入り作成中...')
        self._create_favorites(users, teas)

        self.stdout.write('レビュー作成中...')
        self._create_reviews(100, users, teas, fake)
        
        self.stdout.write('注文作成中...')
        self._create_orders(300, 600, users, products, fake)
        
        self.stdout.write(self.style.SUCCESS('✓ デモデータの作成が完了しました！'))

    def _create_tax_and_shipping(self):
        """税率と送料を設定"""
        if not TaxRate.objects.exists():
            TaxRate.objects.create(
                rate=Decimal('10.00'),
                start_date=timezone.now().date() - timedelta(days=365),
                is_active=True
            )
        
        if not ShippingFee.objects.exists():
            ShippingFee.objects.create(
                fee=800,
                free_shipping_threshold=5000,
                start_date=timezone.now().date() - timedelta(days=365),
                is_active=True
            )

    def _create_users(self, count, fake):
        """ユーザーを作成"""
        users = []
        for i in range(count):
            email = f'user{i+1}@example.com'
            user = User.objects.create_user(
                email=email,
                password='password123',
                nickname=fake.name(),
                is_email_verified=True,
                is_active=True
            )
            users.append(user)
        return users

    def _create_teas(self, count, fake):
        """お茶を作成"""
        teas = []
        steam_types = ['light', 'middle', 'deep']
        
        # リアルなお茶の説明文
        descriptions = [
            '爽やかな香りと上品な甘みが特徴の煎茶です。一番茶のみを使用し、丁寧に仕上げました。',
            '深い蒸しで仕上げた、まろやかな味わいの深蒸し茶。渋みが少なく飲みやすいです。',
            '静岡県産の上質な茶葉を使用。すっきりとした後味が楽しめます。',
            '濃厚な旨味とコクが特徴。じっくりと味わいたい方におすすめの一品です。',
            '香り高く、バランスの取れた味わい。毎日のお茶時間にぴったりです。',
            '若葉の爽やかな香りが広がる、春摘みの新茶。季節限定の味わいをお楽しみください。',
            '伝統的な製法で作られた、昔ながらの味わい。懐かしい香りが心を和ませます。',
            '柔らかな甘みと深いコクが調和した、上品な味わいの煎茶です。',
            'すっきりとした飲み口で、食事との相性も抜群。毎日飲んでも飽きない味です。',
            '茶葉本来の旨味を引き出した、こだわりの一品。贅沢なひとときをどうぞ。',
            '渋みと甘みのバランスが絶妙。お茶好きの方に特におすすめです。',
            '芳醇な香りと深い味わいが特徴。ゆっくりとお楽しみください。',
            '爽やかな香りと優しい甘み。朝のお目覚めの一杯にぴったりです。',
            '濃厚な旨味が口いっぱいに広がります。特別な日のおもてなしにも。',
            '軽やかな飲み口で、どなたにも愛される味わい。ご家族みんなで楽しめます。',
            '茶葉の鮮やかな緑色が美しい、見た目にも楽しい煎茶です。',
            'まろやかで優しい味わい。ほっと一息つきたい時におすすめです。',
            '深い蒸しによる濃厚な味わいと、爽やかな後味が魅力です。',
            '上質な茶葉を厳選。贅沢な香りと味わいをお楽しみいただけます。',
            'バランスの良い味わいで、和菓子との相性も抜群です。',
        ]
        
        tea_names = [
            '特選煎茶「翠香」', '深蒸し煎茶「緑風」', '玉露「雫」', 
            'かぶせ茶「若葉」', '上煎茶「山霧」', 'ほうじ茶「香ばし」',
            '玄米茶「和み」', '抹茶「碧雲」', '釜炒り茶「清流」',
            '茎茶「白露」', '芽茶「初摘み」', '粉茶「朝霧」',
            '特上煎茶「極み」', '深蒸し茶「深緑」', '煎茶「さえみどり」',
            '新茶「初音」', '煎茶「やぶきた」', '深蒸し「富士の誉」',
            '玉緑茶「玉響」', '煎茶「茜富士」'
        ]
        
        origins = [
            '静岡県掛川市', '静岡県川根本町', '鹿児島県知覧',
            '京都府宇治市', '三重県伊勢市', '埼玉県狭山市',
            '静岡県牧之原市', '鹿児島県志布志市', '福岡県八女市',
            '静岡県島田市', '愛知県西尾市', '奈良県大和高原',
            '滋賀県土山町', '宮崎県都城市', '熊本県山都町',
            '佐賀県嬉野市', '長崎県東彼杵町', '岐阜県揖斐川町',
            '静岡県本山', '鹿児島県頴娃町'
        ]
        
        for i in range(count):
            tea = Tea.objects.create(
                name=tea_names[i],
                steam_type=random.choice(steam_types),
                origin=origins[i],
                description=descriptions[i],
                caffeine_free=random.choice([True, False]) if i % 8 == 0 else False,
                published_at=timezone.now() - timedelta(days=random.randint(1, 365))
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
                    is_available=True
                )
                products.append(product)
        return products

    def _create_favorites(self, users, teas):
        """お気に入りを作成"""
        
        created = 0
        # 各ユーザーが0〜8個のお気に入りを持つ
        for user in users:
            # ランダムに0〜8個のお茶をお気に入り登録
            num_favorites = random.randint(0, 8)
            if num_favorites > 0:
                favorite_teas = random.sample(teas, min(num_favorites, len(teas)))
                for tea in favorite_teas:
                    FavoriteTea.objects.create(
                        user=user,
                        tea=tea
                    )
                    created += 1
        
        self.stdout.write(f'  {created}件のお気に入りを作成')

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
        
        created = 0
        max_attempts = count * 3
        attempts = 0
        
        while created < count and attempts < max_attempts:
            user = random.choice(users)
            tea = random.choice(teas)
            attempts += 1
            
            if TeaReview.objects.filter(user=user, tea=tea).exists():
                continue
            
            TeaReview.objects.create(
                user=user,
                tea=tea,
                rating=random.choices([3, 4, 5], weights=[15, 35, 50])[0],  # 5が多め
                content=random.choice(review_texts) if random.random() > 0.2 else ''
            )
            created += 1

    def _create_orders(self, order_count, total_items, users, products, fake):
        """注文を作成（月別にバラバラ）"""
        now = timezone.now()
        
        # 過去12ヶ月に分散
        for i in range(order_count):
            # ランダムな過去の日付（0-365日前）
            days_ago = random.randint(0, 365)
            order_date = now - timedelta(days=days_ago)
            
            user = random.choice(users)
            order_number = f'ORD{order_date.strftime("%Y%m%d")}{i:04d}'
            
            # 注文を作成
            order = Order.objects.create(
                user=user,
                order_number=order_number,
                status=random.choice(['paid', 'processing', 'shipped', 'delivered']),
                shipping_name=fake.name(),
                shipping_postal_code=fake.postcode(),
                shipping_address=fake.address(),
                shipping_phone=fake.phone_number(),
                subtotal=0,
                tax_amount=0,
                shipping_fee=0,
                total_amount=0,
                tax_rate=Decimal('10.00')
            )
            
            # 作成日時を過去に設定
            Order.objects.filter(pk=order.pk).update(
                created_at=order_date,
                updated_at=order_date
            )

        # 注文明細を作成
        orders = list(Order.objects.all())
        items_per_order = total_items // order_count
        
        for order in orders:
            # 1-5個の商品をランダムに追加
            num_items = random.randint(1, min(5, items_per_order))
            selected_products = random.sample(products, num_items)
            
            for product in selected_products:
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=random.randint(1, 3),
                    price=product.price
                )
            
            # 金額を再計算
            order.calculate_amounts()
            order.save()

        self.stdout.write(f'  {order_count}件の注文、約{total_items}件の注文明細を作成')