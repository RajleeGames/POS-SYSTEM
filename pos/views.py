from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth import logout
from django.utils import timezone
from reportlab.pdfgen import canvas
import json
from datetime import timedelta
from django.template.loader import render_to_string
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear
from weasyprint import HTML  # Ensure WeasyPrint is installed in Python 3.13

# Models and Forms
from .models import Contact, Sale, SaleItem, Customer, Product, StockMovement, Expense
from .forms import CustomerForm, ProductForm, ContactForm, ExpenseForm

# -------------------------
# Receipt Views
# -------------------------

@login_required
def receipt_view(request, sale_id):
    """
    Render the HTML receipt template for a given sale.
    """
    sale = get_object_or_404(Sale, id=sale_id)
    context = {'sale': sale}
    if sale.items.exists():
        # For multi–item sales, pass all SaleItem records.
        context['items'] = sale.items.all()
        # Update total_price for display purposes.
        sale.total_price = sale.total_amount
    elif sale.product:
        # Fallback for single–item sale: create a one-item list.
        fallback_item = {
            'product': sale.product,
            'quantity': sale.quantity,
            'price': sale.product.price,
            'total': sale.total_price,
        }
        context['fallback_items'] = [fallback_item]
    return render(request, 'pos/receipt_template.html', context)

@login_required
def generate_receipt_pdf(request, sale_id):
    """
    Generate a PDF receipt for the given sale.
    """
    sale = get_object_or_404(Sale, id=sale_id)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{sale.id}.pdf"'
    
    p = canvas.Canvas(response)
    
    # Header: Title and sale information.
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 800, f"Receipt for Sale ID: {sale.id}")
    p.setFont("Helvetica", 12)
    p.drawString(100, 780, f"Date: {sale.date.strftime('%Y-%m-%d %H:%M:%S')}")
    p.drawString(100, 760, f"Payment Method: {sale.payment_method}")
    if sale.customer:
        p.drawString(100, 740, f"Customer: {sale.customer.name}")
    else:
        p.drawString(100, 740, "Customer: Walk-in Customer")
    
    # Column titles.
    y = 710
    p.setFont("Helvetica-Bold", 12)
    p.drawString(100, y, "Product")
    p.drawString(300, y, "Quantity")
    p.drawString(400, y, "Price")
    p.drawString(500, y, "Total")
    y -= 20
    p.setFont("Helvetica", 12)
    
    # Check if there are related SaleItem records (multi–item sale)
    sale_items = sale.items.all()
    if sale_items.exists():
        for item in sale_items:
            p.drawString(100, y, item.product.name)
            p.drawString(300, y, str(item.quantity))
            p.drawString(400, y, f"${item.product.price:.2f}")
            p.drawString(500, y, f"${item.total_price:.2f}")
            y -= 20
            if y < 50:  # If space is low, start a new page.
                p.showPage()
                y = 800
                p.setFont("Helvetica", 12)
    else:
        # Fallback for single–item sale.
        if sale.product:
            p.drawString(100, y, sale.product.name)
            p.drawString(300, y, str(sale.quantity))
            p.drawString(400, y, f"${sale.product.price:.2f}")
            p.drawString(500, y, f"${sale.total_price:.2f}")
            y -= 20
        else:
            p.drawString(100, y, "No items found for this sale.")
    
    # Save the PDF (do not add an extra showPage() to avoid a blank final page).
    p.save()
    
    return response

# -------------------------
# Sales Views
# -------------------------

@login_required
def sales_history(request):
    """
    Display the sales history, ordered by the 'date' field.
    """
    sales = Sale.objects.all().order_by('-date')
    return render(request, 'pos/sales_history.html', {'sales': sales})

def sales_report(request):
    """
    Display the sales report, ordered by the 'date' field.
    """
    today = timezone.localtime(timezone.now()).date()
    first_of_month = today.replace(day=1)
    last_of_month = today.replace(day=28) + timedelta(days=4)
    last_of_month = last_of_month - timedelta(days=last_of_month.day)

    total_sales_today = Sale.objects.filter(date__date=today).aggregate(Sum('total_price'))['total_price__sum'] or 0
    total_sales_month = Sale.objects.filter(date__date__gte=first_of_month, date__date__lte=last_of_month).aggregate(Sum('total_price'))['total_price__sum'] or 0
    sales = Sale.objects.all().order_by('-date')
    total_sales = Sale.objects.aggregate(total_price_sum=Sum('total_price'))['total_price_sum'] or 0

    return render(request, 'pos/sales_report.html', {
        'sales': sales,
        'total_sales': total_sales,
        'total_sales_today': total_sales_today,
        'total_sales_month': total_sales_month
    })

