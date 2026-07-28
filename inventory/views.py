from django.contrib.auth.decorators import login_required
from django.db import models
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from inventory.models import Package
from store.models import Store


@login_required
def inventory_dashboard_view(request):
    if not request.user.is_stock_person and not request.user.is_manager:
        return redirect('dashboard')

    # General stats
    total_stock = Package.objects.count()
    in_stock_value = Package.objects.filter(
        status='in_stock'
    ).aggregate(total=Sum('selling_price'))['total'] or 0
    stock_remaining = Package.objects.filter(status='in_stock').count()
    total_sold = Package.objects.filter(status='sold').count()
    sold_amount = Package.objects.filter(
        status='sold'
    ).aggregate(total=Sum('selling_price'))['total'] or 0
    total_value = Package.objects.aggregate(total=Sum('selling_price'))['total'] or 0

    # Monthly breakdown
    monthly = Package.objects.annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        total_stock=Count('id'),
        in_stock_value=Sum('selling_price', filter=models.Q(status='in_stock')),
        total_sold=Count('id', filter=models.Q(status='sold')),
        sold_amount=Sum('selling_price', filter=models.Q(status='sold')),
    ).order_by('-month')[:12]

    monthly_data = []
    for m in monthly:
        monthly_data.append({
            'month': m['month'].strftime('%B %Y'),
            'total_stock': m['total_stock'],
            'in_stock_value': f"{m['in_stock_value'] or 0:,.0f}",
            'total_sold': m['total_sold'],
            'sold_amount': f"{m['sold_amount'] or 0:,.0f}",
        })

    return render(request, 'inventory_dashboard.html', {
        'total_stock': total_stock,
        'in_stock_value': f'{in_stock_value:,.0f}',
        'stock_remaining': stock_remaining,
        'total_sold': total_sold,
        'sold_amount': f'{sold_amount:,.0f}',
        'total_value': f'{total_value:,.0f}',
        'monthly_data': monthly_data,
        'is_stock_person': request.user.is_stock_person,
    })


@login_required
def inventory_list_view(request):
    if not request.user.is_stock_person and not request.user.is_manager:
        return redirect('dashboard')

    user = request.user
    store_filter = request.GET.get('store_id', '').strip()

    if user.is_manager:
        packages = Package.objects.all()
        stores = Store.objects.all().order_by('name')
    else:
        stores = Store.objects.all().order_by('name')
        if user.store:
            packages = Package.objects.filter(store=user.store)
        else:
            packages = Package.objects.all()

    if store_filter and user.is_manager:
        packages = packages.filter(store_id=store_filter)

    return render(request, 'inventory_list.html', {
        'packages': packages,
        'stores': stores,
        'selected_store': store_filter,
        'is_stock_person': user.is_stock_person,
        'is_manager': user.is_manager,
    })


@login_required
def stock_search_view(request):
    if not request.user.is_stock_person and not request.user.is_manager:
        return redirect('dashboard')

    query = request.GET.get('q', '').strip()
    packages = Package.objects.none()

    if query:
        from django.db.models import Q
        packages = Package.objects.filter(
            Q(barcode_value__icontains=query) |
            Q(product_name__icontains=query) |
            Q(batch_number__icontains=query) |
            Q(weight__icontains=query) |
            Q(status__icontains=query)
        )

    return render(request, 'inventory_search.html', {
        'packages': packages,
        'query': query,
        'is_stock_person': request.user.is_stock_person,
    })


@login_required
def create_package_view(request):
    if not request.user.is_stock_person and not request.user.is_manager:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)

    if request.method == 'POST':
        package_id = request.POST.get('package_id')
        product_name = request.POST.get('product_name', '')
        weight = request.POST.get('weight')
        selling_price = request.POST.get('selling_price')
        batch_number = request.POST.get('batch_number', '')
        production_date = request.POST.get('production_date') or None
        status = request.POST.get('status', 'in_stock')
        notes = request.POST.get('notes', '')

        store_id = request.POST.get('store_id', '').strip()

        store = None
        if store_id:
            store = get_object_or_404(Store, id=store_id)
        elif not request.user.is_manager and request.user.store:
            store = request.user.store

        if package_id:
            pkg = get_object_or_404(Package, id=package_id)
            pkg.product_name = product_name
            pkg.weight = weight
            pkg.selling_price = selling_price
            pkg.batch_number = batch_number
            pkg.production_date = production_date
            pkg.status = status
            pkg.notes = notes
            if store:
                pkg.store = store
            pkg.updated_by = request.user
            pkg.save()
            return JsonResponse({
                'success': True,
                'message': 'Package updated successfully.',
                'barcode': pkg.barcode_value,
                'product_name': pkg.product_name,
                'weight': str(pkg.weight),
                'selling_price': str(pkg.selling_price),
            })
        else:
            pkg = Package.objects.create(
                product_name=product_name,
                weight=weight,
                selling_price=selling_price,
                batch_number=batch_number,
                production_date=production_date,
                status=status,
                notes=notes,
                store=store,
                created_by=request.user,
            )
            return JsonResponse({
                'success': True,
                'message': f'Package created. Barcode: {pkg.barcode_value}',
                'barcode': pkg.barcode_value,
                'product_name': pkg.product_name,
                'weight': str(pkg.weight),
                'selling_price': str(pkg.selling_price),
            })

    return JsonResponse({'success': False, 'message': 'Invalid request.'})


@login_required
def get_package_view(request, package_id):
    if not request.user.is_stock_person and not request.user.is_manager:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    pkg = get_object_or_404(Package, id=package_id)
    return JsonResponse({
        'id': pkg.id,
        'product_name': pkg.product_name,
        'weight': str(pkg.weight),
        'selling_price': str(pkg.selling_price),
        'batch_number': pkg.batch_number,
        'production_date': pkg.production_date.isoformat() if pkg.production_date else '',
        'status': pkg.status,
        'notes': pkg.notes,
        'store_id': pkg.store.id if pkg.store else '',
    })


@require_POST
@login_required
def delete_package_view(request, package_id):
    if not request.user.is_stock_person and not request.user.is_manager:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)

    pkg = get_object_or_404(Package, id=package_id)
    barcode = pkg.barcode_value
    pkg.delete()
    return JsonResponse({'success': True, 'message': f'Package "{barcode}" deleted successfully.'})
