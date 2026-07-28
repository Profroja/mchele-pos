import datetime

from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from inventory.models import Package
from pos.models import Sale, SaleItem
from store.models import Store
from expendicture.models import Expenditure


@login_required
def pos_dashboard_view(request):
    if not request.user.is_sales_person and not request.user.is_manager:
        return redirect('dashboard')

    user = request.user
    if user.is_manager:
        sales_qs = Sale.objects.all()
    elif user.store:
        sales_qs = Sale.objects.filter(store=user.store)
    else:
        sales_qs = Sale.objects.all()

    total_sales = sales_qs.count()
    total_revenue = sales_qs.aggregate(total=Sum('total_amount'))['total'] or 0
    today_sales = sales_qs.filter(
        sale_date__date=datetime.date.today()
    )
    today_count = today_sales.count()
    today_revenue = today_sales.aggregate(total=Sum('total_amount'))['total'] or 0

    recent_sales = sales_qs[:10]

    return render(request, 'pos_dashboard.html', {
        'total_sales': total_sales,
        'total_revenue': f'{total_revenue:,.0f}',
        'today_count': today_count,
        'today_revenue': f'{today_revenue:,.0f}',
        'recent_sales': recent_sales,
    })


@login_required
def sales_list_view(request):
    if not request.user.is_sales_person and not request.user.is_manager:
        return redirect('dashboard')

    import calendar
    from django.core.paginator import Paginator
    from django.db.models import Q

    today = datetime.date.today()
    default_start = today.replace(day=1)
    default_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])

    start_date = request.GET.get('start_date', default_start.strftime('%Y-%m-%d'))
    end_date = request.GET.get('end_date', default_end.strftime('%Y-%m-%d'))
    search = request.GET.get('search', '').strip()

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

    user = request.user
    if user.is_manager:
        sales = Sale.objects.filter(sale_date__gte=start_dt, sale_date__lte=end_dt)
    elif user.store:
        sales = Sale.objects.filter(sale_date__gte=start_dt, sale_date__lte=end_dt, store=user.store)
    else:
        sales = Sale.objects.filter(sale_date__gte=start_dt, sale_date__lte=end_dt)

    if search:
        sales = sales.filter(
            Q(receipt_number__icontains=search) |
            Q(items__barcode_value__icontains=search) |
            Q(items__product_name__icontains=search)
        ).distinct()

    total_sales = sales.count()
    total_revenue = sales.aggregate(total=Sum('total_amount'))['total'] or 0

    paginator = Paginator(sales, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'pos_sales.html', {
        'sales': page_obj,
        'page_obj': page_obj,
        'total_sales': total_sales,
        'total_revenue': f'{total_revenue:,.0f}',
        'start_date': start_date,
        'end_date': end_date,
        'search': search,
    })


@login_required
@require_POST
def create_sale_view(request):
    if not request.user.is_sales_person and not request.user.is_manager:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)

    barcodes = request.POST.getlist('barcodes')
    payment_method = request.POST.get('payment_method', 'cash')

    if not barcodes:
        barcode = request.POST.get('barcode', '').strip()
        if barcode:
            barcodes = [barcode]

    if not barcodes:
        return JsonResponse({'success': False, 'message': 'No barcodes provided'})

    packages = []
    for barcode in barcodes:
        barcode = barcode.strip()
        if not barcode:
            continue
        try:
            pkg = Package.objects.get(barcode_value=barcode)
        except Package.DoesNotExist:
            return JsonResponse({'success': False, 'message': f'Barcode {barcode} not found'})

        if pkg.status == 'sold':
            return JsonResponse({'success': False, 'message': f'Package {barcode} is already sold'})
        if pkg.status != 'in_stock':
            return JsonResponse({'success': False, 'message': f'Package {barcode} is not available ({pkg.get_status_display()})'})
        packages.append(pkg)

    if not packages:
        return JsonResponse({'success': False, 'message': 'No valid packages'})

    total_amount = sum(pkg.selling_price for pkg in packages)

    sale = Sale.objects.create(
        total_amount=total_amount,
        payment_method=payment_method,
        store=request.user.store if request.user.store else None,
        created_by=request.user,
    )

    items_data = []
    for pkg in packages:
        item = SaleItem.objects.create(
            sale=sale,
            package=pkg,
            barcode_value=pkg.barcode_value,
            product_name=pkg.product_name,
            weight=pkg.weight,
            selling_price=pkg.selling_price,
        )
        pkg.status = 'sold'
        pkg.save()
        items_data.append({
            'barcode': item.barcode_value,
            'product_name': item.product_name or '-',
            'weight': str(item.weight),
            'price': str(item.selling_price),
            'price_formatted': f'TSh {item.selling_price:,.0f} /=',
        })

    return JsonResponse({
        'success': True,
        'message': 'Sale completed successfully',
        'receipt_number': sale.receipt_number,
        'total_amount': f'TSh {sale.total_amount:,.0f} /=',
        'payment_method': sale.get_payment_method_display(),
        'sale_date': sale.sale_date.strftime('%d %B %Y, %H:%M'),
        'sold_by': request.user.username,
        'items': items_data,
    })


@login_required
def get_sale_view(request, sale_id):
    if not request.user.is_sales_person and not request.user.is_manager:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    sale = get_object_or_404(Sale, id=sale_id)
    items = []
    for item in sale.items.all():
        items.append({
            'barcode': item.barcode_value,
            'product_name': item.product_name or '-',
            'weight': str(item.weight),
            'price': str(item.selling_price),
            'price_formatted': f'TSh {item.selling_price:,.0f} /=',
        })

    return JsonResponse({
        'id': sale.id,
        'receipt_number': sale.receipt_number,
        'total_amount': f'TSh {sale.total_amount:,.0f} /=',
        'payment_method': sale.get_payment_method_display(),
        'sale_date': sale.sale_date.strftime('%d %B %Y, %H:%M'),
        'sold_by': sale.created_by.username if sale.created_by else '-',
        'items': items,
    })


