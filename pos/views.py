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
from .models import Contact, Sale, SaleItem, Customer, Product, StockMovement
from .forms import CustomerForm, ProductForm, ContactForm

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
    last_of_month = today.replace(day=28) + timezone.timedelta(days=4)
    last_of_month = last_of_month - timezone.timedelta(days=last_of_month.day)

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
        'low_stock_products': low_stock_products,  # Pass low stock info to the template
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
            # Ensure your Product model has a 'barcode' field.
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


def enhanced_sales_report(request):
    """
    Render an enhanced sales report with data for daily, weekly, monthly, and yearly sales.
    (Replace the sample data below with actual queries as needed.)
    """
    daily_sales = [{"day": "2025-02-01", "total": 150000.00}, {"day": "2025-02-02", "total": 200000.00}, {"day": "2025-02-03", "total": 270000.00}, {"day": "2025-02-04", "total": 300000.00}, {"day": "2025-02-05", "total": 400000.00}, {"day": "2025-02-06", "total": 340000.00}, {"day": "2025-02-07", "total": 500000.00}]
    weekly_sales = [{"week": "2025-W01", "total": 550000.00}, {"week": "2025-W02", "total": 760000.00}, {"week": "2025-W03", "total": 670000.00}, {"week": "2025-W04", "total": 531500.00}, {"week": "2025-W05", "total": 430000.00}, {"week": "2025-W06", "total": 500000.00}, {"week": "2025-W07", "total": 450000.00}, {"week": "2025-W08", "total": 250000.00}]
    monthly_sales = [{"month": "2024-01", "total": 5460800.00}, {"month": "2024-02", "total": 4085800.00}, {"month": "2024-03", "total": 1678200.00}, {"month": "2024-04", "total": 3335200.00}, {"month": "2024-05", "total": 3008200.00}, {"month": "2024-06", "total": 4000000.00}, {"month": "2025-07", "total": 3075200.00}, {"month": "2024-08", "total": 2455200.00}, {"month": "2024-09", "total": 2455200.00}, {"month": "2024-10", "total": 2455200.00}, {"month": "2024-11", "total": 2455200.00}, {"month": "2024-12", "total": 2455200.00}, {"month": "2025-01", "total": 2455200.00}, {"month": "2025-02", "total": 2455200.00}]
    yearly_sales = [{"year": "2024", "total": 214355000.00}, {"year": "2025", "total": 63460000.00}]

    context = {
        "daily_sales_json": json.dumps(daily_sales),
        "weekly_sales_json": json.dumps(weekly_sales),
        "monthly_sales_json": json.dumps(monthly_sales),
        "yearly_sales_json": json.dumps(yearly_sales),
    }
    
    return render(request, "pos/enhanced_sales_report.html", context)

# -------------------------
# Settings View
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
