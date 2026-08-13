from django.core.management.base import BaseCommand
from service.migrations_nonsql.runner import NonSqlMigrationRunner


class Command(BaseCommand):
    help = "Applies non-SQL versioned migrations (MongoDB, MinIO, ChromaDB)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting non-SQL migration runner..."))
        try:
            runner = NonSqlMigrationRunner()
            executed = runner.run()
            if executed:
                for name in executed:
                    self.stdout.write(self.style.SUCCESS(f"Applied: {name}"))
            else:
                self.stdout.write(self.style.SUCCESS("No pending non-SQL migrations."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Non-SQL migration failed: {e}"))
            raise SystemExit(1)
