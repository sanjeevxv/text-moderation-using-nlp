#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'safenet.settings')
sys.path.append('c:\\Users\\vansh\\Desktop\\safenet')
django.setup()

# Test database access
try:
    from moderation.models import ModerationResult
    fields = [f.name for f in ModerationResult._meta.fields if not f.many_to_one]
    print("ModerationResult fields:", fields)

    # Try to access the database
    count = ModerationResult.objects.count()
    print(f"ModerationResult records: {count}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