def logout_view(request):
    """
    Log out the current user.
    """
    logout(request)
    return redirect('login')

# -------------------------
# Product Views
# -------------------------

def product_list(request):
    """
    List all products.
    """
    products = Product.objects.all()
    return render(request, 'pos/product_list.html', {'products': products})

def view_product(request, product_id):
    """
    View details of a single product.
    """
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'product_detail.html', {'product': product})

def add_product(request):
    """
    Add a new product.
    """
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'add_product.html', {'form': form})

def edit_product(request, product_id):
    """
    Edit an existing product.
    """
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'edit_product.html', {'form': form, 'product': product})

def delete_product(request, product_id):
    """
    Delete a product.
    """
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    return redirect('product_list')

# -------------------------
# POS System Views
# -------------------------

@login_required
def pos(request):
    """
    Main POS system view.
    """
    products = Product.objects.all()
    customers = Customer.objects.all()

    if request.method == "POST":
        product_id = request.POST.get("product")
        quantity_str = request.POST.get("quantity")
        customer_id = request.POST.get("customer")
        
        try:
            quantity = int(quantity_str)
        except (ValueError, TypeError):
            messages.error(request, "Invalid quantity provided.")
            return render(request, 'pos/pos.html', {
                'products': products,
                'customers': customers,
                'message': "Invalid quantity provided."
            })
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return render(request, 'pos/pos.html', {
                'products': products,
                'customers': customers,
                'message': "Product not found!"
            })
        
        if product.stock >= quantity:
            total_price = product.price * quantity
            sale = Sale(
                product=product,
                quantity=quantity,
                total_price=total_price,
                cashier=request.user
            )
            
            if customer_id:
                try:
                    customer = Customer.objects.get(id=customer_id)
                    sale.customer = customer
                except Customer.DoesNotExist:
                    messages.error(request, "Customer not found.")
                    return render(request, 'pos/pos.html', {
                        'products': products,
                        'customers': customers,
                        'message': "Customer not found."
                    })
            sale.save()
            try:
                product.reduce_stock(quantity)
            except Exception as e:
                messages.error(request, f"Error reducing stock: {str(e)}")
                return render(request, 'pos/pos.html', {
                    'products': products,
                    'customers': customers,
                    'message': "Error reducing stock."
                })
            return render(request, 'pos/pos.html', {
                'products': products,
                'customers': customers,
                'message': f"Sale completed! Total: ${total_price}"
            })
        else:
            return render(request, 'pos/pos.html', {
                'products': products,
                'customers': customers,
                'message': "Insufficient stock!"
            })
    return render(request, 'pos/pos.html', {'products': products, 'customers': customers})

def index(request):
    """
    Index page view.
    """
    return render(request, 'pos/index.html')

@login_required
def dashboard(request):
    """
    Dashboard view.
    """
    return render(request, 'pos/dashboard.html')

def add_customer(request):
    """
    Add a new customer.
    """
    if request.method == "POST":
        form = CustomerForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('add_customer')
    else:
        form = CustomerForm()
    customers = Customer.objects.all()
    return render(request, 'pos/add_customer.html', {'form': form, 'customers': customers})

def signup_view(request):
    """
    User signup view.
    """
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

