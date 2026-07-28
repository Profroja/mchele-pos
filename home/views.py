from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from auth.models import User
from pos.models import Sale
from django.db.models import Sum
from inventory.models import Package
from store.models import Store


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'login.html', {
                'error': 'Invalid username or password',
            })

    return render(request, 'login.html')


@login_required
def dashboard_view(request):
    user = request.user

    if user.is_manager:
        import datetime, calendar
        today = datetime.date.today()

        # Month navigation
        month_str = request.GET.get('month', '')
        try:
            selected_month = datetime.datetime.strptime(month_str, '%Y-%m').date()
        except (ValueError, TypeError):
            selected_month = today.replace(day=1)

        month_start = selected_month.replace(day=1)
        month_end = selected_month.replace(day=calendar.monthrange(selected_month.year, selected_month.month)[1])
        month_end_dt = datetime.datetime.combine(month_end, datetime.time.max)

        prev_month = (month_start - datetime.timedelta(days=1)).replace(day=1)
        next_month = (month_end + datetime.timedelta(days=1)).replace(day=1)

        # Overall stats
        total_sales = Sale.objects.count()
        total_revenue = Sale.objects.aggregate(total=Sum('total_amount'))['total'] or 0
        today_sales = Sale.objects.filter(sale_date__date=today)
        today_count = today_sales.count()
        today_revenue = today_sales.aggregate(total=Sum('total_amount'))['total'] or 0

        # Month stats
        month_sales = Sale.objects.filter(sale_date__gte=month_start, sale_date__lte=month_end_dt)
        month_count = month_sales.count()
        month_revenue = month_sales.aggregate(total=Sum('total_amount'))['total'] or 0
        from pos.models import SaleItem
        month_items_count = SaleItem.objects.filter(sale__in=month_sales).count()
        month_avg = month_revenue / month_count if month_count > 0 else 0

        total_stock = Package.objects.filter(status='in_stock').count()
        in_stock = Package.objects.filter(status='in_stock').count()
        sold = Package.objects.filter(status='sold').count()
        in_stock_value = Package.objects.filter(status='in_stock').aggregate(total=Sum('selling_price'))['total'] or 0
        sold_amount = Package.objects.filter(status='sold').aggregate(total=Sum('selling_price'))['total'] or 0

        recent_sales = Sale.objects.all()[:5]

        month_name = selected_month.strftime('%B %Y')

        return render(request, 'manager_dashboard.html', {
            'total_sales': total_sales,
            'total_revenue': f'{total_revenue:,.0f}',
            'today_count': today_count,
            'today_revenue': f'{today_revenue:,.0f}',
            'total_stock': total_stock,
            'in_stock': in_stock,
            'sold': sold,
            'in_stock_value': f'{in_stock_value:,.0f}',
            'sold_amount': f'{sold_amount:,.0f}',
            'recent_sales': recent_sales,
            'month_name': month_name,
            'month_count': month_count,
            'month_revenue': f'{month_revenue:,.0f}',
            'month_items_count': month_items_count,
            'month_avg': f'{month_avg:,.0f}',
            'prev_month': prev_month.strftime('%Y-%m'),
            'next_month': next_month.strftime('%Y-%m'),
            'is_current_month': month_start == today.replace(day=1),
        })
    elif user.is_sales_person:
        return redirect('pos_dashboard')
    elif user.is_stock_person:
        return redirect('inventory_dashboard')
    else:
        return HttpResponse('<h1>Unknown role</h1>', status=403)


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def manager_sales_view(request):
    if not request.user.is_manager:
        return redirect('dashboard')

    import datetime, calendar
    today = datetime.date.today()
    default_start = today.replace(day=1)
    default_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])

    start_date = request.GET.get('start_date', default_start.strftime('%Y-%m-%d'))
    end_date = request.GET.get('end_date', default_end.strftime('%Y-%m-%d'))

    try:
        start_dt = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.datetime.strptime(end_date, '%Y-%m-%d').replace(
            hour=23, minute=59, second=59
        )
    except (ValueError, TypeError):
        start_dt = datetime.datetime.combine(default_start, datetime.time.min)
        end_dt = datetime.datetime.combine(default_end, datetime.time.max)
        start_date = default_start.strftime('%Y-%m-%d')
        end_date = default_end.strftime('%Y-%m-%d')

    store_filter = request.GET.get('store_id', '').strip()

    sales = Sale.objects.filter(sale_date__gte=start_dt, sale_date__lte=end_dt)
    if store_filter:
        sales = sales.filter(store_id=store_filter)

    stores = Store.objects.all().order_by('name')
    total_sales = sales.count()
    total_revenue = sales.aggregate(total=Sum('total_amount'))['total'] or 0

    return render(request, 'manager_sales.html', {
        'sales': sales,
        'total_sales': total_sales,
        'total_revenue': f'{total_revenue:,.0f}',
        'start_date': start_date,
        'end_date': end_date,
        'store_filter': store_filter,
        'stores': stores,
    })


