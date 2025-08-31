from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
from django.core.management import call_command
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import Claim, ClaimDetail, ClaimNote, ClaimFlag
import json
import csv
import io
import os
import tempfile


def claim_list(request):
    """Display list of all claims with search and filtering"""
    claims = Claim.objects.select_related('detail').prefetch_related('notes', 'flags')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        claims = claims.filter(
            Q(patient_name__icontains=search_query) |
            Q(insurer_name__icontains=search_query) |
            Q(id__icontains=search_query)
        )
    
    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        claims = claims.filter(status=status_filter)
    
    # Flag filter
    flagged_filter = request.GET.get('flagged', '')
    if flagged_filter == 'true':
        claims = claims.filter(is_flagged=True)
    elif flagged_filter == 'false':
        claims = claims.filter(is_flagged=False)
    
    # Pagination
    paginator = Paginator(claims, 25)  # Show 25 claims per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'flagged_filter': flagged_filter,
        'status_choices': Claim.STATUS_CHOICES,
    }
    
    return render(request, 'claims/claim_list.html', context)


def claim_detail(request, claim_id):
    """Display detailed view of a specific claim"""
    claim = get_object_or_404(Claim, id=claim_id)
    
    # Get or create claim detail
    claim_detail, created = ClaimDetail.objects.get_or_create(claim=claim)
    
    # Get notes and flags
    notes = claim.notes.all()
    flags = claim.flags.all()
    
    context = {
        'claim': claim,
        'claim_detail': claim_detail,
        'notes': notes,
        'flags': flags,
    }
    
    return render(request, 'claims/claim_detail.html', context)


@require_http_methods(["POST"])
def toggle_flag(request, claim_id):
    """Toggle flag status for a claim via HTMX"""
    claim = get_object_or_404(Claim, id=claim_id)
    
    if claim.is_flagged:
        # Unflag the claim
        claim.is_flagged = False
        claim.flags.filter(is_resolved=False).update(
            is_resolved=True,
            resolved_by=request.user if request.user.is_authenticated else None,
            resolved_at=timezone.now()
        )
        flag_status = "unflagged"
        button_class = "btn-outline-warning"
        button_text = "🚩 Flag"
    else:
        # Flag the claim
        claim.is_flagged = True
        if request.user.is_authenticated:
            ClaimFlag.objects.create(
                claim=claim,
                reason='review_needed',
                description='Flagged via web interface',
                flagged_by=request.user
            )
        else:
            # For anonymous users, create a basic flag without user tracking
            ClaimFlag.objects.create(
                claim=claim,
                reason='review_needed',
                description='Flagged by anonymous user',
                flagged_by=None
            )
        flag_status = "flagged"
        button_class = "btn-warning"
        button_text = "🏳️ Unflag"
    
    claim.updated_by = request.user if request.user.is_authenticated else None
    claim.save()
    
    # Return HTMX response
    return HttpResponse(f'''
        <button hx-post="/claims/{claim_id}/toggle-flag/" 
                hx-target="this" 
                hx-swap="outerHTML"
                class="btn {button_class} btn-sm">
            {button_text}
        </button>
    ''')


@require_http_methods(["POST"])
def add_note(request, claim_id):
    """Add a note to a claim via HTMX"""
    claim = get_object_or_404(Claim, id=claim_id)
    content = request.POST.get('content', '').strip()
    
    if content and request.user.is_authenticated:
        note = ClaimNote.objects.create(
            claim=claim,
            content=content,
            created_by=request.user
        )
        
        # Return the new note HTML
        return HttpResponse(f'''
            <div class="note-item mb-2 p-2 border rounded">
                <div class="note-content">{note.content}</div>
                <small class="text-muted">
                    By {note.created_by.username} on {note.created_at.strftime('%b %d, %Y at %I:%M %p')}
                </small>
            </div>
        ''')
    
    return HttpResponse('<div class="alert alert-danger">Error adding note</div>')