@login_required
def make_sale(request):
    """
    Make Sale view for processing a sale with multiple items.
    """
    products = Product.objects.all()
    customers = Customer.objects.all()

    if request.method == "POST":
        product_ids = request.POST.getlist('product[]')
        quantity_list = request.POST.getlist('quantity[]')
        customer_id = request.POST.get('customer', None)
        payment_method = request.POST.get('payment_method', 'cash')

        if not product_ids or not quantity_list:
            messages.error(request, "No items selected!")
            return render(request, 'pos/make_sale.html', {
                'products': products,
                'customers': customers,
                'message': "No items selected."
            })

        sale = Sale(customer=None, payment_method=payment_method, cashier=request.user)
        if customer_id:
            try:
                customer = Customer.objects.get(id=customer_id)
                sale.customer = customer
            except Customer.DoesNotExist:
                messages.error(request, "Customer not found.")
                return render(request, 'pos/make_sale.html', {
                    'products': products,
                    'customers': customers,
                    'message': "Customer not found."
                })
        sale.save()

        total_amount = 0
        for prod_id, qty_str in zip(product_ids, quantity_list):
            try:
                quantity = int(qty_str)
            except (ValueError, TypeError):
                messages.error(request, "Invalid quantity provided.")
                return render(request, 'pos/make_sale.html', {
                    'products': products,
                    'customers': customers,
                    'message': "Invalid quantity provided."
                })

            try:
                product = Product.objects.get(id=prod_id)
            except Product.DoesNotExist:
                messages.error(request, "Product not found!")
                return render(request, 'pos/make_sale.html', {
                    'products': products,
                    'customers': customers,
                    'message': "Product not found!"
                })

            if product.stock < quantity:
                messages.error(request, f"Insufficient stock for {product.name}!")
                return render(request, 'pos/make_sale.html', {
                    'products': products,
                    'customers': customers,
                    'message': f"Insufficient stock for {product.name}!"
                })

            line_total = product.price * quantity
            total_amount += line_total

            SaleItem.objects.create(
                sale=sale,
                product=product,
                quantity=quantity,
                total_price=line_total
            )

            try:
                product.reduce_stock(quantity)
            except Exception as e:
                messages.error(request, f"Error reducing stock for {product.name}: {str(e)}")
                return render(request, 'pos/make_sale.html', {
                    'products': products,
                    'customers': customers,
                    'message': f"Error reducing stock for {product.name}."
                })

        sale.total_amount = total_amount
        sale.save()

        messages.success(request, f"Sale completed! Total: ${total_amount}")
        return redirect('receipt_view', sale_id=sale.id)

    return render(request, 'pos/make_sale.html', {'products': products, 'customers': customers})

def complete_sale(request):
    """
    Complete Sale view for processing a sale with payment method.
    """
    if request.method == "POST":
        product_id = request.POST.get('product_id')
        quantity_str = request.POST.get('quantity')
        customer_id = request.POST.get('customer_id', None)
        payment_method = request.POST.get('payment_method', 'cash')
        
        try:
            quantity = int(quantity_str)
        except (ValueError, TypeError):
            messages.error(request, "Invalid quantity provided.")
            return redirect('pos')
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            messages.error(request, "Product not found.")
            return redirect('pos')
        
        try:
            product.reduce_stock(quantity)
        except Exception as e:
            messages.error(request, f"Error reducing stock: {str(e)}")
            return redirect('pos')
        
        total_price = product.price * quantity
        
        try:
            sale = Sale.objects.create(
                product=product,
                quantity=quantity,
                total_price=total_price,
                payment_method=payment_method,
                cashier=request.user
            )
        except Exception as e:
            messages.error(request, f"Error creating sale: {str(e)}")
            return redirect('pos')
        
        if customer_id:
            try:
                customer = Customer.objects.get(id=customer_id)
                sale.customer = customer
                sale.save()
            except Customer.DoesNotExist:
                messages.error(request, "Customer not found.")
                return redirect('pos')
        
        messages.success(request, f"Sale completed for {product.name}. Total: ${total_price:.2f}")
        return redirect('sale_success')
    return render(request, 'pos/pos.html')

def sale_success(request):
    """
    View to show sale success message.
    """
    return render(request, 'pos/sale_success.html')

