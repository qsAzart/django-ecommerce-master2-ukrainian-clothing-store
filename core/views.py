import random
import string
from django.shortcuts import render
from django.db.models import Q

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.generic import ListView, DetailView, View

from .forms import CheckoutForm, CouponForm, RefundForm, PaymentForm,CreateProduct
from .models import Item, OrderItem, Order, Address, Payment, Coupon, Refund, UserProfile

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))


def products(request):
    context = {
        'items': Item.objects.all()
    }
    return render(request, "products.html", context)


def is_valid_form(values):
    valid = True
    for field in values:
        if field == '':
            valid = False
    return valid


class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            form = CheckoutForm()
            context = {
                'form': form,
                'couponform': CouponForm(),
                'order': order,
                'DISPLAY_COUPON_FORM': True
            }

            shipping_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='S',
                default=True
            )
            if shipping_address_qs.exists():
                context.update(
                    {'default_shipping_address': shipping_address_qs[0]})

            billing_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='B',
                default=True
            )
            if billing_address_qs.exists():
                context.update(
                    {'default_billing_address': billing_address_qs[0]})
            return render(self.request, "checkout.html", context)
        except ObjectDoesNotExist:
            messages.info(self.request, "У вас немає активного замовлення.")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():

                use_default_shipping = form.cleaned_data.get(
                    'use_default_shipping')
                if use_default_shipping:
                    print("Використання адреси доставки за умовчанням.")
                    address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='S',
                        default=True
                    )
                    if address_qs.exists():
                        shipping_address = address_qs[0]
                        order.shipping_address = shipping_address
                        order.save()
                    else:
                        messages.info(
                            self.request, "У вас немає адреси доставки за умовчанням.")
                        return redirect('core:checkout')
                else:
                    print("Користувач вводить нову адресу доставки.")
                    shipping_address1 = form.cleaned_data.get(
                        'shipping_address')
                    shipping_address2 = form.cleaned_data.get(
                        'shipping_address2')
                    shipping_country = form.cleaned_data.get(
                        'shipping_country')
                    shipping_zip = form.cleaned_data.get('shipping_zip')

                    if is_valid_form([shipping_address1, shipping_country, shipping_zip]):
                        shipping_address = Address(
                            user=self.request.user,
                            street_address=shipping_address1,
                            apartment_address=shipping_address2,
                            country=shipping_country,
                            zip=shipping_zip,
                            address_type='S'
                        )
                        shipping_address.save()

                        order.shipping_address = shipping_address
                        order.save()

                        set_default_shipping = form.cleaned_data.get(
                            'set_default_shipping')
                        if set_default_shipping:
                            shipping_address.default = True
                            shipping_address.save()

                use_default_billing = form.cleaned_data.get(
                    'use_default_billing')
                same_billing_address = form.cleaned_data.get(
                    'same_billing_address')

                if same_billing_address:
                    billing_address = shipping_address
                    billing_address.pk = None
                    billing_address.save()
                    billing_address.address_type = 'B'
                    billing_address.save()
                    order.billing_address = billing_address
                    order.save()

                elif use_default_billing:
                    print("Використання платіжної адреси за умовчанням.")
                    address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='B',
                        default=True
                    )
                    if address_qs.exists():
                        billing_address = address_qs[0]
                        order.billing_address = billing_address
                        order.save()
                    else:
                        messages.info(
                            self.request, "Платіжна адреса за умовчанням недоступна.")
                        return redirect('core:checkout')
                else:
                    print("Користувач вводить нову платіжну адресу.")
                    billing_address1 = form.cleaned_data.get(
                        'billing_address')
                    billing_address2 = form.cleaned_data.get(
                        'billing_address2')
                    billing_country = form.cleaned_data.get(
                        'billing_country')
                    billing_zip = form.cleaned_data.get('billing_zip')

                    if is_valid_form([billing_address1, billing_country, billing_zip]):
                        billing_address = Address(
                            user=self.request.user,
                            street_address=billing_address1,
                            apartment_address=billing_address2,
                            country=billing_country,
                            zip=billing_zip,
                            address_type='B'
                        )
                        billing_address.save()

                        order.billing_address = billing_address
                        order.save()

                        set_default_billing = form.cleaned_data.get(
                            'set_default_billing')
                        if set_default_billing:
                            billing_address.default = True
                            billing_address.save()

                payment_option = form.cleaned_data.get('payment_option')

                if payment_option == 'M':
                    return redirect('core:payment', payment_option='Monobank')
                elif payment_option == 'P':
                    return redirect('core:payment', payment_option='Privat24')
                else:
                    messages.warning(
                        self.request, "Вибрано недійсний спосіб оплати.")
                    return redirect('core:checkout')
        except ObjectDoesNotExist:
            messages.warning(self.request, "У вас немає активного замовлення.")
            return redirect("core:order-summary")


