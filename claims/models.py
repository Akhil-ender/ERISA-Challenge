from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Claim(models.Model):
    """
    Claim List Fields - Table view data (provided by us)
    """
    # Basic claim information
    patient_name = models.CharField(max_length=200)
    billed_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('processing', 'Processing'),
        ('review', 'Under Review'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    insurer_name = models.CharField(max_length=200)
    discharge_date = models.DateField()
    
    # User-Generated Data
    is_flagged = models.BooleanField(default=False, help_text="Users can flag claims for review")
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # User tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_claims')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_claims')

    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Claim {self.id} - {self.patient_name}"


class ClaimDetail(models.Model):
    """
    Claim Detail Fields - Detailed view data (provided by us)
    """
    claim = models.OneToOneField(Claim, on_delete=models.CASCADE, related_name='detail')
    
    # Additional detail fields
    cpt_codes = models.TextField(help_text="CPT codes separated by commas")
    denial_reason = models.TextField(blank=True, null=True)
    
    # Timestamps for detail
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Details for {self.claim}"
    
    def get_cpt_codes_list(self):
        """Return CPT codes as a list"""
        if self.cpt_codes:
            return [code.strip() for code in self.cpt_codes.split(',')]
        return []


class ClaimNote(models.Model):
    """
    Custom annotations and comments for claims
    """
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='notes')
    content = models.TextField()
    
    # User tracking
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Note on {self.claim} by {self.created_by.username}"


class ClaimFlag(models.Model):
    """
    Flag tracking for claims with reasons
    """
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='flags')
    
    REASON_CHOICES = [
        ('suspicious', 'Suspicious Activity'),
        ('review_needed', 'Needs Review'),
        ('documentation', 'Missing Documentation'),
        ('amount_discrepancy', 'Amount Discrepancy'),
        ('other', 'Other'),
    ]
    
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    description = models.TextField(blank=True, null=True)
    is_resolved = models.BooleanField(default=False)
    
    # User tracking
    flagged_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flagged_claims', null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_flags')
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Flag on {self.claim} - {self.get_reason_display()}"