@login_required
def cashier_dashboard(request):
    """
    Cashier dashboard view with low stock notifications.
    """
    products = Product.objects.all()
    customers = Customer.objects.all()
    recent_sales = Sale.objects.order_by('-date')[:10]
    
    # Query products with low stock (threshold: less than 10)
    low_stock_products = Product.objects.filter(stock__lt=10)

    if request.method == "POST":
        product_id = request.POST.get('product')
        quantity_str = request.POST.get('quantity')
        customer_id = request.POST.get('customer')
        payment_method = request.POST.get('payment_method', 'cash')
        
        try:
            quantity = int(quantity_str)
            product = Product.objects.get(id=product_id)
        except (ValueError, Product.DoesNotExist):
            messages.error(request, "Invalid product or quantity.")
            return redirect('cashier_dashboard')
        
        if product.stock < quantity:
            messages.error(request, "Insufficient stock!")
        else:
            total_price = product.price * quantity
            sale = Sale(
                product=product,
                quantity=quantity,
                total_price=total_price,
                payment_method=payment_method,
                cashier=request.user
            )
            if customer_id:
                try:
                    customer = Customer.objects.get(id=customer_id)
                    sale.customer = customer
                except Customer.DoesNotExist:
                    messages.error(request, "Selected customer does not exist.")
                    return redirect('cashier_dashboard')
            try:
                sale.save()
                messages.success(request, f"Sale completed! Total: Tsh{total_price}")
            except ValueError as e:
                messages.error(request, str(e))
            return redirect('cashier_dashboard')
    
    context = {
        'products': products,
        'customers': customers,
        'recent_sales': recent_sales,
        'low_stock_products': low_stock_products,
    }
    return render(request, 'pos/cashier_dashboard.html', context)

# -------------------------
# AJAX Views for Barcode Scanning & Enhanced Product Search
# -------------------------

def lookup_by_barcode(request):
    """
    Return product details based on a scanned barcode.
    Expect a GET parameter 'barcode'.
    """
    barcode = request.GET.get('barcode', None)
    if barcode:
        try:
            product = Product.objects.get(barcode=barcode)
            data = {
                'id': product.id,
                'name': product.name,
                'price': float(product.price),
                'stock': product.stock,
            }
            return JsonResponse({'status': 'success', 'product': data})
        except Product.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Product not found.'})
    return JsonResponse({'status': 'error', 'message': 'No barcode provided.'})

def search_products(request):
    """
    AJAX view to return a list of products filtered by a search query.
    Additional filters (such as category or price range) can be added as needed.
    """
    query = request.GET.get('query', '')
    products = Product.objects.filter(name__icontains=query)[:10]

    product_list = [{
        'id': product.id,
        'name': product.name,
        'price': float(product.price),
        'stock': product.stock,
    } for product in products]

    return JsonResponse({'status': 'success', 'products': product_list})

def search_product(request):
    """
    Return a JSON response with products matching the query.
    """
    query = request.GET.get('query', '')
    products = Product.objects.filter(name__icontains=query)[:10]
    product_list = [{'name': product.name, 'price': product.price} for product in products]
    return JsonResponse({'products': product_list})

def add_to_sale(product_id):
    """
    (Optional) Helper function for adding a product to the sale.
    """
    get_object_or_404(Product, id=product_id)
    return redirect('cashier_dashboard')

# -------------------------
# Enhanced Sales Report & Export/Print Views
# -------------------------

@login_required
def enhanced_sales_report(request):
    """
    Render an enhanced sales report with actual data for daily, weekly, monthly, and yearly sales,
    along with aggregated numbers for the current month: total sales, expenses, and net profit.
    """
    sales_qs = Sale.objects.all()

    # Daily Sales: Group sales by day
    daily_sales_qs = sales_qs.annotate(day=TruncDay('date')).values('day').annotate(total=Sum('total_amount')).order_by('day')
    daily_sales = [{'day': sale['day'].strftime('%Y-%m-%d'), 'total': float(sale['total'])} for sale in daily_sales_qs]

    # Weekly Sales: Group sales by week
    weekly_sales_qs = sales_qs.annotate(week=TruncWeek('date')).values('week').annotate(total=Sum('total_amount')).order_by('week')
    weekly_sales = [{'week': sale['week'].strftime('%Y-%m-%d'), 'total': float(sale['total'])} for sale in weekly_sales_qs]

    # Monthly Sales: Group sales by month
    monthly_sales_qs = sales_qs.annotate(month=TruncMonth('date')).values('month').annotate(total=Sum('total_amount')).order_by('month')
    monthly_sales = [{'month': sale['month'].strftime('%Y-%m'), 'total': float(sale['total'])} for sale in monthly_sales_qs]

    # Yearly Sales: Group sales by year
    yearly_sales_qs = sales_qs.annotate(year=TruncYear('date')).values('year').annotate(total=Sum('total_amount')).order_by('year')
    yearly_sales = [{'year': sale['year'].strftime('%Y'), 'total': float(sale['total'])} for sale in yearly_sales_qs]

    # Aggregated numbers for current month
    today = timezone.now().date()
    monthly_sales_total = Sale.objects.filter(date__year=today.year, date__month=today.month).aggregate(total=Sum('total_amount'))['total'] or 0
    total_expenses = Expense.objects.filter(date__year=today.year, date__month=today.month).aggregate(total=Sum('amount'))['total'] or 0
    net_profit = monthly_sales_total - total_expenses
    todays_sales = Sale.objects.filter(date__date=today).aggregate(total=Sum('total_amount'))['total'] or 0

    context = {
        "daily_sales_json": json.dumps(daily_sales),
        "weekly_sales_json": json.dumps(weekly_sales),
        "monthly_sales_json": json.dumps(monthly_sales),
        "yearly_sales_json": json.dumps(yearly_sales),
        "monthly_sales_total": monthly_sales_total,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "todays_sales": todays_sales,
    }
    return render(request, "pos/enhanced_sales_report.html", context)

