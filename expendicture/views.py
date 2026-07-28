import datetime

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from expendicture.models import Expenditure
from store.models import Store


@login_required
def expenditure_list_view(request):
    if not request.user.is_sales_person and not request.user.is_manager and not request.user.is_stock_person:
        return redirect('dashboard')

    user = request.user
    today = datetime.date.today()
    default_start = today.replace(day=1)

    import calendar
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

    if user.is_manager:
        expenditures = Expenditure.objects.filter(
            created_at__gte=start_dt, created_at__lte=end_dt
        )
        stores = Store.objects.all().order_by('name')
        if store_filter:
            expenditures = expenditures.filter(store_id=store_filter)
    else:
        stores = Store.objects.all().order_by('name')
        if user.store:
            expenditures = Expenditure.objects.filter(
                created_at__gte=start_dt, created_at__lte=end_dt, store=user.store
            )
        else:
            expenditures = Expenditure.objects.filter(
                created_at__gte=start_dt, created_at__lte=end_dt, created_by=user
            )

    total_amount = expenditures.aggregate(total=Sum('amount'))['total'] or 0
    count = expenditures.count()

    return render(request, 'expenditure_list.html', {
        'expenditures': expenditures,
        'total_amount': f'{total_amount:,.0f}',
        'count': count,
        'start_date': start_date,
        'end_date': end_date,
        'stores': stores,
        'store_filter': store_filter,
        'is_manager': user.is_manager,
        'is_stock_person': user.is_stock_person,
    })


@login_required
def create_expenditure_view(request):
    if not request.user.is_sales_person and not request.user.is_manager and not request.user.is_stock_person:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)

    if request.method == 'POST':
        amount = request.POST.get('amount')
        purpose = request.POST.get('purpose', '').strip()
        notes = request.POST.get('notes', '').strip()
        store_id = request.POST.get('store_id', '').strip()

        if not amount or not purpose:
            return JsonResponse({'success': False, 'message': 'Amount and purpose are required'})

        store = None
        if store_id:
            store = get_object_or_404(Store, id=store_id)
        elif not request.user.is_manager and request.user.store:
            store = request.user.store

        Expenditure.objects.create(
            amount=amount,
            purpose=purpose,
            notes=notes,
            store=store,
            created_by=request.user,
        )

        return JsonResponse({
            'success': True,
            'message': f'Expenditure of TSh {float(amount):,.0f} recorded successfully.',
        })

    return JsonResponse({'success': False, 'message': 'Invalid request.'})


@require_POST
@login_required
def delete_expenditure_view(request, expenditure_id):
    if not request.user.is_manager:
        return JsonResponse({'success': False, 'message': 'Only managers can delete expenditures'}, status=403)

    exp = get_object_or_404(Expenditure, id=expenditure_id)
    exp.delete()
    return JsonResponse({'success': True, 'message': 'Expenditure deleted successfully.'})
