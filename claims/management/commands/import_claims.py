import csv
import os
from datetime import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from claims.models import Claim, ClaimDetail


class Command(BaseCommand):
    help = 'Import claims data from CSV files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--claims-file',
            type=str,
            default='claims/claim_list_data.csv',
            help='Path to the claims list CSV file'
        )
        parser.add_argument(
            '--details-file',
            type=str,
            default='claims/claim_detail_data.csv',
            help='Path to the claims detail CSV file'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before import'
        )

    def handle(self, *args, **options):
        claims_file = options['claims_file']
        details_file = options['details_file']
        
        # Check if files exist
        if not os.path.exists(claims_file):
            raise CommandError(f'Claims file "{claims_file}" does not exist.')
        if not os.path.exists(details_file):
            raise CommandError(f'Details file "{details_file}" does not exist.')

        # Clear existing data if requested
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            with transaction.atomic():
                ClaimDetail.objects.all().delete()
                Claim.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared.'))

        # Import claims
        self.stdout.write('Starting claims import...')
        claims_imported = self.import_claims(claims_file)
        self.stdout.write(
            self.style.SUCCESS(f'Successfully imported {claims_imported} claims.')
        )

        # Import claim details
        self.stdout.write('Starting claim details import...')
        details_imported = self.import_claim_details(details_file)
        self.stdout.write(
            self.style.SUCCESS(f'Successfully imported {details_imported} claim details.')
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Import completed! {claims_imported} claims and {details_imported} details imported.'
            )
        )

    def import_claims(self, file_path):
        """Import claims from CSV file"""
        imported_count = 0
        
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter='|')
            
            # Batch processing for better performance
            batch_size = 1000
            claims_batch = []
            
            for row in reader:
                try:
                    # Map status values
                    status_mapping = {
                        'Paid': 'approved',
                        'Denied': 'denied',
                        'Under Review': 'review',
                        'Processing': 'processing',
                        'Pending': 'pending'
                    }
                    
                    status = status_mapping.get(row['status'], 'pending')
                    
                    # Parse discharge date
                    discharge_date = datetime.strptime(row['discharge_date'], '%Y-%m-%d').date()
                    
                    claim = Claim(
                        id=int(row['id']),
                        patient_name=row['patient_name'],
                        billed_amount=Decimal(row['billed_amount']),
                        paid_amount=Decimal(row['paid_amount']),
                        status=status,
                        insurer_name=row['insurer_name'],
                        discharge_date=discharge_date
                    )
                    
                    claims_batch.append(claim)
                    
                    # Bulk create when batch is full
                    if len(claims_batch) >= batch_size:
                        Claim.objects.bulk_create(claims_batch, ignore_conflicts=True)
                        imported_count += len(claims_batch)
                        claims_batch = []
                        
                        if imported_count % 1000 == 0:
                            self.stdout.write(f'Imported {imported_count} claims...')
                
                except (ValueError, KeyError) as e:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping invalid row: {row} - Error: {e}')
                    )
            
            # Import remaining claims in batch
            if claims_batch:
                Claim.objects.bulk_create(claims_batch, ignore_conflicts=True)
                imported_count += len(claims_batch)
        
        return imported_count

    def import_claim_details(self, file_path):
        """Import claim details from CSV file"""
        imported_count = 0
        
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter='|')
            
            # Batch processing for better performance
            batch_size = 1000
            details_batch = []
            
            for row in reader:
                try:
                    # Get the corresponding claim
                    claim_id = int(row['claim_id'])
                    
                    # Skip if claim doesn't exist (shouldn't happen with proper data)
                    if not Claim.objects.filter(id=claim_id).exists():
                        self.stdout.write(
                            self.style.WARNING(f'Claim {claim_id} not found for detail row')
                        )
                        continue
                    
                    # Handle denial reason - 'N/A' should be None
                    denial_reason = row['denial_reason']
                    if denial_reason == 'N/A':
                        denial_reason = None
                    
                    detail = ClaimDetail(
                        claim_id=claim_id,
                        cpt_codes=row['cpt_codes'],
                        denial_reason=denial_reason
                    )
                    
                    details_batch.append(detail)
                    
                    # Bulk create when batch is full
                    if len(details_batch) >= batch_size:
                        ClaimDetail.objects.bulk_create(details_batch, ignore_conflicts=True)
                        imported_count += len(details_batch)
                        details_batch = []
                        
                        if imported_count % 1000 == 0:
                            self.stdout.write(f'Imported {imported_count} claim details...')
                
                except (ValueError, KeyError) as e:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping invalid detail row: {row} - Error: {e}')
                    )
            
            # Import remaining details in batch
            if details_batch:
                ClaimDetail.objects.bulk_create(details_batch, ignore_conflicts=True)
                imported_count += len(details_batch)
        
        return imported_count