@login_required
def manager_stock_view(request):
    if not request.user.is_manager:
        return redirect('dashboard')

    product_name = request.GET.get('product_name', '').strip()
    weight = request.GET.get('weight', '').strip()
    store_filter = request.GET.get('store_id', '').strip()

    packages = Package.objects.all().order_by('-created_at')

    if store_filter:
        packages = packages.filter(store_id=store_filter)
    if product_name:
        packages = packages.filter(product_name__icontains=product_name)
    if weight:
        packages = packages.filter(weight=weight)

    stores = Store.objects.all().order_by('name')
    product_names = Package.objects.exclude(product_name__isnull=True).exclude(product_name__exact='').values_list('product_name', flat=True).distinct().order_by('product_name')
    weights = Package.objects.values_list('weight', flat=True).distinct().order_by('weight')

    total_count = packages.count()
    in_stock_count = packages.filter(status='in_stock').count()
    sold_count = packages.filter(status='sold').count()
    in_stock_value = packages.filter(status='in_stock').aggregate(total=Sum('selling_price'))['total'] or 0
    sold_value = packages.filter(status='sold').aggregate(total=Sum('selling_price'))['total'] or 0
    total_value = packages.aggregate(total=Sum('selling_price'))['total'] or 0

    return render(request, 'manager_stock.html', {
        'packages': packages,
        'product_name': product_name,
        'weight': weight,
        'store_filter': store_filter,
        'stores': stores,
        'product_names': product_names,
        'weights': weights,
        'total_count': total_count,
        'in_stock_count': in_stock_count,
        'sold_count': sold_count,
        'in_stock_value': f'{in_stock_value:,.0f}',
        'sold_value': f'{sold_value:,.0f}',
        'total_value': f'{total_value:,.0f}',
    })


@login_required
def staff_view(request):
    if not request.user.is_manager:
        return redirect('dashboard')
    users = User.objects.all().order_by('-date_joined')
    stores = Store.objects.all().order_by('name')
    return render(request, 'manager_staff.html', {'users': users, 'stores': stores})


@login_required
def create_user_view(request):
    if not request.user.is_manager:
        return redirect('dashboard')

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        username = request.POST.get('username')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        phone = request.POST.get('phone', '')
        role = request.POST.get('role')
        password = request.POST.get('password')
        store_id = request.POST.get('store_id', '').strip()

        store = None
        if store_id:
            store = get_object_or_404(Store, id=store_id)

        if user_id:
            user = get_object_or_404(User, id=user_id)
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.phone = phone
            user.role = role
            user.store = store if role != 'manager' else None
            if password:
                user.set_password(password)
            user.updated_by = request.user
            user.save()
            messages.success(request, 'User updated successfully.')
        else:
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists.')
                return redirect('staff')
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                role=role,
                created_by=request.user,
            )
            user.store = store if role != 'manager' else None
            user.save()
            messages.success(request, 'User created successfully.')

        return redirect('staff')

    return redirect('staff')


@login_required
def get_user_view(request, user_id):
    if not request.user.is_manager:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    user = get_object_or_404(User, id=user_id)
    return JsonResponse({
        'id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'phone': user.phone,
        'role': user.role,
        'store_id': user.store.id if user.store else '',
    })


@require_POST
@login_required
def delete_user_view(request, user_id):
    if not request.user.is_manager:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)

    user = get_object_or_404(User, id=user_id)
    if user.id == request.user.id:
        return JsonResponse({'success': False, 'message': 'You cannot delete yourself.'})
    username = user.username
    user.delete()
    return JsonResponse({'success': True, 'message': f'User "{username}" deleted successfully.'})


@login_required
def stores_view(request):
    if not request.user.is_manager:
        return redirect('dashboard')
    stores = Store.objects.all().order_by('name')
    return render(request, 'manager_stores.html', {'stores': stores})


@login_required
def create_store_view(request):
    if not request.user.is_manager:
        return redirect('dashboard')

    if request.method == 'POST':
        store_id = request.POST.get('store_id')
        name = request.POST.get('name', '').strip()
        location = request.POST.get('location', '').strip()
        phone = request.POST.get('phone', '').strip()

        if not name:
            messages.error(request, 'Store name is required.')
            return redirect('stores')

        if store_id:
            store = get_object_or_404(Store, id=store_id)
            store.name = name
            store.location = location
            store.phone = phone
            store.updated_by = request.user
            store.save()
            messages.success(request, 'Store updated successfully.')
        else:
            if Store.objects.filter(name__iexact=name).exists():
                messages.error(request, 'Store name already exists.')
                return redirect('stores')
            Store.objects.create(
                name=name,
                location=location,
                phone=phone,
                created_by=request.user,
            )
            messages.success(request, 'Store created successfully.')

        return redirect('stores')

    return redirect('stores')


@login_required
def get_store_view(request, store_id):
    if not request.user.is_manager:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    store = get_object_or_404(Store, id=store_id)
    return JsonResponse({
        'id': store.id,
        'name': store.name,
        'location': store.location,
        'phone': store.phone,
    })


@require_POST
@login_required
def delete_store_view(request, store_id):
    if not request.user.is_manager:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)

    store = get_object_or_404(Store, id=store_id)
    name = store.name
    store.delete()
    return JsonResponse({'success': True, 'message': f'Store "{name}" deleted successfully.'})