@require_http_methods(["POST"])
def update_status(request, claim_id):
    """Update claim status via HTMX"""
    claim = get_object_or_404(Claim, id=claim_id)
    new_status = request.POST.get('status')
    
    if new_status in dict(Claim.STATUS_CHOICES):
        claim.status = new_status
        claim.updated_by = request.user if request.user.is_authenticated else None
        claim.save()
        
        # Get status display name and CSS class
        status_display = claim.get_status_display()
        status_class = {
            'pending': 'warning',
            'approved': 'success',
            'denied': 'danger',
            'processing': 'info',
            'review': 'secondary'
        }.get(new_status, 'secondary')
        
        return HttpResponse(f'''
            <span class="badge bg-{status_class}">{status_display}</span>
        ''')
    
    return HttpResponse('<span class="badge bg-danger">Error</span>')


def search_claims(request):
    """HTMX endpoint for live search"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return HttpResponse('')
    
    claims = Claim.objects.filter(
        Q(patient_name__icontains=query) |
        Q(insurer_name__icontains=query) |
        Q(id__icontains=query)
    )[:10]  # Limit to 10 results
    
    html = ''
    for claim in claims:
        html += f'''
            <div class="search-result p-2 border-bottom">
                <a href="/claims/{claim.id}/" class="text-decoration-none">
                    <strong>{claim.patient_name}</strong> - {claim.insurer_name}
                    <br><small class="text-muted">Claim #{claim.id}</small>
                </a>
            </div>
        '''
    
    return HttpResponse(html)


def dashboard(request):
    """Dashboard with comprehensive summary statistics"""
    from django.db.models import Sum, Avg, Count, Q, F
    from decimal import Decimal
    
    # Basic counts
    total_claims = Claim.objects.count()
    flagged_claims = Claim.objects.filter(is_flagged=True).count()
    
    # Financial statistics
    financial_stats = Claim.objects.aggregate(
        total_billed=Sum('billed_amount'),
        total_paid=Sum('paid_amount'),
        avg_billed=Avg('billed_amount'),
        avg_paid=Avg('paid_amount')
    )
    
    # Calculate underpayment statistics
    total_billed = financial_stats['total_billed'] or Decimal('0')
    total_paid = financial_stats['total_paid'] or Decimal('0')
    total_underpayment = total_billed - total_paid
    avg_underpayment = financial_stats['avg_billed'] - financial_stats['avg_paid'] if financial_stats['avg_billed'] and financial_stats['avg_paid'] else Decimal('0')
    
    # Claims with significant underpayment (more than 50% difference)
    underpaid_claims = Claim.objects.filter(
        billed_amount__gt=F('paid_amount') * 2
    ).count()
    
    # Status breakdown
    status_counts = {}
    for status_code, status_name in Claim.STATUS_CHOICES:
        status_counts[status_name] = Claim.objects.filter(status=status_code).count()
    
    # Top insurers by claim count
    top_insurers = Claim.objects.values('insurer_name').annotate(
        claim_count=Count('id'),
        total_billed=Sum('billed_amount'),
        total_paid=Sum('paid_amount')
    ).order_by('-claim_count')[:5]
    
    # Recent activities (claims, notes, flags)
    recent_claims = Claim.objects.order_by('-created_at')[:5]
    recent_notes = ClaimNote.objects.select_related('claim', 'created_by').order_by('-created_at')[:5]
    recent_flags = ClaimFlag.objects.select_related('claim', 'flagged_by').order_by('-created_at')[:5]
    
    # Monthly trends (simplified for demo)
    monthly_stats = Claim.objects.extra(
        select={'month': "strftime('%%Y-%%m', created_at)"}
    ).values('month').annotate(
        count=Count('id'),
        total_billed=Sum('billed_amount'),
        total_paid=Sum('paid_amount')
    ).order_by('-month')[:6]
    
    # Denial analysis
    denied_claims = Claim.objects.filter(status='denied')
    denial_stats = {
        'count': denied_claims.count(),
        'total_amount': denied_claims.aggregate(total=Sum('billed_amount'))['total'] or Decimal('0')
    }
    
    # Top denial reasons
    top_denial_reasons = ClaimDetail.objects.filter(
        claim__status='denied',
        denial_reason__isnull=False
    ).exclude(denial_reason='').values('denial_reason').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    context = {
        'total_claims': total_claims,
        'flagged_claims': flagged_claims,
        'status_counts': status_counts,
        'recent_claims': recent_claims,
        'recent_notes': recent_notes,
        'recent_flags': recent_flags,
        'financial_stats': {
            'total_billed': total_billed,
            'total_paid': total_paid,
            'total_underpayment': total_underpayment,
            'avg_billed': financial_stats['avg_billed'] or Decimal('0'),
            'avg_paid': financial_stats['avg_paid'] or Decimal('0'),
            'avg_underpayment': avg_underpayment,
            'underpaid_claims': underpaid_claims,
        },
        'top_insurers': top_insurers,
        'monthly_stats': monthly_stats,
        'denial_stats': denial_stats,
        'top_denial_reasons': top_denial_reasons,
    }
    
    return render(request, 'claims/dashboard.html', context)


def csv_upload(request):
    """CSV upload interface"""
    if request.method == 'POST':
        return handle_csv_upload(request)
    
    # Get current data statistics for the upload page
    current_stats = {
        'total_claims': Claim.objects.count(),
        'total_details': ClaimDetail.objects.count(),
    }
    
    return render(request, 'claims/csv_upload.html', {'current_stats': current_stats})


def handle_csv_upload(request):
    """Handle CSV file upload and processing"""
    try:
        claims_file = request.FILES.get('claims_file')
        details_file = request.FILES.get('details_file')
        upload_mode = request.POST.get('upload_mode', 'append')  # append or overwrite
        
        if not claims_file or not details_file:
            messages.error(request, 'Both claims and details CSV files are required.')
            return redirect('claims:csv_upload')
        
        # Validate file formats
        if not (claims_file.name.endswith('.csv') and details_file.name.endswith('.csv')):
            messages.error(request, 'Please upload CSV files only.')
            return redirect('claims:csv_upload')
        
        # Save uploaded files temporarily
        with tempfile.TemporaryDirectory() as temp_dir:
            claims_path = os.path.join(temp_dir, 'claims.csv')
            details_path = os.path.join(temp_dir, 'details.csv')
            
            # Write files to temp directory
            with open(claims_path, 'wb+') as destination:
                for chunk in claims_file.chunks():
                    destination.write(chunk)
            
            with open(details_path, 'wb+') as destination:
                for chunk in details_file.chunks():
                    destination.write(chunk)
            
            # Validate CSV structure
            validation_errors = validate_csv_files(claims_path, details_path)
            if validation_errors:
                for error in validation_errors:
                    messages.error(request, error)
                return redirect('claims:csv_upload')
            
            # Count records to be imported
            with open(claims_path, 'r') as f:
                claims_count = sum(1 for line in f) - 1  # Subtract header
            
            with open(details_path, 'r') as f:
                details_count = sum(1 for line in f) - 1  # Subtract header
            
            # Import data using management command
            try:
                if upload_mode == 'overwrite':
                    call_command('import_claims', 
                               claims_file=claims_path, 
                               details_file=details_path, 
                               clear=True)
                    messages.success(request, f'Successfully imported {claims_count} claims and {details_count} details (overwrote existing data).')
                else:
                    call_command('import_claims', 
                               claims_file=claims_path, 
                               details_file=details_path)
                    messages.success(request, f'Successfully imported {claims_count} claims and {details_count} details (appended to existing data).')
                
            except Exception as e:
                messages.error(request, f'Import failed: {str(e)}')
                return redirect('claims:csv_upload')
    
    except Exception as e:
        messages.error(request, f'Upload failed: {str(e)}')
        return redirect('claims:csv_upload')
    
    return redirect('claims:dashboard')


def validate_csv_files(claims_path, details_path):
    """Validate CSV file structure and content"""
    errors = []
    
    # Expected headers
    expected_claims_headers = ['id', 'patient_name', 'billed_amount', 'paid_amount', 'status', 'insurer_name', 'discharge_date']
    expected_details_headers = ['id', 'claim_id', 'denial_reason', 'cpt_codes']
    
    try:
        # Validate claims file
        with open(claims_path, 'r') as f:
            reader = csv.reader(f, delimiter='|')
            headers = next(reader)
            if headers != expected_claims_headers:
                errors.append(f'Claims file headers incorrect. Expected: {expected_claims_headers}, Got: {headers}')
            
            # Check first few rows for basic data validation
            for i, row in enumerate(reader):
                if i >= 3:  # Check only first 3 rows
                    break
                if len(row) != len(expected_claims_headers):
                    errors.append(f'Claims file row {i+2} has {len(row)} columns, expected {len(expected_claims_headers)}')
                    break
    
    except Exception as e:
        errors.append(f'Error reading claims file: {str(e)}')
    
    try:
        # Validate details file
        with open(details_path, 'r') as f:
            reader = csv.reader(f, delimiter='|')
            headers = next(reader)
            if headers != expected_details_headers:
                errors.append(f'Details file headers incorrect. Expected: {expected_details_headers}, Got: {headers}')
            
            # Check first few rows for basic data validation
            for i, row in enumerate(reader):
                if i >= 3:  # Check only first 3 rows
                    break
                if len(row) != len(expected_details_headers):
                    errors.append(f'Details file row {i+2} has {len(row)} columns, expected {len(expected_details_headers)}')
                    break
    
    except Exception as e:
        errors.append(f'Error reading details file: {str(e)}')
    
    return errors


def export_csv(request):
    """Export current claims data to CSV"""
    import csv
    from django.http import StreamingHttpResponse
    
    def generate_claims_csv():
        """Generator for claims CSV data"""
        yield '|'.join(['id', 'patient_name', 'billed_amount', 'paid_amount', 'status', 'insurer_name', 'discharge_date']) + '\n'
        
        for claim in Claim.objects.all().iterator():
            yield '|'.join([
                str(claim.id),
                claim.patient_name,
                str(claim.billed_amount),
                str(claim.paid_amount),
                claim.status,
                claim.insurer_name,
                claim.discharge_date.strftime('%Y-%m-%d')
            ]) + '\n'
    
    def generate_details_csv():
        """Generator for details CSV data"""
        yield '|'.join(['id', 'claim_id', 'denial_reason', 'cpt_codes']) + '\n'
        
        for detail in ClaimDetail.objects.all().iterator():
            yield '|'.join([
                str(detail.id),
                str(detail.claim.id),
                detail.denial_reason or 'N/A',
                detail.cpt_codes
            ]) + '\n'
    
    export_type = request.GET.get('type', 'claims')
    
    if export_type == 'claims':
        response = StreamingHttpResponse(generate_claims_csv(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="exported_claims.csv"'
    else:
        response = StreamingHttpResponse(generate_details_csv(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="exported_claim_details.csv"'
    
    return response


def user_login(request):
    """Simple login view"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            next_url = request.GET.get('next', 'claims:dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'claims/login.html')


def user_logout(request):
    """Logout view"""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('claims:dashboard')


def user_register(request):
    """Simple registration view"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        # Basic validation
        if not username or not password:
            messages.error(request, 'Username and password are required.')
            return render(request, 'claims/register.html')
        
        if password != password_confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'claims/register.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'claims/register.html')
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        
        messages.success(request, f'Account created for {username}! You can now log in.')
        return redirect('claims:login')
    
    return render(request, 'claims/register.html')


@login_required
def user_profile(request):
    """User profile with activity history"""
    user = request.user
    
    # Get user's activities
    user_notes = ClaimNote.objects.filter(created_by=user).order_by('-created_at')[:10]
    user_flags = ClaimFlag.objects.filter(flagged_by=user).order_by('-created_at')[:10]
    
    # Stats
    stats = {
        'notes_count': ClaimNote.objects.filter(created_by=user).count(),
        'flags_count': ClaimFlag.objects.filter(flagged_by=user).count(),
        'resolved_flags': ClaimFlag.objects.filter(resolved_by=user).count(),
    }
    
    context = {
        'user_notes': user_notes,
        'user_flags': user_flags,
        'stats': stats,
    }
    
    return render(request, 'claims/profile.html', context)