@login_required
def search_barcode_view(request):
    if not request.user.is_sales_person and not request.user.is_manager:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)

    barcode = request.GET.get('barcode', '').strip()
    if not barcode:
        return JsonResponse({'success': False, 'message': 'No barcode provided'})

    try:
        package = Package.objects.get(barcode_value=barcode)
        if not request.user.is_manager and request.user.store and package.store_id != request.user.store_id:
            return JsonResponse({'success': False, 'message': f'Barcode {barcode} not found in your store'})
        return JsonResponse({
            'success': True,
            'id': package.id,
            'barcode': package.barcode_value,
            'product_name': package.product_name,
            'weight': str(package.weight),
            'price': str(package.selling_price),
            'price_formatted': f'TSh {package.selling_price:,.0f} /=',
            'status': package.status,
            'status_display': package.get_status_display(),
        })
    except Package.DoesNotExist:
        return JsonResponse({'success': False, 'message': f'Barcode {barcode} not found'})


@login_required
def stock_lookup_view(request):
    if not request.user.is_sales_person and not request.user.is_manager:
        return redirect('dashboard')

    from django.core.paginator import Paginator
    from django.db.models import Q

    product_name = request.GET.get('product_name', '').strip()
    weight = request.GET.get('weight', '').strip()
    search = request.GET.get('search', '').strip()

    user = request.user
    if user.is_manager:
        packages = Package.objects.all().order_by('-created_at')
    elif user.store:
        packages = Package.objects.filter(store=user.store).order_by('-created_at')
    else:
        packages = Package.objects.all().order_by('-created_at')

    if product_name:
        packages = packages.filter(product_name__icontains=product_name)
    if weight:
        packages = packages.filter(weight=weight)
    if search:
        packages = packages.filter(
            Q(barcode_value__icontains=search) |
            Q(product_name__icontains=search)
        )

    # Get distinct product names and weights for dropdowns
    product_names = Package.objects.exclude(product_name__isnull=True).exclude(product_name__exact='').values_list('product_name', flat=True).distinct().order_by('product_name')
    weights = Package.objects.values_list('weight', flat=True).distinct().order_by('weight')

    total_count = packages.count()
    in_stock_count = packages.filter(status='in_stock').count()

    paginator = Paginator(packages, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'pos_stock_lookup.html', {
        'packages': page_obj,
        'page_obj': page_obj,
        'product_name': product_name,
        'weight': weight,
        'search': search,
        'product_names': product_names,
        'weights': weights,
        'total_count': total_count,
        'in_stock_count': in_stock_count,
    })


@login_required
def funga_hesabu_view(request):
    if not request.user.is_sales_person and not request.user.is_manager:
        return redirect('dashboard')

    user = request.user
    selected_date = request.GET.get('date', '').strip()
    store_filter = request.GET.get('store_id', '').strip()

    if selected_date:
        try:
            target_date = datetime.datetime.strptime(selected_date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            target_date = datetime.date.today()
            selected_date = target_date.strftime('%Y-%m-%d')
    else:
        target_date = datetime.date.today()
        selected_date = target_date.strftime('%Y-%m-%d')

    day_start = datetime.datetime.combine(target_date, datetime.time.min)
    day_end = datetime.datetime.combine(target_date, datetime.time.max)

    if user.is_manager:
        sales_qs = Sale.objects.filter(sale_date__gte=day_start, sale_date__lte=day_end)
        exp_qs = Expenditure.objects.filter(created_at__gte=day_start, created_at__lte=day_end)
        if store_filter:
            sales_qs = sales_qs.filter(store_id=store_filter)
            exp_qs = exp_qs.filter(store_id=store_filter)
        stores = Store.objects.all().order_by('name')
    elif user.store:
        sales_qs = Sale.objects.filter(sale_date__gte=day_start, sale_date__lte=day_end, store=user.store)
        exp_qs = Expenditure.objects.filter(created_at__gte=day_start, created_at__lte=day_end, store=user.store)
        stores = None
    else:
        sales_qs = Sale.objects.filter(sale_date__gte=day_start, sale_date__lte=day_end, created_by=user)
        exp_qs = Expenditure.objects.filter(created_at__gte=day_start, created_at__lte=day_end, created_by=user)
        stores = None

    sales_count = sales_qs.count()
    sales_total = sales_qs.aggregate(total=Sum('total_amount'))['total'] or 0

    exp_count = exp_qs.count()
    exp_total = exp_qs.aggregate(total=Sum('amount'))['total'] or 0

    net = sales_total - exp_total

    sale_items_qs = SaleItem.objects.filter(sale__in=sales_qs).select_related('package', 'sale')
    items_count = sale_items_qs.count()
    items_weight_total = sum(item.weight for item in sale_items_qs)
    items_value_total = sum(item.selling_price for item in sale_items_qs)

    return render(request, 'funga_hesabu.html', {
        'selected_date': selected_date,
        'sales': sales_qs,
        'sales_count': sales_count,
        'sales_total': f'{sales_total:,.0f}',
        'exp_count': exp_count,
        'exp_total': f'{exp_total:,.0f}',
        'net': f'{net:,.0f}',
        'sale_items': sale_items_qs,
        'items_count': items_count,
        'items_weight_total': f'{items_weight_total:,.2f}',
        'items_value_total': f'{items_value_total:,.0f}',
        'expenditures': exp_qs,
        'stores': stores,
        'store_filter': store_filter,
        'is_manager': user.is_manager,
    })
