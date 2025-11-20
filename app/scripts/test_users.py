"""
Test users template.

Edit the "password" field for each user to the desired password, then run
`python scripts/seed_test_users.py` to create them in Supabase.

Do NOT commit real passwords to source control. This file is convenient
for local development only.
"""


TEST_USERS = [
    {"email": "user@gmail.com", "password": "12345678", "name": "user"},
]