@login_required
def export_pdf(request):
    """
    Export the enhanced sales report as a PDF using WeasyPrint.
    """
    sales_qs = Sale.objects.all()

    daily_sales_qs = sales_qs.annotate(day=TruncDay('date')).values('day').annotate(total=Sum('total_amount')).order_by('day')
    daily_sales = [{'day': sale['day'].strftime('%Y-%m-%d'), 'total': float(sale['total'])} for sale in daily_sales_qs]

    weekly_sales_qs = sales_qs.annotate(week=TruncWeek('date')).values('week').annotate(total=Sum('total_amount')).order_by('week')
    weekly_sales = [{'week': sale['week'].strftime('%Y-%m-%d'), 'total': float(sale['total'])} for sale in weekly_sales_qs]

    monthly_sales_qs = sales_qs.annotate(month=TruncMonth('date')).values('month').annotate(total=Sum('total_amount')).order_by('month')
    monthly_sales = [{'month': sale['month'].strftime('%Y-%m'), 'total': float(sale['total'])} for sale in monthly_sales_qs]

    yearly_sales_qs = sales_qs.annotate(year=TruncYear('date')).values('year').annotate(total=Sum('total_amount')).order_by('year')
    yearly_sales = [{'year': sale['year'].strftime('%Y'), 'total': float(sale['total'])} for sale in yearly_sales_qs]

    today = timezone.now().date()
    monthly_sales_total = Sale.objects.filter(date__year=today.year, date__month=today.month).aggregate(total=Sum('total_amount'))['total'] or 0
    total_expenses = Expense.objects.filter(date__year=today.year, date__month=today.month).aggregate(total=Sum('amount'))['total'] or 0
    net_profit = monthly_sales_total - total_expenses
    todays_sales = Sale.objects.filter(date__date=today).aggregate(total=Sum('total_amount'))['total'] or 0

    context = {
        "daily_sales_json": json.dumps(daily_sales),
        "weekly_sales_json": json.dumps(weekly_sales),
        "monthly_sales_json": json.dumps(monthly_sales),
        "yearly_sales_json": json.dumps(yearly_sales),
        "monthly_sales_total": monthly_sales_total,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "todays_sales": todays_sales,
    }
    html_string = render_to_string("pos/enhanced_sales_report.html", context)
    html = HTML(string=html_string)
    pdf = html.write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="sales_report.pdf"'
    return response

