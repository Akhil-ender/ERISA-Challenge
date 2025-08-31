from django.contrib import admin
from .models import Claim, ClaimDetail, ClaimNote, ClaimFlag


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient_name', 'billed_amount', 'paid_amount', 'status', 'insurer_name', 'discharge_date', 'is_flagged', 'created_at')
    list_filter = ('status', 'is_flagged', 'insurer_name', 'created_at')
    search_fields = ('patient_name', 'insurer_name')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('patient_name', 'billed_amount', 'paid_amount', 'status', 'insurer_name', 'discharge_date')
        }),
        ('User Data', {
            'fields': ('is_flagged', 'created_by', 'updated_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(ClaimDetail)
class ClaimDetailAdmin(admin.ModelAdmin):
    list_display = ('claim', 'cpt_codes', 'denial_reason', 'created_at')
    search_fields = ('claim__patient_name', 'cpt_codes', 'denial_reason')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ClaimNote)
class ClaimNoteAdmin(admin.ModelAdmin):
    list_display = ('claim', 'content_preview', 'created_by', 'created_at')
    list_filter = ('created_by', 'created_at')
    search_fields = ('claim__patient_name', 'content')
    readonly_fields = ('created_at', 'updated_at')
    
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = "Content Preview"


@admin.register(ClaimFlag)
class ClaimFlagAdmin(admin.ModelAdmin):
    list_display = ('claim', 'reason', 'is_resolved', 'flagged_by', 'created_at', 'resolved_at')
    list_filter = ('reason', 'is_resolved', 'created_at')
    search_fields = ('claim__patient_name', 'description')
    readonly_fields = ('created_at', 'resolved_at')
    
    fieldsets = (
        ('Flag Information', {
            'fields': ('claim', 'reason', 'description', 'is_resolved')
        }),
        ('User Tracking', {
            'fields': ('flagged_by', 'resolved_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'resolved_at'),
            'classes': ('collapse',)
        })
    )