class PaymentView(View):
    def get(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        if order.billing_address:
            context = {
                'order': order,
                'DISPLAY_COUPON_FORM': False,
                'STRIPE_PUBLIC_KEY' : settings.STRIPE_PUBLIC_KEY
            }
            userprofile = self.request.user.userprofile
            if userprofile.one_click_purchasing:
                # fetch the users card list
                cards = stripe.Customer.list_sources(
                    userprofile.stripe_customer_id,
                    limit=3,
                    object='card'
                )
                card_list = cards['data']
                if len(card_list) > 0:
                    # update the context with the default card
                    context.update({
                        'card': card_list[0]
                    })
            return render(self.request, "payment.html", context)
        else:
            messages.warning(
                self.request, "Ви не додали платіжну адресу.")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        form = PaymentForm(self.request.POST)
        userprofile = UserProfile.objects.get(user=self.request.user)
        if form.is_valid():
            token = form.cleaned_data.get('stripeToken')
            save = form.cleaned_data.get('save')
            use_default = form.cleaned_data.get('use_default')

            if save:
                if userprofile.stripe_customer_id != '' and userprofile.stripe_customer_id is not None:
                    customer = stripe.Customer.retrieve(
                        userprofile.stripe_customer_id)
                    customer.sources.create(source=token)

                else:
                    customer = stripe.Customer.create(
                        email=self.request.user.email,
                    )
                    customer.sources.create(source=token)
                    userprofile.stripe_customer_id = customer['id']
                    userprofile.one_click_purchasing = True
                    userprofile.save()

            amount = int(order.get_total() * 100)

            try:

                if use_default or save:
                    # charge the customer because we cannot charge the token more than once
                    charge = stripe.Charge.create(
                        amount=amount,  # cents
                        currency="usd",
                        customer=userprofile.stripe_customer_id
                    )
                else:
                    # charge once off on the token
                    charge = stripe.Charge.create(
                        amount=amount,  # cents
                        currency="usd",
                        source=token
                    )

                # create the payment
                payment = Payment()
                payment.stripe_charge_id = charge['id']
                payment.user = self.request.user
                payment.amount = order.get_total()
                payment.save()

                # assign the payment to the order

                order_items = order.items.all()
                order_items.update(ordered=True)
                for item in order_items:
                    item.save()

                order.ordered = True
                order.payment = payment
                order.ref_code = create_ref_code()
                order.save()

                messages.success(self.request, "Ваше замовлення виконано успішно!")
                return redirect("/")

            except stripe.error.CardError as e:
                body = e.json_body
                err = body.get('error', {})
                messages.warning(self.request, f"{err.get('message')}")
                return redirect("/")

            except stripe.error.RateLimitError as e:
                # Too many requests made to the API too quickly
                messages.warning(self.request, "Помилка обмеження швидкості.")
                return redirect("/")

            except stripe.error.InvalidRequestError as e:
                # Invalid parameters were supplied to Stripe's API
                print(e)
                messages.warning(self.request, "Недійсні параметри.")
                return redirect("/")

            except stripe.error.AuthenticationError as e:
                # Authentication with Stripe's API failed
                # (maybe you changed API keys recently)
                messages.warning(self.request, "Не автентифіковано.")
                return redirect("/")

            except stripe.error.APIConnectionError as e:
                # Network communication with Stripe failed
                messages.warning(self.request, "Помилка мережі.")
                return redirect("/")

            except stripe.error.StripeError as e:
                # Display a very generic error to the user, and maybe send
                # yourself an email
                messages.warning(
                    self.request, "Щось пішло не так. З вас не стягунули плату. Будь ласка спробуйте ще раз.")
                return redirect("/")

            except Exception as e:
                # send an email to ourselves
                messages.warning(
                    self.request, "Сталася помилка! Просимо вас звернутися до нас у підтримці.")
                return redirect("/")

        messages.warning(self.request, "Отримано недійсні дані.")
        return redirect("/payment/stripe/")


class HomeView(ListView):
    model = Item
    paginate_by = 10
    template_name = "home.html"

class HomeHeaderView(ListView):
    model = Item
    paginate_by = 10
    template_name = "home.html"

class AboutHeaderView(ListView):
    model = Item
    paginate_by = 10
    template_name = "about.html"


class SupportHeaderView(ListView):
    model = Item
    paginate_by = 10
    template_name = "support.html"


class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'object': order
            }
            return render(self.request, 'order_summary.html', context)
        except ObjectDoesNotExist:
            messages.warning(self.request, "У вас немає активного замовлення.")
            return redirect("/")


class ItemDetailView(DetailView):
    model = Item
    template_name = "product.html"


@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
    )
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "Кількість цього товару оновлено.")
            return redirect("core:order-summary")
        else:
            order.items.add(order_item)
            messages.info(request, "Цей товар додано у ваш кошик.")
            return redirect("core:order-summary")
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(
            user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "Цей товар додано у ваш кошик.")
        return redirect("core:order-summary")