@login_required
def print_enhanced_report(request):
    """
    Render a printable version of the enhanced sales report.
    This view uses a print-optimized template: pos/print_enhanced_report.html.
    """
    sales_qs = Sale.objects.all()

    daily_sales_qs = sales_qs.annotate(day=TruncDay('date')).values('day').annotate(total=Sum('total_amount')).order_by('day')
    daily_sales = [{'day': sale['day'].strftime('%Y-%m-%d'), 'total': float(sale['total'])} for sale in daily_sales_qs]

    weekly_sales_qs = sales_qs.annotate(week=TruncWeek('date')).values('week').annotate(total=Sum('total_amount')).order_by('week')
    weekly_sales = [{'week': sale['week'].strftime('%Y-%m-%d'), 'total': float(sale['total'])} for sale in weekly_sales_qs]

    monthly_sales_qs = sales_qs.annotate(month=TruncMonth('date')).values('month').annotate(total=Sum('total_amount')).order_by('month')
    monthly_sales = [{'month': sale['month'].strftime('%Y-%m'), 'total': float(sale['total'])} for sale in monthly_sales_qs]

    yearly_sales_qs = sales_qs.annotate(year=TruncYear('date')).values('year').annotate(total=Sum('total_amount')).order_by('year')
    yearly_sales = [{'year': sale['year'].strftime('%Y'), 'total': float(sale['total'])} for sale in yearly_sales_qs]

    today = timezone.now().date()
    monthly_sales_total = Sale.objects.filter(date__year=today.year, date__month=today.month).aggregate(total=Sum('total_amount'))['total'] or 0
    total_expenses = Expense.objects.filter(date__year=today.year, date__month=today.month).aggregate(total=Sum('amount'))['total'] or 0
    net_profit = monthly_sales_total - total_expenses
    todays_sales = Sale.objects.filter(date__date=today).aggregate(total=Sum('total_amount'))['total'] or 0

    context = {
        "daily_sales_json": json.dumps(daily_sales),
        "weekly_sales_json": json.dumps(weekly_sales),
        "monthly_sales_json": json.dumps(monthly_sales),
        "yearly_sales_json": json.dumps(yearly_sales),
        "monthly_sales_total": monthly_sales_total,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "todays_sales": todays_sales,
    }
    return render(request, "pos/print_enhanced_report.html", context)

@login_required
def print_receipt(request, sale_id):
    """
    Render a printable receipt for a given sale using the template pos/print_receipt.html.
    """
    sale = get_object_or_404(Sale, id=sale_id)
    return render(request, "pos/print_receipt.html", {"sale": sale})

# -------------------------
# Settings, Contact, and Misc Views
# -------------------------

@login_required
def settings_view(request):
    """
    Render the settings page.
    """
    return render(request, 'pos/settings.html')

def get_product_details(request):
    """
    Alternate AJAX view to retrieve product details by barcode.
    """
    barcode = request.GET.get("barcode")
    try:
        product = Product.objects.get(barcode=barcode)
        return JsonResponse({
            "success": True,
            "id": product.id,
            "name": product.name,
            "price": float(product.price)
        })
    except Product.DoesNotExist:
        return JsonResponse({"success": False, "message": "Product not found"})

def contacts_list(request):
    contacts = Contact.objects.all().order_by('-created_at')
    return render(request, 'pos/contacts_list.html', {'contacts': contacts})

def add_contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('contacts_list')
    else:
        form = ContactForm()
    return render(request, 'pos/contact_form.html', {'form': form, 'title': 'Add Contact'})

def edit_contact(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    if request.method == 'POST':
        form = ContactForm(request.POST, instance=contact)
        if form.is_valid():
            form.save()
            return redirect('contacts_list')
    else:
        form = ContactForm(instance=contact)
    return render(request, 'pos/contact_form.html', {'form': form, 'title': 'Edit Contact'})

def delete_contact(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    if request.method == 'POST':
        contact.delete()
        return redirect('contacts_list')
    return render(request, 'pos/delete_contact.html', {'contact': contact})

def stock_movement_list(request):
    movements = StockMovement.objects.all().order_by('-timestamp')
    return render(request, 'pos/stock_movement.html', {'movements': movements})

# -------------------------
# Expense Views
# -------------------------

def add_expense(request):
    if request.method == "POST":
        form = ExpenseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('expense_list')
    else:
        form = ExpenseForm()
    return render(request, 'pos/add_expense.html', {'form': form})

def calculate_monthly_earnings():
    current_month = timezone.now().month
    # Aggregate monthly earnings using the total_amount field.
    earnings = Sale.objects.filter(date__month=current_month).aggregate(total=Sum('total_amount'))['total'] or 0
    return earnings

def expense_list(request):
    current_month = timezone.now().month
    # Retrieve all expenses for the current month.
    expenses = Expense.objects.filter(date__month=current_month)
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
    monthly_earnings = calculate_monthly_earnings()
    net_profit = monthly_earnings - total_expenses

    context = {
        'expenses': expenses,
        'total_expenses': total_expenses,
        'monthly_earnings': monthly_earnings,
        'net_profit': net_profit,
    }
    return render(request, 'pos/expense_list.html', context)
