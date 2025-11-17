"""
Management command to ingest JSON data into ChromaDB
"""
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.rag.rag_service_chromadb import RAGServiceChroma


class Command(BaseCommand):
    help = 'Ingest JSON files from data directory into ChromaDB with hybrid indexing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data-dir',
            type=str,
            default=None,
            help='Path to data directory (default: BASE_DIR/data)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-ingestion (clears existing data)'
        )

    def handle(self, *args, **options):
        data_dir = options.get('data_dir')
        force = options.get('force', False)
        
        if data_dir is None:
            data_dir = os.path.join(settings.BASE_DIR, 'data')
        
        if not os.path.exists(data_dir):
            self.stdout.write(
                self.style.ERROR(f'Data directory not found: {data_dir}')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS('=' * 60)
        )
        self.stdout.write(
            self.style.SUCCESS('ChromaDB Data Ingestion (Hybrid Retrieval)')
        )
        self.stdout.write(
            self.style.SUCCESS('=' * 60)
        )
        
        if force:
            self.stdout.write(
                self.style.WARNING('\nForce mode: Clearing existing data...')
            )
        
        self.stdout.write(f'\nData directory: {data_dir}\n')
        
        try:
            # Initialize service and ingest data
            rag_service = RAGServiceChroma()
            stats = rag_service.ingest_all_data(data_dir)
            
            self.stdout.write(
                self.style.SUCCESS('\n' + '=' * 60)
            )
            self.stdout.write(
                self.style.SUCCESS('Ingestion Complete!')
            )
            self.stdout.write(
                self.style.SUCCESS('=' * 60)
            )
            
            total_chunks = sum(stats.values())
            self.stdout.write(f'\nTotal chunks ingested: {total_chunks}')
            
            for competitor, count in stats.items():
                self.stdout.write(f'  - {competitor.capitalize()}: {count} chunks')
            
            self.stdout.write(
                self.style.SUCCESS('\n✓ Data successfully ingested into ChromaDB')
            )
            self.stdout.write(
                self.style.SUCCESS('✓ Hybrid retrieval enabled (Dense + BM25)')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n✗ Error during ingestion: {str(e)}')
            )
            raise
