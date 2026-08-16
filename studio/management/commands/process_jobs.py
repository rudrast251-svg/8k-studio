import time

from django.core.management.base import BaseCommand
from django.db import transaction

from studio.models import Job
from studio.services import process_job


class Command(BaseCommand):
    help = 'Background worker: processes queued enhancement jobs. Run continuously with --loop.'

    def add_arguments(self, parser):
        parser.add_argument('--loop', action='store_true', help='Run forever, polling for new jobs.')
        parser.add_argument('--interval', type=float, default=3.0, help='Seconds between polls when looping.')
        parser.add_argument('--once', action='store_true', help='Process all currently queued jobs, then exit.')

    def handle(self, *args, **options):
        if options['loop']:
            self.stdout.write(self.style.SUCCESS('8K Studio worker started. Watching for jobs...'))
            while True:
                processed = self._drain_queue()
                if not processed:
                    time.sleep(options['interval'])
        else:
            count = self._drain_queue()
            self.stdout.write(self.style.SUCCESS(f'Processed {count} job(s).'))

    def _drain_queue(self) -> int:
        count = 0
        while True:
            job = self._claim_next_job()
            if job is None:
                break
            self.stdout.write(f'Processing job #{job.id} ({job.job_type})...')
            process_job(job)
            job.refresh_from_db()
            self.stdout.write(self.style.SUCCESS(f'Job #{job.id} -> {job.status}'))
            count += 1
        return count

    @staticmethod
    def _claim_next_job():
        """Atomically claim the oldest queued job via a conditional UPDATE,
        so multiple worker processes can safely run against the same DB
        (works portably across SQLite/Postgres, unlike SELECT ... FOR UPDATE
        SKIP LOCKED which SQLite doesn't support)."""
        candidate = Job.objects.filter(status=Job.Status.UPLOADED).order_by('created_at').first()
        if candidate is None:
            return None
        with transaction.atomic():
            updated = Job.objects.filter(pk=candidate.pk, status=Job.Status.UPLOADED).update(
                status=Job.Status.PROCESSING, progress_percent=5
            )
            if not updated:
                return None
        candidate.refresh_from_db()
        return candidate