@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order.items.remove(order_item)
            order_item.delete()
            messages.info(request, "Даний товар видалено з вашого кошика.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "Цього товару немає у вашому кошику.")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "У вас немає активного замовлення.")
        return redirect("core:product", slug=slug)


def remove_message_after_delay(request, delay):
    def remove_message():
        messages.get_messages(request).used = True

    timer = threading.Timer(delay, remove_message)
    timer.start()


@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
            messages.info(request, "Кількість цього товару оновлено.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "Цього товару не було у вашому кошику.")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "У вас немає активного замовлення.")
        return redirect("core:product", slug=slug)


def get_coupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.info(request, "Цього купону не існує.")
        return redirect("core:checkout")


class AddCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get('code')
                order = Order.objects.get(
                    user=self.request.user, ordered=False)
                order.coupon = get_coupon(self.request, code)
                order.save()
                messages.success(self.request, "Купон успішно додано!")
                return redirect("core:checkout")
            except ObjectDoesNotExist:
                messages.info(self.request, "У вас немає активного замовлення.")
                return redirect("core:checkout")


class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            'form': form
        }
        return render(self.request, "request_refund.html", context)

    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')
            # edit the order
            try:
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested = True
                order.save()

                # store the refund
                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()

                messages.info(self.request, "Ваш запит отримано.")
                return redirect("core:request-refund")

            except ObjectDoesNotExist:
                messages.info(self.request, "Цього порядку не існує.")
                return redirect("core:request-refund")

@login_required
def createProduct(request):
    form = CreateProduct()
    if request.method == 'POST':
        form = CreateProduct(request.POST)
        if form.is_valid():
            form.save()
            return products(request)
    return render(request,'create_product.html', {'form': form})

def accessories_category(request):
    accessories = Item.objects.filter(category='AC')
    return render(request, 'categories/accessories_category.html', {'object_list': accessories})

def baseball_caps_category(request):
    baseball_caps = Item.objects.filter(category='BC')
    return render(request, 'categories/baseball_caps_category.html', {'object_list': baseball_caps})

def jackets_category(request):
    jackets = Item.objects.filter(category='JK')
    return render(request, 'categories/jackets_category.html', {'object_list': jackets})

def caps_category(request):
    caps = Item.objects.filter(category='CP')
    return render(request, 'categories/caps_category.html', {'object_list': caps})

def sneakers_category(request):
    sneakers = Item.objects.filter(category='SN')
    return render(request, 'categories/sneakers_category.html', {'object_list': sneakers})

def pajamas_category(request):
    pajamas = Item.objects.filter(category='PM')
    return render(request, 'categories/pajamas_category.html', {'object_list': pajamas})

def sandals_category(request):
    sandals = Item.objects.filter(category='SA')
    return render(request, 'categories/sandals_category.html', {'object_list': sandals})

def shirts_category(request):
    shirts = Item.objects.filter(category='SR')
    return render(request, 'categories/shirts_category.html', {'object_list': shirts})

def tracksuits_category(request):
    tracksuits = Item.objects.filter(category='SW')
    return render(request, 'categories/tracksuits_category.html', {'object_list': tracksuits})

def t_shirts_and_tops_category(request):
    t_shirts_and_tops = Item.objects.filter(category='TT')
    return render(request, 'categories/t-shirts_and_tops_category.html', {'object_list': t_shirts_and_tops})

def hoodies_and_sweatshirts_category(request):
    hoodies_and_sweatshirts = Item.objects.filter(category='HS')
    return render(request, 'categories/hoodies_and_sweatshirts_category.html', {'object_list': hoodies_and_sweatshirts})

def boots_category(request):
    boots = Item.objects.filter(category='BT')
    return render(request, 'categories/boots_category.html', {'object_list': boots})

def pants_and_jeans_category(request):
    pants_and_jeans = Item.objects.filter(category='PJ')
    return render(request, 'categories/pants_and_jeans_category.html', {'object_list': pants_and_jeans})

def shorts_category(request):
    shorts = Item.objects.filter(category='SH')
    return render(request, 'categories/shorts_category.html', {'object_list': shorts})

def socks_category(request):
    socks = Item.objects.filter(category='SC')
    return render(request, 'categories/socks_category.html', {'object_list': socks})


def products_by_category(request, category):
    products = Product.objects.filter(category=category)

    product_data = [
        {
            'title': product.title,
            'price': product.price,
            'url': product.get_absolute_url(),
        }
        for product in products
    ]

    return JsonResponse(product_data, safe=False)

def search(request):
    query = request.GET.get('query')
    if query:
        items = Item.objects.filter(title__icontains=query)
    else:
        items = Item.objects.none()

    products_data = []
    for item in items:
        product_data = {
            'image': item.image,
            'category': item.get_category_display(),
            'title': item.title,
            'price': item.price,
            'discount_price': item.discount_price,
            'url': item.get_absolute_url(),
        }
        products_data.append(product_data)

    context = {
        'products_data': products_data,
    }

    return render(request, "search_view.html", context)
