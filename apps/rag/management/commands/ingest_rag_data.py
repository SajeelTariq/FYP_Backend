"""
Management command to ingest JSON data into RAG system.
"""
from django.core.management.base import BaseCommand
from apps.rag.rag_service import RAGService


class Command(BaseCommand):
    help = 'Ingest JSON files from data directory into RAG system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data-dir',
            type=str,
            help='Path to data directory (default: BASE_DIR/data)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-ingestion (delete existing chunks first)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Starting RAG data ingestion...\n'))
        
        data_dir = options.get('data_dir')
        force = options.get('force')
        
        if force:
            from apps.rag.rag_models import DocumentChunk
            count = DocumentChunk.objects.all().count()
            if count > 0:
                self.stdout.write(self.style.WARNING(f'⚠️  Deleting {count} existing chunks...'))
                DocumentChunk.objects.all().delete()
                self.stdout.write(self.style.SUCCESS('✅ Deleted\n'))
        
        # Initialize service
        rag_service = RAGService()
        
        # Ingest data
        results = rag_service.ingest_all_data(data_dir)
        
        # Print summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('\n📊 INGESTION SUMMARY\n'))
        self.stdout.write('='*60 + '\n')
        
        total_chunks = 0
        for competitor, chunk_count in results.items():
            self.stdout.write(f"  {competitor}: {chunk_count} chunks")
            total_chunks += chunk_count
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'\n✅ Total: {total_chunks} chunks ingested\n'))
        self.stdout.write('='*60 + '\n')
