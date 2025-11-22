import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Supabase configuration missing in .env")

# Backend service client (full access)
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Optional: user-level client (anon)
supabase_anon = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
