import os
import stat
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Fixes SQLite database file permissions and checks for locks'

    def handle(self, *args, **options):
        db_path = settings.DATABASES['default']['NAME']
        
        # Check if the database file exists
        if not os.path.exists(db_path):
            self.stdout.write(self.style.ERROR(f"Database file not found at: {db_path}"))
            return
            
        # Check file permissions
        mode = os.stat(db_path).st_mode
        self.stdout.write(f"Current permissions: {oct(mode & 0o777)}")
        
        # Check for lock files
        wal_path = f"{db_path}-wal"
        shm_path = f"{db_path}-shm"
        
        for lock_file in [wal_path, shm_path]:
            if os.path.exists(lock_file):
                self.stdout.write(self.style.WARNING(f"Found lock file: {lock_file}"))
                try:
                    os.remove(lock_file)
                    self.stdout.write(self.style.SUCCESS(f"Removed lock file: {lock_file}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to remove {lock_file}: {str(e)}"))
        
        # Make sure the database is writable
        try:
            # Make the file writable by the current user
            os.chmod(db_path, 0o666)  # Read/write for all
            self.stdout.write(self.style.SUCCESS(f"Set permissions for {db_path} to 0o666"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to set permissions: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS("Database permission check complete."))
